// Prueba del panel (admin.html): "Pegar ofertas" reenvía motivo/alcance y
// foto de Drive al backend (contrato de Code.gs: parse_ofertas devuelve
// motivo/motivo_tipo/alcance por producto; registrar_ofertas acepta
// foto_drive_id/foto_nombre_archivo). Sin navegador: carga el <script> del
// panel en una VM con un DOM mínimo simulado, como test-panel-cambiar-foto.js.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const HTML = fs.readFileSync('/home/hatch/workspace/impacto/pagina/admin.html', 'utf8');
const SCRIPT = HTML.match(/<script>([\s\S]*?)<\/script>/)[1];

// ---------- DOM mínimo ----------
function makeEl(id) {
  return {
    id: id || '', innerHTML: '', textContent: '', value: '', disabled: false,
    style: {}, files: [], onclick: null, className: '', children: [],
    querySelectorAll() { return []; },
    querySelector() { return null; },
    appendChild(c) { this.children.push(c); return c; },
    closest() { return null; },
    getAttribute() { return null; },
    setAttribute() { },
    addEventListener() { },
  };
}
const elementos = {};
const documentStub = {
  getElementById(id) {
    if (!elementos[id]) elementos[id] = makeEl(id);
    return elementos[id];
  },
  createElement(tag) { return makeEl(tag); },
  querySelector() { return null; },
  querySelectorAll() { return []; },
};
const localStorageStub = {
  _d: {},
  getItem(k) { return this._d[k] || null; },
  setItem(k, v) { this._d[k] = String(v); },
  clear() { this._d = {}; },
};

// ---------- fetch simulado ----------
function mockFetch(url) {
  if (String(url) === 'config.json') {
    return Promise.resolve({ json: () => Promise.resolve({ api_url: 'https://example.com/exec' }) });
  }
  if (String(url).indexOf('?action=estado') !== -1) {
    return Promise.resolve({ json: () => Promise.resolve({ ok: true, usuarios_configurados: true }) });
  }
  return Promise.resolve({ json: () => Promise.resolve({ ok: true }) });
}

const sandbox = {
  console, setTimeout, clearTimeout,
  document: documentStub,
  localStorage: localStorageStub,
  fetch: mockFetch,
  FileReader: function () { },
};
vm.createContext(sandbox);
vm.runInContext(SCRIPT, sandbox);
const G = (expr) => vm.runInContext(expr, sandbox);
const tick = () => new Promise(r => setTimeout(r, 20));

// Ofertas tal como las devuelve parse_ofertas (backend nuevo): una con
// motivo de rebaja y foto de Drive por nombre; otra sin motivo y con la
// foto que ya tenía el producto (miniatura de Drive, sin drive_id).
const OFERTAS = [
  {
    grupo: 'VENTILADORES', tipo: 'Ventilador recargable', modelo: 'Olmco F6',
    caracteristicas: 'Batería 20000 mAh',
    texto_original: '[10/11/26 19:15] Nathali: Plantilla modificada motivo (Rebaja de precio)',
    motivo: 'Plantilla modificada motivo (Rebaja de precio)', motivo_tipo: 'precio',
    alcance: { precio: true, caracteristicas: false, proveedores: false, foto: false },
    foto: {
      foto_url: 'https://drive.google.com/thumbnail?id=WA0198ID&sz=w1000', foto_tipo: 'vendedor',
      origen: 'drive', drive_id: 'WA0198ID', nombre_archivo: 'Ventilador-Olmco-F6-WA0198.jpg',
      detalle: 'Coincide por nombre: Ventilador-Olmco-F6-WA0198.jpg', candidatas: [], usadas: [],
    },
    proveedores: [{ proveedor: 'Santiago 🍋', precio: 40, moneda: 'USD', comision: 1000, comision_moneda: 'MN', garantia: '10 días', domicilio: 'Incluido', pago: 'USD' }],
  },
  {
    grupo: 'TV', tipo: 'Smart TV', modelo: 'Vivamax 32',
    caracteristicas: '', texto_original: '[13/11/26 10:00] Nathali: Smart TV Vivamax 32',
    motivo: '', motivo_tipo: '',
    alcance: { precio: true, caracteristicas: true, proveedores: true, foto: true },
    foto: {
      foto_url: 'https://drive.google.com/thumbnail?id=EXISTEID&sz=w1000', foto_tipo: 'vendedor',
      origen: 'drive', detalle: 'Foto que ya tiene el producto.', candidatas: [],
    },
    proveedores: [{ proveedor: 'Santiago 🍋', precio: 300, moneda: 'USD', comision: 2000, comision_moneda: 'MN', garantia: '30 días', domicilio: 'Incluido', pago: 'USD' }],
  },
];

let PASSED = 0;
function check(nombre, fn) {
  return Promise.resolve().then(fn).then(
    () => { PASSED++; console.log('  OK  ' + nombre); },
    (e) => { console.log('  FALLA  ' + nombre + ' → ' + e.message); process.exitCode = 1; });
}
function eq(a, b, msg) { assert.strictEqual(a, b, (msg || '') + ' (esperado ' + JSON.stringify(b) + ', obtenido ' + JSON.stringify(a) + ')'); }
function deepEq(a, b, msg) { assert.deepStrictEqual(a, b, (msg || '') + ' (esperado ' + JSON.stringify(b) + ', obtenido ' + JSON.stringify(a) + ')'); }
function incluye(s, frag, msg) { assert.ok(String(s || '').includes(frag), (msg || '') + ' (esperado que contenga ' + JSON.stringify(frag) + ')'); }

function payload() {
  return JSON.parse(G('JSON.stringify(recogerVistaPegar())'));
}

(async () => {
  await tick(); await tick(); // deja correr arrancar() con los stubs
  G(`vistaPegar = ${JSON.stringify(OFERTAS)};`);
  G('renderVistaPegar();');
  const htmlVista = elementos['pg-vista'].innerHTML;

  await check('La vista previa muestra el motivo y los chips de alcance', () => {
    incluye(htmlVista, 'data-pg="motivo"');
    incluye(htmlVista, 'Plantilla modificada motivo (Rebaja de precio)');
    incluye(htmlVista, 'data-pg-alcance-chip="precio"');
    incluye(htmlVista, 'data-pg-alcance-chip="caracteristicas"');
    incluye(htmlVista, 'data-pg-alcance-chip="proveedores"');
    incluye(htmlVista, 'data-pg-alcance-chip="foto"');
    incluye(htmlVista, 'data-pg-alcance-chip="todo"');
    // Rebaja: solo el chip Precio activo; sin motivo: todos activos.
    incluye(htmlVista, 'class="pg-chip activo" data-pg-alcance-chip="precio"');
  });

  await check('recogerVistaPegar envía motivo, tipo y alcance de la rebaja', () => {
    const p = payload();
    eq(p[0].motivo, 'Plantilla modificada motivo (Rebaja de precio)');
    eq(p[0].motivo_tipo, 'precio');
    deepEq(p[0].alcance, { precio: true, caracteristicas: false, proveedores: false, foto: false });
    incluye(p[0].texto_original, 'Rebaja de precio');
  });

  await check('recogerVistaPegar envía foto_drive_id y foto_nombre_archivo (Drive por nombre)', () => {
    const p = payload();
    eq(p[0].foto_drive_id, 'WA0198ID');
    eq(p[0].foto_nombre_archivo, 'Ventilador-Olmco-F6-WA0198.jpg');
    eq(p[0].foto_url, 'https://drive.google.com/thumbnail?id=WA0198ID&sz=w1000');
    eq(p[0].foto_tipo, 'vendedor');
    eq(p[0].foto_origen, 'drive');
    eq(p[0].foto_descargar, false);
  });

  await check('Foto que ya tenía el producto: el drive_id se saca de la miniatura', () => {
    const p = payload();
    eq(p[1].foto_drive_id, 'EXISTEID');
    eq(p[1].foto_nombre_archivo, '');
    eq(p[1].motivo, '');
    eq(p[1].motivo_tipo, '');
    deepEq(p[1].alcance, { precio: true, caracteristicas: true, proveedores: true, foto: true });
  });

  await check('Los campos de antes siguen viajando (foto, proveedores, precios)', () => {
    const p = payload();
    eq(p[0].grupo, 'VENTILADORES');
    eq(p[0].tipo, 'Ventilador recargable');
    eq(p[0].modelo, 'Olmco F6');
    eq(p[0].caracteristicas, 'Batería 20000 mAh');
    eq(p[0].proveedores[0].precio, 40);
    eq(p[0].proveedores[0].proveedor, 'Santiago 🍋');
    eq(p[1].proveedores[0].precio, 300);
  });

  await check('Borrar el motivo en la vista previa abre el alcance a todo', () => {
    // Bloque falso del DOM: el usuario borró el motivo de la oferta 0.
    function fakeInput(attr, value) {
      return { getAttribute: (n) => (n === 'data-pg' ? attr : null), value: value };
    }
    function fakeBlock(i, vals) {
      return {
        getAttribute: (n) => (n === 'data-pg-prod' ? String(i) : null),
        querySelector: () => null,
        querySelectorAll: (sel) => {
          if (String(sel).indexOf('data-pg-prov') !== -1) return [];
          return ['tipo', 'modelo', 'caracteristicas', 'motivo'].map((k) => fakeInput(k, vals[k]));
        },
      };
    }
    elementos['pg-vista'].querySelectorAll = (sel) => {
      if (String(sel).indexOf('data-pg-prod') !== -1) {
        return [
          fakeBlock(0, { tipo: 'Ventilador recargable', modelo: 'Olmco F6', caracteristicas: 'Batería 20000 mAh', motivo: '' }),
          fakeBlock(1, { tipo: 'Smart TV', modelo: 'Vivamax 32', caracteristicas: '', motivo: '' }),
        ];
      }
      return [];
    };
    const p = payload();
    eq(p[0].motivo, '');
    eq(p[0].motivo_tipo, '');
    deepEq(p[0].alcance, { precio: true, caracteristicas: true, proveedores: true, foto: true });
  });

  console.log('\n' + PASSED + ' checks pasaron.' + (process.exitCode ? ' HUBO FALLAS.' : ' TODO OK.'));
})();
