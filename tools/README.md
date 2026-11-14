# Herramientas de Impacto (proyecto sin IA)

Renombrado de fotos de vendedores por OCR, sin IA, sin tokens y sin
servicios de pago. Las fotos llegan a Google Drive como
`IMG-...-WA....jpg`, sin nombre de producto. Este script les pasa
RapidOCR (local), busca marca+modelo entre los productos "disponible"
del día y renombra el archivo en Drive cuando la coincidencia es única.

## Archivos

| Archivo | Qué es |
|---|---|
| `renombrar_fotos.py` | El script. Lee la Hoja, lista Fotos/\<GRUPO\>/ en Drive, OCR, empareja y renombra. |
| `test_renombrar.py` | Pruebas sin Google ni OCR en vivo: 96 casos contra los textos OCR reales de la prueba del 14/11 (`../ocr-test/ocr-textos-20261114.json`) y el JSON de productos. Se corre con `python3 test_renombrar.py`. |
| `requirements.txt` | `rapidocr-onnxruntime==1.4.4` + cliente de Google (Drive y Sheets). |
| `install.sh` | Instalación en el VPS (Ubuntu 22.04 ARM). Idempotente. |
| `README.md` | Este archivo. |

## Regla de seguridad (aprobada por D.J., innegociable)

- **Exactamente 1 candidato → renombrar.**
- 0 candidatos → no tocar, queda `sin_coincidencia`.
- 2 o más candidatos → no tocar, queda `ambiguo`.
- El OCR no devuelve texto → no tocar, queda `sin_texto`.
- **Solo se empareja contra tipo+modelo** (la identidad corta del
  producto). Las características NO se usan para puntuar: son fichas
  larguísimas y genéricas que casan con cualquier foto del grupo.
- Un renombre exige **al menos un token fuerte**: marca, código de
  modelo o medida con unidad (`#12`, `9kg`, `1 ton`, `43"`). Coincidir
  solo por palabras genéricas o por el tipo (`TV`, `bicicleta`,
  `split`) nunca renombra. Los números casan solo como token completo
  con unidad, nunca por subcadena dentro de otro número.
- Cuatro vetos antes de puntuar (solo pueden convertir un renombre en
  pendiente manual, nunca al revés):
  - **Veto de marca:** si en la foto se lee una marca (de la Hoja o de
    la lista curada de marcas vistas en fotos pero ausentes de la Hoja:
    `JMD`, `Midonkey`, `Laituning`, `Panther`, `Midea`, `Unizuki`…),
    solo quedan los candidatos de esa marca. La marca se reconoce
    también con 1 letra de error del OCR (`MIKAZUKI` → Mikasuki) en
    palabras de 6+ letras. Así una foto Mikasuki no se renombra como
    VEDCA, y una foto JMD no se renombra como la TV genérica de 43".
  - **Veto de tipo:** si la foto trae un tipo claro distinto al del
    candidato (`lavadora-secadora` no es `secadora a vapor`;
    `triciclo de carga` no es `bicicleta`), el candidato queda fuera.
  - **Veto de medida:** si la foto trae una medida que contradice la
    del candidato, fuera. Se comparan TODAS las medidas (kg, pulgadas,
    aro, voltios, vatios y capacidad: toneladas, K y BTU en la misma
    escala, 12K BTU = 1 ton). Así un split Milexus de 2 ton (24K) no
    se renombra como el de 1 ton.
  - **Veto de capacidad por familia de marca:** si la capacidad de la
    foto no la tiene NINGÚN producto de esa marca en el grupo, no queda
    ningún candidato de la marca (ni siquiera el que no declara
    capacidad en la Hoja). Así el split de 2 ton tampoco cae en el
    `Split Milexus` sin datos.
- **El precio impreso en la foto NUNCA manda.** Si difiere del precio de
  la Hoja, se renombra igual (puede estar desactualizado por una rebaja)
  y solo queda la advertencia `precio_foto_difiere` en el log.
  Manda el precio de la Hoja / del mensaje.
- El script **nunca borra, mueve ni sobrescribe nada**: solo cambia el
  nombre (`files.update` en Drive, `os.rename` en modo local).
- El nuevo nombre sigue el patrón ya en uso:
  `<Tipo>-<Marca>-<Modelo>-WAxxxx.jpg`
  (ej. `Lavadora-automatica-Wynwood-9kg-WA0107.jpg`). El id WA del
  nombre original se conserva para trazabilidad.
- El nombre sale **solo de tipo+modelo** (las características no
  entran: el nombre viejo del split llegaba a 600 caracteres), sin
  marcadores de la Hoja ("Pendiente Especificar",
  "en la imagen promocional"), sin paréntesis, sin la palabra "marca"
  (ni su errata "mara") y sin palabras repetidas ("Eko Eko" → "Eko").
  Se limita a **120 caracteres** en total. Si tras limpiar no queda
  nada distintivo, la foto NO se renombra.

## Instalación en el VPS (Oracle Cloud Always Free, ARM, Ubuntu 22.04)

```bash
git clone https://github.com/jibsanwhite/impacto-ventas.git
cd impacto-ventas/tools
sudo bash install.sh
```

Esto crea `/opt/impacto-tools`, un entorno virtual en
`/opt/impacto-tools/venv`, instala los requirements y verifica que
RapidOCR se importa. Se puede correr dos veces sin romper nada.

## Credenciales (cuenta de servicio de Google)

El JSON de la cuenta de servicio vive **fuera del repo**, en:

```
/opt/impacto-tools/service-account.json
```

Nunca se sube a GitHub. La cuenta necesita:

- Lectura de la Hoja "Impacto — Catálogo (datos)" (compartir la Hoja con
  el correo de la cuenta de servicio, como lector).
- Permiso de edición (renombrar) en la carpeta Fotos de Drive
  (compartir la carpeta con ese correo, como editor).

Scopes que usa el script: `https://www.googleapis.com/auth/drive` y
`https://www.googleapis.com/auth/spreadsheets.readonly`.

## Cómo correrlo

**Primero siempre en seco** (es el comportamiento por defecto, no
escribe nada en Drive):

```bash
/opt/impacto-tools/venv/bin/python /opt/impacto-tools/renombrar_fotos.py --dry-run
```

**Solo un grupo:**

```bash
/opt/impacto-tools/venv/bin/python /opt/impacto-tools/renombrar_fotos.py --dry-run --group LAVADORAS
```

**Renombrar de verdad** (solo después de revisar el dry-run):

```bash
/opt/impacto-tools/venv/bin/python /opt/impacto-tools/renombrar_fotos.py --live --credentials /opt/impacto-tools/service-account.json
```

**Guardar el registro en un archivo:**

```bash
/opt/impacto-tools/venv/bin/python /opt/impacto-tools/renombrar_fotos.py --live --log /var/log/impacto-renombrar.log
```

El script también acepta la variable de entorno
`GOOGLE_APPLICATION_CREDENTIALS` en vez de `--credentials`.

## Cron nocturna (02:00)

```cron
0 2 * * * /opt/impacto-tools/venv/bin/python /opt/impacto-tools/renombrar_fotos.py --live --credentials /opt/impacto-tools/service-account.json >> /var/log/impacto-renombrar.log 2>&1
```

## Modo local (pruebas sin Google)

Procesa fotos de una carpeta local contra un JSON de productos, sin
tocar ninguna API. El JSON es una lista de:

```json
[
  {"id": 72, "grupo": "LAVADORAS", "tipo": "Lavadora automática",
   "modelo": "Wynwood 9kg", "caracteristicas": "", "precio": 250,
   "moneda": "USD"}
]
```

```bash
python3 renombrar_fotos.py --dry-run --local-dir ./fotos-prueba --products-file ./productos-prueba.json
python3 renombrar_fotos.py --live --local-dir ./fotos-prueba --products-file ./productos-prueba.json
```

En modo local `--live` renombra los archivos en disco (y no sobrescribe
si el destino ya existe). Las subcarpetas se toman como grupo por su
nombre (`LAVADORAS-20261113` → `LAVADORAS`).

## Salida

Cada corrida imprime el log línea por línea (fecha-hora, archivo,
decisión, motivo, producto si aplica) y un resumen final:

```
RESUMEN:
  revisadas: 10
  renombradas: 7
  sin_texto: 1
  sin_coincidencia: 1
  ambiguo: 1
  precio_foto_difiere: 1
  error: 0
```

Código de salida 0 aunque haya fotos saltadas; distinto de 0 solo si
falla algo grave (sin credenciales, sin acceso a la Hoja, etc.).

## Notas

- OCR comparado el 13/11: RapidOCR 1.4.4 lee la marca en 14/22 fotos
  (64%) frente a 6/22 (27%) de Tesseract. La mayoría de las fotos
  promocionales no imprimen el precio: marca+modelo es el trabajo
  principal, el precio solo confirma cuando está.
- Solo se procesan archivos con nombre `IMG-AAAAMMDD-WAxxxx.jpg`;
  los ya renombrados se saltan.
- Sin credenciales, precios ni fotos dentro del código ni del repo.
