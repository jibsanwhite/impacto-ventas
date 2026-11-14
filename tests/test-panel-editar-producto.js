// Prueba del panel (admin.html): editar un producto ya subido sin eliminarlo.
// - Botón por producto (solo admin): Disponible ✓ / No disponible →
//   update_producto con el estado invertido.
// - Selector de moneda por proveedor (solo admin): corregir la moneda junto
//   al precio sin tocar el importe → update_proveedor {precio, moneda}.
// - El gestor no ve ni el botón de estado ni el selector de moneda.
// Mismo harness que test-panel-cambiar-foto.js (VM + DOM mínimo + fetch).
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

// Fila de proveedor falsa (para el botón "Guardar precio").
let SELECT_MONEDA_VISIBLE = true;
function fakeSelect(original, valor) {
  return {
    value: valor,
    getAttribute(n) { return n === 'data-moneda-original' ? original : null; },
  };
}
const SELECTS = {
  1: fakeSelect('CUP', 'CUP'),
  2: fakeSelect('EUR', 'EUR'),
};
function fakeFilaProv(pid) {
  return {
    getAttribute(n) { return n === 'data-prov' ? String(pid) : null; },
    querySelector(sel) {
      if (String(sel).indexOf('data-campo="precio"') !== -1) return { value: String(pid) === '1' ? '210' : '300' };
      if (String(sel).indexOf('data-campo="moneda"') !== -1) return SELECT_MONEDA_VISIBLE ? SELECTS[pid] : null;
      return null;
    },
  };
}
// Botones falsos de estado por producto.
const fakeEstadoBtns = {};
function fakeEstadoBtn(pid) {
  if (!fakeEstadoBtns[pid]) {
    const b = makeEl('est-btn-' + pid);
    b.textContent = String(pid) === '1' ? 'Disponible ✓' : 'No disponible';
    b.getAttribute = (n) => (n === 'data-estado-prod' ? String(pid) : null);
    fakeEstadoBtns[pid] = b;
  }
  return fakeEstadoBtns[pid];
}
// Botones falsos "Guardar precio" por proveedor.
const fakePrecioBtns = {};
function fakePrecioBtn(pid) {
  if (!fakePrecioBtns[pid]) {
    const b = makeEl('precio-btn-' + pid);
    b.textContent = 'Guardar precio';
    b.getAttribute = (n) => (n === 'data-accion' ? 'precio' : null);
    b.closest = () => fakeFilaProv(pid);
    fakePrecioBtns[pid] = b;
  }
  return fakePrecioBtns[pid];
}
function listaConBotones() {
  const el = makeEl('lista-productos');
  el.querySelectorAll = (sel) => {
    const s = String(sel);
    if (s.indexOf('data-estado-prod') !== -1) return [fakeEstadoBtn('1'), fakeEstadoBtn('2')];
    if (s.indexOf('data-accion') !== -1) return [fakePrecioBtn('1'), fakePrecioBtn('2')];
    return [];
  };
  return el;
}

const documentStub = {
  getElementById(id) {
    if (!elementos[id]) {
      elementos[id] = id === 'lista-productos' ? listaConBotones() : makeEl(id);
    }
    return elementos[id];
  },
  createElement(tag) { return makeEl(tag); },
  querySelector(sel) {
    const m = String(sel).match(/\[data-cf-editor="([^"]+)"\]/);
    if (m) { const k = 'cf-' + m[1]; return elementos[k] || (elementos[k] = makeEl(k)); }
    return null;
  },
  querySelectorAll() { return []; },
};
const localStorageStub = {
  _d: {},
  getItem(k) { return this._d[k] || null; },
  setItem(k, v) { this._d[k] = String(v); },
  clear() { this._d = {}; },
};

// ---------- fetch simulado ----------
const LLAMADAS = [];
const DATOS = {
  productos: [
    { id: 1, grupo: 'TV', tipo: 'TV Premier 32" con barra', modelo: '', caracteristicas: 'Con barra de sonido', foto_url: 'https://drive.google.com/thumbnail?id=TV1&sz=w1000', foto_tipo: 'vendedor', estado: 'disponible' },
    { id: 2, grupo: 'TV', tipo: 'TV Royal 50"', modelo: '', caracteristicas: '', foto_url: '', foto_tipo: 'referencia', estado: 'vendido' },
  ],
  proveedores: [
    { id: 1, producto_id: 1, proveedor: 'Santiago 🍋', gestor_usuario: '', precio: 210, moneda: 'CUP', pago: 'USD, MN a precio toque', stock_disponible: true, comision: 4000, comision_moneda: 'MN', domicilio: 'Incluido', garantia: '10 días', notas_internas: '' },
    { id: 2, producto_id: 2, proveedor: 'Santiago 🍋', gestor_usuario: '', precio: 300, moneda: 'EUR', pago: 'USD', stock_disponible: true, comision: 1000, comision_moneda: 'MN', domicilio: 'Incluido', garantia: '10 días', notas_internas: '' },
  ],
};
function mockFetch(url, opts) {
  if (String(url) === 'config.json') {
    return Promise.resolve({ json: () => Promise.resolve({ api_url: 'https://example.com/exec' }) });
  }
  if (String(url).indexOf('?action=estado') !== -1) {
    return Promise.resolve({ json: () => Promise.resolve({ ok: true, usuarios_configurados: true }) });
  }
  const body = opts && opts.body ? JSON.parse(opts.body) : {};
  LLAMADAS.push(body);
  let r = { ok: true };
  if (body.action === 'datos_gestion') r = { ok: true, rol: 'administrador', usuario: 'djalonso', productos: DATOS.productos, proveedores: DATOS.proveedores };
  if (body.action === 'listar_usuarios') r = { ok: true, usuarios: [] };
  return Promise.resolve({ json: () => Promise.resolve(r) });
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

let PASSED = 0;
function check(nombre, fn) {
  return Promise.resolve().then(fn).then(
    () => { PASSED++; console.log('  OK  ' + nombre); },
    (e) => { console.log('  FALLA  ' + nombre + ' → ' + e.message); process.exitCode = 1; });
}
function eq(a, b, msg) { assert.strictEqual(a, b, (msg || '') + ' (esperado ' + JSON.stringify(b) + ', obtenido ' + JSON.stringify(a) + ')'); }
function incluye(s, frag, msg) { assert.ok(String(s || '').includes(frag), (msg || '') + ' (esperado que contenga ' + JSON.stringify(frag) + ')'); }
function noIncluye(s, frag, msg) { assert.ok(!String(s || '').includes(frag), (msg || '') + ' (no debía contener ' + JSON.stringify(frag) + ')'); }

(async () => {
  await tick(); await tick(); // deja correr arrancar() con los stubs
  G(`sesion = {token: 'tok-admin', usuario: 'djalonso', rol: 'administrador', nombre: 'D.J.'}; API_URL = 'https://example.com/exec';`);
  G(`vistaPanel(${JSON.stringify(DATOS)})`);
  const lista = elementos['lista-productos'];
  const htmlProductos = lista.children.map(c => c.innerHTML).join('\n');

  await check('Admin: cada producto muestra su botón de estado (Disponible ✓ / No disponible)', () => {
    incluye(htmlProductos, 'data-estado-prod="1"');
    incluye(htmlProductos, 'Disponible ✓');
    incluye(htmlProductos, 'data-estado-prod="2"');
    incluye(htmlProductos, 'No disponible');
  });
  await check('Admin: el subtítulo explica los controles nuevos', () => {
    incluye(elementos['app'].innerHTML, 'disponible o no disponible');
  });
  await check('Admin: cada proveedor muestra el selector de moneda con la actual seleccionada', () => {
    incluye(htmlProductos, 'data-campo="moneda"');
    incluye(htmlProductos, '<option selected>CUP</option>');
  });
  await check('Moneda no listada (EUR) se añade como opción seleccionada, no se resetea', () => {
    incluye(htmlProductos, '<option selected>EUR</option>');
  });
  await check('Tocar "Disponible ✓" llama update_producto con estado vendido', async () => {
    LLAMADAS.length = 0;
    fakeEstadoBtn('1').onclick();
    await tick(); await tick();
    const llamada = LLAMADAS.find(c => c.action === 'update_producto');
    assert.ok(llamada, 'no se llamó a update_producto');
    eq(llamada.id, '1');
    eq(llamada.estado, 'vendido');
  });
  await check('Tocar "No disponible" llama update_producto con estado disponible', async () => {
    LLAMADAS.length = 0;
    fakeEstadoBtn('2').onclick();
    await tick(); await tick();
    const llamada = LLAMADAS.find(c => c.action === 'update_producto');
    assert.ok(llamada, 'no se llamó a update_producto');
    eq(llamada.id, '2');
    eq(llamada.estado, 'disponible');
  });
  await check('Cambiar la moneda a USD y guardar: update_proveedor con el mismo importe (210) y moneda USD', async () => {
    LLAMADAS.length = 0;
    SELECTS[1].value = 'USD'; // el admin cambia el selector de CUP a USD
    fakePrecioBtn('1').onclick();
    await tick(); await tick();
    const llamada = LLAMADAS.find(c => c.action === 'update_proveedor');
    assert.ok(llamada, 'no se llamó a update_proveedor');
    eq(llamada.id, '1');
    eq(llamada.precio, 210);
    eq(llamada.moneda, 'USD');
  });
  await check('Guardar sin tocar la moneda: update_proveedor lleva el precio y la moneda actual', async () => {
    LLAMADAS.length = 0;
    SELECTS[1].value = 'CUP';
    fakePrecioBtn('1').onclick();
    await tick(); await tick();
    const llamada = LLAMADAS.find(c => c.action === 'update_proveedor');
    assert.ok(llamada, 'no se llamó a update_proveedor');
    eq(llamada.precio, 210);
    eq(llamada.moneda, 'CUP');
  });
  await check('Gestor: no ve el botón de estado ni el selector de moneda (texto plano)', async () => {
    G(`sesion = {token: 'tok-gestor', usuario: 'nathali', rol: 'gestor', nombre: 'Nathali'};`);
    elementos['lista-productos'] = listaConBotones();
    G(`vistaPanel(${JSON.stringify(DATOS)})`);
    const htmlGestor = elementos['lista-productos'].children.map(c => c.innerHTML).join('\n');
    noIncluye(htmlGestor, 'data-estado-prod');
    noIncluye(htmlGestor, 'No disponible');
    noIncluye(htmlGestor, 'data-campo="moneda"');
    incluye(htmlGestor, 'CUP'); // la moneda sigue visible como texto
    incluye(htmlGestor, 'Guardar precio'); // el gestor sí puede cambiar el precio
  });
  await check('Gestor: guardar el precio NO envía moneda', async () => {
    SELECT_MONEDA_VISIBLE = false; // el gestor no tiene selector
    LLAMADAS.length = 0;
    fakePrecioBtn('1').onclick();
    await tick(); await tick();
    const llamada = LLAMADAS.find(c => c.action === 'update_proveedor');
    assert.ok(llamada, 'no se llamó a update_proveedor');
    eq(llamada.precio, 210);
    eq(llamada.moneda, undefined);
    SELECT_MONEDA_VISIBLE = true;
  });

  console.log('\n' + PASSED + ' checks pasaron.' + (process.exitCode ? ' HUBO FALLAS.' : ' TODO OK.'));
})();
