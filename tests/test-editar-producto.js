// Pruebas de la edición de productos en el panel (~/workspace/impacto):
// - El estado propio del producto es el interruptor general: si está
//   'vendido', el catálogo público lo muestra vendido aunque algún
//   proveedor tenga stock. Vacío = disponible (filas viejas).
// - update_producto (solo admin) escribe el estado; update_proveedor
//   (admin) corrige la moneda sin tocar el importe; el gestor no puede
//   cambiar la moneda (se ignora) ni el estado (rol no permitido).
// Mismo harness que test-parseo-backend.js: Code.gs en VM con la hoja y
// Drive simulados. Sin tocar la Hoja real ni el espacio.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const crypto = require('crypto');

// ---------- Mocks ----------
function makeSheet(rows) {
  return {
    rows,
    getDataRange() { return { getValues: () => this.rows.map(r => r.slice()) }; },
    appendRow(row) { this.rows.push(row.slice()); return this; },
    getRange(fila, col) {
      const self = this;
      return { setValue(v) { self.rows[fila - 1][col - 1] = v; }, getValue() { return self.rows[fila - 1][col - 1]; } };
    },
    deleteRow() { },
  };
}

const HOJAS = {};
function seedHojas() {
  HOJAS.Productos = makeSheet([
    ['id', 'grupo', 'tipo', 'modelo', 'caracteristicas', 'foto_url', 'foto_tipo', 'estado', 'creado', 'drive_id', 'nombre_archivo'],
    [1, 'TV', 'TV Premier 32" con barra', '', 'Con barra de sonido', 'https://drive.google.com/thumbnail?id=TV1&sz=w1000', 'vendedor', 'disponible', new Date('2026-11-13'), '', ''],
    [2, 'TV', 'TV Royal 50"', '', '', '', 'referencia', 'vendido', new Date('2026-11-13'), '', ''],
    [3, 'TV', 'TV Vivamax 32"', '', '', '', 'referencia', '', new Date('2026-11-13'), '', ''],
    [4, 'TV', 'TV Eko 43"', '', '', '', 'referencia', 'disponible', new Date('2026-11-13'), '', ''],
    [5, 'LAVADORAS', 'Lavadora automática', 'Milexus 7.5 kg', '', '', 'referencia', 'disponible', new Date('2026-11-13'), '', ''],
  ]);
  HOJAS.Proveedores = makeSheet([
    ['id', 'producto_id', 'proveedor', 'gestor_usuario', 'precio', 'moneda', 'stock_disponible', 'comision', 'comision_moneda', 'domicilio', 'garantia', 'notas_internas', 'pago'],
    [10, 1, 'Santiago 🍋', '', 210, 'USD', 'SI', 4000, 'MN', 'Incluido dentro de la ciudad', '10 días', '', 'USD, MN a precio toque'],
    [11, 2, 'Santiago 🍋', '', 300, 'USD', 'SI', 1000, 'MN', 'Incluido dentro de la ciudad', '10 días', '', 'USD'],
    [12, 3, 'Santiago 🍋', '', 250, 'USD', 'SI', 1000, 'MN', 'Incluido dentro de la ciudad', '10 días', '', 'USD'],
    [13, 4, 'Santiago 🍋', '', 200, 'USD', 'NO', 1000, 'MN', 'Incluido dentro de la ciudad', '10 días', '', 'USD'],
    [14, 5, 'Dos Caminos 🥑', 'nathali', 100, 'CUP', 'SI', 500, 'MN', 'Incluido', '1 mes', '', 'USD'],
    [15, 5, 'Dos Caminos 🍊', '', 210, 'CUP', 'SI', 1000, 'MN', 'Incluido', '10 días', '', 'USD'],
  ]);
  HOJAS.Usuarios = makeSheet([['usuario', 'nombre', 'rol', 'password_hash', 'activo', 'creado']]);
  HOJAS.Sesiones = makeSheet([
    ['token', 'usuario', 'rol', 'expira', 'creado'],
    ['tok-admin', 'alonso', 'administrador', new Date(Date.now() + 3600e3), new Date()],
    ['tok-gestor', 'nathali', 'gestor', new Date(Date.now() + 3600e3), new Date()],
  ]);
  HOJAS.Config = makeSheet([['clave', 'valor'], ['whatsapp_pedidos', '5358559794'], ['nombre_comunidad', 'Impacto'], ['resumen_hora', '20:00']]);
}

function mockFetch(url) {
  return { getResponseCode: () => 404, getContentText: () => '', getBlob: () => ({}) };
}

seedHojas();

const sandbox = {
  console,
  SpreadsheetApp: {
    openById() {
      return { getSheetByName: (n) => HOJAS[n] || null };
    },
  },
  DriveApp: {
    getFolderById: () => null,
    getFileById: () => null,
    Access: { ANYONE_WITH_LINK: 'ANYONE_WITH_LINK' },
    Permission: { VIEW: 'VIEW' },
  },
  UrlFetchApp: { fetch: (url, opts) => mockFetch(url) },
  Utilities: {
    computeDigest(algo, texto) {
      const h = crypto.createHash('sha256').update(texto, 'utf8').digest();
      return Array.from(h).map(b => (b > 127 ? b - 256 : b));
    },
    getUuid: (() => { let n = 0; return () => 'uuid-' + (++n); })(),
    base64Decode: (s) => Buffer.from(s, 'base64'),
    newBlob: (bytes, mime, nombre) => ({ getBytes: () => bytes }),
    Charset: { UTF_8: 'UTF-8' },
    DigestAlgorithm: { SHA_256: 'SHA-256' },
  },
  ContentService: {
    MimeType: { JSON: 'JSON' },
    createTextOutput(s) {
      const o = { _s: s, setMimeType() { return o; }, getContent() { return o._s; } };
      return o;
    },
  },
};
vm.createContext(sandbox);
const SRC = fs.readFileSync('/home/hatch/workspace/impacto/backend/Code.gs', 'utf8');
vm.runInContext(SRC, sandbox);
const G = (expr) => vm.runInContext(expr, sandbox);

HOJAS.Usuarios.rows.push(['alonso', 'Alonso', 'administrador', G(`sha256('clave1234')`), 'SI', new Date()]);

let PASSED = 0;
function check(nombre, fn) {
  try { fn(); PASSED++; console.log('  OK  ' + nombre); }
  catch (e) { console.log('  FALLA  ' + nombre + ' → ' + e.message); process.exitCode = 1; }
}
function eq(a, b, msg) { assert.strictEqual(a, b, (msg || '') + ' (esperado ' + JSON.stringify(b) + ', obtenido ' + JSON.stringify(a) + ')'); }

function post(action, extra, token) {
  const cuerpo = Object.assign({ action, token: token || 'tok-admin' }, extra || {});
  const out = G(`doPost({postData: {contents: ${JSON.stringify(JSON.stringify(cuerpo))}}})`);
  return JSON.parse(out.getContent());
}
function filaProducto(id) { return HOJAS.Productos.rows.find(r => r[0] === id); }
function filaProveedor(id) { return HOJAS.Proveedores.rows.find(r => r[0] === id); }
function catalogo() { return G(`catalogoPublico()`); }
function oferta(id) { return catalogo().ofertas.find(o => o.id === id); }

// ---------- TEST 1: el estado propio manda en el catálogo público ----------
console.log('\nTEST 1 — estado propio del producto en catalogoPublico()');
check('Prod 1 disponible + stock SI → disponible, precio_desde 210 USD', () => {
  const o = oferta(1);
  eq(o.estado, 'disponible'); eq(o.precio_desde, 210); eq(o.moneda, 'USD');
});
check('Prod 2 estado vendido + stock SI → vendido, precio_desde null', () => {
  const o = oferta(2);
  eq(o.estado, 'vendido'); eq(o.precio_desde, null);
});
check('Prod 3 estado vacío (fila vieja) + stock SI → disponible, precio_desde 250', () => {
  const o = oferta(3);
  eq(o.estado, 'disponible'); eq(o.precio_desde, 250);
});
check('Prod 4 disponible + sin stock → vendido, precio_desde null (regresión)', () => {
  const o = oferta(4);
  eq(o.estado, 'vendido'); eq(o.precio_desde, null);
});
check('Prod 5 disponible + 2 proveedores SI → disponible, precio_desde 100', () => {
  const o = oferta(5);
  eq(o.estado, 'disponible'); eq(o.precio_desde, 100);
});

// ---------- TEST 2: update_producto cambia el estado (solo admin) ----------
console.log('\nTEST 2 — update_producto (estado)');
check('Admin marca prod 1 como vendido: col 8 = vendido y el catálogo lo muestra vendido', () => {
  const r = post('update_producto', { id: 1, estado: 'vendido' });
  assert.ok(r.ok, 'update_producto falló: ' + JSON.stringify(r));
  eq(filaProducto(1)[7], 'vendido');
  const o = oferta(1);
  eq(o.estado, 'vendido'); eq(o.precio_desde, null);
});
check('Admin lo vuelve a disponible: col 8 = disponible y el catálogo vuelve a 210', () => {
  const r = post('update_producto', { id: 1, estado: 'disponible' });
  assert.ok(r.ok, 'update_producto falló: ' + JSON.stringify(r));
  eq(filaProducto(1)[7], 'disponible');
  const o = oferta(1);
  eq(o.estado, 'disponible'); eq(o.precio_desde, 210);
});
check('Gestor NO puede cambiar el estado (rol no permitido)', () => {
  const r = post('update_producto', { id: 1, estado: 'vendido' }, 'tok-gestor');
  assert.ok(!r.ok, 'el gestor no debería poder: ' + JSON.stringify(r));
  eq(filaProducto(1)[7], 'disponible');
});
check('Producto inexistente → error', () => {
  const r = post('update_producto', { id: 999, estado: 'vendido' });
  assert.ok(!r.ok, 'debía fallar: ' + JSON.stringify(r));
});

// ---------- TEST 3: update_proveedor corrige la moneda sin tocar el importe ----------
console.log('\nTEST 3 — update_proveedor (moneda)');
check('Caso que motivó el pedido: proveedor 15, 210 CUP → 210 USD (importe intacto)', () => {
  const r = post('update_proveedor', { id: 15, moneda: 'USD' });
  assert.ok(r.ok, 'update_proveedor falló: ' + JSON.stringify(r));
  eq(filaProveedor(15)[4], 210);
  eq(filaProveedor(15)[5], 'USD');
});
check('Admin cambia precio y moneda a la vez: 100 CUP → 120 USD', () => {
  const r = post('update_proveedor', { id: 14, precio: 120, moneda: 'USD' });
  assert.ok(r.ok, 'update_proveedor falló: ' + JSON.stringify(r));
  eq(filaProveedor(14)[4], 120);
  eq(filaProveedor(14)[5], 'USD');
});
check('Gestor propio: el precio cambia pero la moneda se ignora (sigue CUP)', () => {
  // Restauro la moneda del 14 a CUP para aislar el caso del gestor.
  HOJAS.Proveedores.rows.find(r => r[0] === 14)[5] = 'CUP';
  const r = post('update_proveedor', { id: 14, precio: 130, moneda: 'USD' }, 'tok-gestor');
  assert.ok(r.ok, 'update_proveedor del gestor falló: ' + JSON.stringify(r));
  eq(filaProveedor(14)[4], 130);
  eq(filaProveedor(14)[5], 'CUP');
});
check('Gestor NO puede tocar un proveedor ajeno', () => {
  const r = post('update_proveedor', { id: 15, precio: 999, moneda: 'MN' }, 'tok-gestor');
  assert.ok(!r.ok, 'debía fallar: ' + JSON.stringify(r));
  eq(filaProveedor(15)[4], 210);
  eq(filaProveedor(15)[5], 'USD');
});

console.log('\n' + PASSED + ' checks pasaron.' + (process.exitCode ? ' HUBO FALLAS.' : ' TODO OK.'));
