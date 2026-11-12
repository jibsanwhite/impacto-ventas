# Impacto — Ventas

Página de catálogo para los gestores de la comunidad IMPACTO: ofertas de productos del hogar con varios proveedores por producto, pedido por WhatsApp y panel de gestión con login y roles.

## 🛒 Comunidad IMPACTO

IMPACTO es una comunidad de compraventa de productos del hogar (cocinas, neveras, ollas, colchones, splits, TV, lavadoras y más) para revender en los estados de WhatsApp. Los gestores ofrecen los productos a precio final y cobran una comisión por cada venta cerrada.

El precio base de cada publicación ya incluye:

- Producto nuevo con factura o comprobante de compra
- Comisión del gestor
- Domicilio dentro de la ciudad (zonas céntricas de Santiago)
- Garantía: 30 días para equipos grandes y de 7, 10, 15 o 20 días para equipos pequeños, según el proveedor

Queda prohibido aumentar el precio. La comisión se paga tras la entrega o en la noche. Se aceptan USD, Moneda Nacional y Euros (según el proveedor); algunos aceptan tarjeta Clásica, transferencia o Zelle.

## 🚀 Página en vivo

- Catálogo: https://impacto-ventas-gf9k.vercel.app
- Panel de gestión: https://impacto-ventas-gf9k.vercel.app/admin.html

La página lee el catálogo en vivo desde el backend (Google Apps Script + hoja de datos en Drive). `ofertas.json` es solo el respaldo que se muestra si el backend no responde.

## 📁 Estructura

```
├── index.html          # Catálogo público (HTML + CSS + JS en un solo archivo)
├── admin.html          # Panel de gestión (login, productos, proveedores, stock)
├── config.json         # URL del backend (Apps Script) y número de WhatsApp para pedidos
├── ofertas.json        # Catálogo de respaldo (se muestra si el backend no responde)
└── README.md           # Este archivo
```

## 🔧 Cómo funciona

1. **Frontend:** `index.html` es el catálogo público:
   - 🔍 Buscador, filtro por grupo y filtro por rango de precios y moneda
   - 👥 Elegir proveedor: cada producto puede tener varios proveedores con distinto precio, pago, garantía y domicilio; el más barato sale elegido por defecto
   - 📋 Detalles: características, precio, pago y domicilio del proveedor elegido
   - 💬 Pedir por WhatsApp: abre el pedido con el producto, el proveedor elegido, el precio y el pago
   - 📤 Compartir: texto corto listo para copiar en los estados

2. **Backend:** un Google Apps Script con la hoja de datos "Impacto — Catálogo (datos)" en Drive (pestañas Productos, Proveedores, Usuarios, Sesiones y Config) y la carpeta Fotos en Drive. Atiende el catálogo público, el login con roles, la gestión de productos y proveedores, el stock, las fotos y las acciones del panel (Pegar ofertas y Sincronizar ahora). El código del backend (Code.gs) vive en el proyecto de Apps Script, no en este repo; su URL vive en `config.json`.

3. **Datos:** la hoja en Drive es la fuente de verdad. Las ofertas se pegan en el espacio "Impacto — Ventas para estados" y se sincronizan a la hoja (productos, proveedores, precios, comisiones y fotos). Las fotos de Drive son la "Foto del vendedor"; las de Internet son de referencia. Los precios y las comisiones de cada proveedor viven en la hoja, nunca en el código.

## 👥 Usuarios y roles

El primer administrador se crea desde el panel cuando la tabla de usuarios está vacía, y el admin gestiona el resto desde 👥 Usuarios:

| Rol | Permisos |
|---|---|
| **administrador** | Todo: productos, proveedores, stock, fotos, usuarios |
| **gestor** | Ver el catálogo y sus propios proveedores con su comisión |
| **cliente** | Solo ver el catálogo |

- Las claves se guardan solo como huella SHA-256 (mínimo 8 caracteres).
- Sesiones con token de 24 horas.
- El catálogo público nunca muestra comisiones ni notas internas.

## 💰 Precios y comisiones

- El precio base ya incluye la comisión del gestor, el domicilio en ciudad y la garantía. Subir el precio está prohibido: la comisión no se paga hasta que pase el tiempo de garantía.
- La comisión se paga tras la entrega o en la noche, en el chat personal del gestor.
- El precio y la comisión pueden estar en monedas distintas (por ejemplo, venta en USD y comisión en CUP): nunca se infiere una de la otra.
- El domicilio está incluido solo en zonas céntricas; las zonas alejadas pagan un recargo. Si el cliente rechaza el producto, paga el domicilio igual.

## 📋 Historial y registro

- El historial de este repo está en los commits de GitHub.
- Los cambios de datos (precios, proveedores, stock, fotos) se hacen desde el panel de gestión o desde el espacio, y quedan en la hoja de datos.

## ⚠️ Privacidad

- **NUNCA** subas claves, tokens ni datos de clientes a este repositorio.
- `ofertas.json` lleva solo el catálogo público (productos, precios y proveedores con sus códigos internos). La hoja de datos con usuarios y sesiones vive en Drive, fuera de este repo.
- Las fotos de los vendedores viven en Drive; en el repo no hay fotos.

## 📝 Licencia

Uso privado.
