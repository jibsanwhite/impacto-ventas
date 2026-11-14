# Guía VPS — Renombrado automático de fotos de Impacto

**Para D.J. (Dariel Alonso), dueño de Alo Rico Rico. Solo necesitas tu teléfono Android.**

## Qué es esto y por qué

Esto es un servidor virtual gratis (VPS) en Oracle Cloud que cada noche a las 02:00 corre el script de renombrado de fotos de Impacto con RapidOCR. Sirve para que las fotos que llegan de WhatsApp con nombres tipo `IMG-...-WA....jpg` se renombren solas con el código del producto, aunque Max no esté disponible.

Si el VPS no corre un día, **nada se rompe**: las fotos quedan con su nombre de WhatsApp y se emparejan a mano con el botón "Elegir de Drive". El trabajo manual sigue funcionando siempre.

**Regla de esta guía:** hay dos partes bien separadas. La Parte 1 es **LO QUE HACES TÚ** (cuentas y permisos, desde el teléfono). La Parte 2 es **LO QUE HACE MAX** (instalar, probar y activar el cron por SSH). Tú no tienes que escribir ningún comando ni usar ninguna terminal: eso lo hace Max.

---

# PARTE 1 — LO QUE HACES TÚ

## A) Crear la cuenta de Oracle Cloud

1. Abre el navegador del teléfono y entra a **oracle.com/cloud/free**.
2. Toca el botón **"Start for free"** (o "Comienza gratis").
3. Escribe tu **correo electrónico** y una **contraseña** para la cuenta de Oracle. Toca **"Create account"** (Crear cuenta).
4. Revisa tu correo y abre el mensaje de Oracle. Toca el enlace de verificación para confirmar el correo.
5. Completa el formulario de registro: tu **nombre y apellidos**, **país (Cuba)** y **número de teléfono**. Toca **"Continue"** (Continuar).
6. **Elige la región principal (home region).** Es la lista desplegable que dice "Home Region". Elige la más cercana a ti, por ejemplo **US East (Ashburn)** o **São Paulo**. **OJO: esta región no se puede cambiar después.** Todos los recursos gratis tienen que crearse en esa región.
7. **Verificación con tarjeta.** Oracle te pedirá una **tarjeta de crédito o débito** para verificar tu identidad. Escribe los datos de la tarjeta y toca **"Verify"** (Verificar). Oracle hace una **retención temporal pequeña** en la tarjeta y luego la libera: **el tier Always Free no cobra nada por los recursos gratuitos**. Si la tarjeta no tiene fondos para la retención, la verificación falla: usa una tarjeta con saldo disponible.
8. Cuando el registro termine, entra a la consola de Oracle Cloud con tu correo y contraseña. Ya tienes la cuenta.
9. **Guarda en un lugar seguro** (por ejemplo, en tus notas del teléfono): el correo de la cuenta de Oracle y la contraseña. Max no necesita tu contraseña de Oracle para nada: **no la pases por chat**.

## B) Crear la instancia ARM (el servidor)

1. Entra a la consola de Oracle Cloud desde el navegador del teléfono: **cloud.oracle.com**. Inicia sesión con tu correo y contraseña.
2. Toca el **menú de hamburguesa (☰)** arriba a la izquierda.
3. Toca **"Compute"** y luego **"Instances"**.
4. Toca el botón **"Create instance"** (Crear instancia).
5. En el campo **"Name"** (Nombre), escribe: **impacto-renombrar**.
6. En la sección **"Image and shape"** (Imagen y forma), toca **"Change image"** (Cambiar imagen).
7. En la lista de imágenes, toca **"Ubuntu"** y elige **"Canonical Ubuntu 22.04"**. Toca **"Select image"** (Seleccionar imagen).
8. En la misma sección, toca **"Change shape"** (Cambiar forma).
9. Toca la categoría **"Ampere"** (ARM).
10. Toca el shape **"VM.Standard.A1.Flex"**.
11. Ajusta los deslizadores: **OCPU: 1** y **Memory (GB): 6**. Fíjate en que aparezca la etiqueta **"Always Free-eligible"** (elegible para Always Free) junto al shape: si no aparece, NO sigas, avísame.
12. En la sección **"Networking"** (Red), deja la opción de crear una **nueva VCN** (red virtual) con los valores por defecto. Asegúrate de que esté marcada la casilla **"Assign a public IPv4 address"** (Asignar una dirección IPv4 pública).
13. En la sección **"Add SSH keys"** (Agregar claves SSH), toca **"Generate a key pair for me"** (Generar un par de claves para mí). Toca **"Save private key"** (Guardar clave privada) y **"Save public key"** (Guardar clave pública) y guarda los dos archivos en el teléfono. **Pásame la clave PRIVADA a mí (Max) por el chat cuando te la pida, y no se la pases a nadie más: es la llave de entrada al servidor.**
14. En la sección **"Boot volume"** (Volumen de arranque), deja el tamaño por defecto. Fíjate en que también diga **"Always Free-eligible"**.
15. Toca el botón **"Create"** (Crear) al final de la página.
16. Espera 2 o 3 minutos. Cuando la instancia pase a estado **"Running"** (En ejecución), toca su nombre para abrir sus detalles.
17. En la página de detalles, busca el campo **"Public IP"** (IP pública) y **anótala**: es un número con cuatro grupos separados por puntos (por ejemplo, 129.146.10.25). **Pásame esa IP por el chat.**
18. Si al tocar "Create" te sale el error **"Out of capacity for shape VM.Standard.A1.Flex"**, no hiciste nada mal: significa que el hardware ARM gratuito de tu región está agotado en ese momento. Avísame y lo intentamos de nuevo otro día u otra hora; a veces hay que esperar días.

## C) Crear la cuenta de servicio de Google

La cuenta de servicio es una identidad "robot" de Google: no es una persona, es la credencial que el script del VPS usará para leer la Hoja y renombrar las fotos en Drive. Es **otra identidad distinta a Max**: aunque yo ya tengo permiso para renombrar, esta cuenta necesita que tú le compartas las carpetas por separado.

1. Abre el navegador del teléfono y entra a **console.cloud.google.com**. Inicia sesión con tu cuenta de Google (la misma que usas en Drive).
2. Toca el **selector de proyecto** arriba a la izquierda (donde dice el nombre del proyecto actual o "Seleccionar un proyecto").
3. Toca **"Nuevo proyecto"** (New project).
4. En el campo **"Nombre del proyecto"**, escribe: **impacto-renombrar-fotos**. Toca **"Crear"** (Create).
5. Espera a que se cree el proyecto y asegúrate de que arriba a la izquierda diga **impacto-renombrar-fotos**. Si dice otro proyecto, toca el selector y cámbialo.
6. Toca el **menú de hamburguesa (☰)** y luego **"APIs y servicios"** → **"Biblioteca"** (Library).
7. En el buscador de la Biblioteca, escribe **Google Drive API**. Toca el resultado **"Google Drive API"** y luego toca el botón **"Habilitar"** (Enable).
8. Vuelve a la Biblioteca (menú ☰ → "APIs y servicios" → "Biblioteca"). En el buscador, escribe **Google Sheets API**. Toca el resultado **"Google Sheets API"** y luego toca el botón **"Habilitar"** (Enable).
9. Toca el **menú de hamburguesa (☰)** y luego **"IAM y administración"** → **"Cuentas de servicio"** (Service Accounts).
10. Toca el botón **"Crear cuenta de servicio"** (Create Service Account).
11. En el campo **"Nombre de la cuenta de servicio"**, escribe: **impacto-renombrar**. Toca **"Crear y continuar"** (Create and Continue).
12. En la pantalla de permisos (roles), **no elijas ningún rol**: toca **"Continuar"** (Continue) directamente. (La cuenta no necesita roles de proyecto: sus permisos vienen de lo que tú le compartas en Drive.)
13. En la pantalla siguiente, toca **"Listo"** (Done).
14. En la lista de cuentas de servicio, toca la que acabas de crear (**impacto-renombrar**).
15. Copia el **correo de la cuenta de servicio**: es el que termina en **@impacto-renombrar-fotos.iam.gserviceaccount.com**. **Anótalo y pásamelo por el chat**: lo necesitaré para verificar que las carpetas se compartieron bien.
16. Toca la pestaña **"Claves"** (Keys).
17. Toca **"Agregar clave"** (Add Key) → **"Crear clave nueva"** (Create new key).
18. En la ventana que se abre, elige el tipo **JSON** y toca **"Crear"** (Create).
19. El navegador **descargará automáticamente un archivo .json** (su nombre será algo como `impacto-renombrar-fotos-xxxx.json`). **No lo abras, no lo edites, no lo subas a ningún sitio público.**
20. **Pásame ese archivo JSON a mí (Max)**: puedes enviármelo por el chat o subirlo a Drive y decirme dónde quedó. Yo lo coloco en el VPS como `/opt/impacto-tools/service-account.json`. **Nunca va a GitHub ni a ningún lugar público.**

## D) Compartir las carpetas de Fotos y la Hoja con la cuenta de servicio

La cuenta de servicio solo puede tocar lo que tú le compartas. Hay que compartirle **las 21 carpetas de categoría** (con permiso de Editor, para poder renombrar) y **la Hoja** (con permiso de Lector).

### D1) Las 21 carpetas (una por una)

1. Abre la app de **Google Drive** en el teléfono (o drive.google.com en el navegador).
2. Abre la carpeta **Fotos** (la que contiene las carpetas de categoría).
3. Para cada carpeta de la lista de abajo, haz lo siguiente:
   - Mantén pulsada la carpeta (o toca los **tres puntos ⋮** junto a su nombre).
   - Toca **"Compartir"** (Share).
   - En el campo de correo, escribe el **correo de la cuenta de servicio** que anotaste en el paso C15 (el que termina en `@impacto-renombrar-fotos.iam.gserviceaccount.com`).
   - Toca el selector de permiso y elige **"Editor"**.
   - **Desmarca** la casilla **"Notificar a las personas"** (no hace falta avisar a un robot).
   - Toca **"Compartir"** (Share) o **"Enviar"**.
4. Repite con las 21 carpetas:

   1. COCINAS
   2. ENERGÍA
   3. LAVADORAS
   4. TV
   5. HORNOS
   6. NEVERAS
   7. REFRIGERADORES
   8. SPLITS
   9. BOCINAS
   10. CAJITAS
   11. FREIDORAS
   12. OLLAS
   13. VENTILADORES
   14. LICUADORAS
   15. BASES
   16. CAFETERAS
   17. LUMINARIA
   18. COLCHONES
   19. TRANSPORTE
   20. MICROONDAS
   21. OTROS

   **Atajo si Drive te lo permite:** comparte la carpeta **Fotos** completa con permiso de Editor, y luego verifica que cada subcarpeta herede el permiso. Si alguna subcarpeta no lo hereda, compártela por separado como arriba.

### D2) La Hoja "Impacto — Catálogo (datos)"

1. Abre la app de **Google Sheets** en el teléfono (o la Hoja desde Drive).
2. Abre la Hoja **"Impacto — Catálogo (datos)"**.
3. Toca los **tres puntos ⋮** arriba a la derecha y luego **"Compartir y exportar"** → **"Compartir"** (o el icono de compartir).
4. En el campo de correo, escribe el **correo de la cuenta de servicio** (el mismo del paso C15).
5. Toca el selector de permiso y elige **"Lector"** (Viewer). La Hoja solo se lee, nunca se escribe desde el VPS.
6. **Desmarca** la casilla **"Notificar a las personas"**.
7. Toca **"Compartir"** (Share) o **"Enviar"**.

## E) Pasar la información a Max

Cuando termines todo lo de arriba, pásame por el chat estas 4 cosas:

1. La **IP pública** de la instancia (paso B17).
2. El **archivo JSON** de la cuenta de servicio (paso C19-C20), por el chat o subido a Drive.
3. La **clave privada SSH** que guardaste (paso B13), cuando yo te la pida.
4. El **correo de la cuenta de servicio** (paso C15), para verificar los permisos.

Con eso yo instalo y pruebo. **No me pases tu contraseña de Oracle ni tu contraseña de Google.**

---

# PARTE 2 — LO QUE HACE MAX

(Esta parte no la haces tú. Es lo que yo hago en el VPS, para que sepas qué esperar.)

1. Me conecto al VPS por SSH con la IP pública y la clave privada que me pasaste.
2. Copio el código del repo (carpeta `tools/`) al VPS, en `/opt/impacto-tools/`.
3. Coloco el JSON de la cuenta de servicio en `/opt/impacto-tools/service-account.json`. **Ese archivo nunca entra al repo ni a GitHub.**
4. Corro el instalador: `sudo bash /opt/impacto-tools/install.sh`. Instala Python, RapidOCR y las dependencias del script.
5. Hago la prueba en seco, sin renombrar nada: `python3 /opt/impacto-tools/renombrar_fotos.py --dry-run`. El registro queda en `/var/log/impacto-renombrar.log`.
6. **Te muestro el resultado de la prueba** (qué fotos renombraría y cuáles no pudo emparejar) y espero tu visto bueno.
7. Solo con tu visto bueno, activo el cron de cada noche a las 02:00 para que el script corra solo.
8. Te confirmo que el cron quedó activo y te digo qué día se hizo la primera corrida real.

---

# Advertencias honestas

- **El tier gratis de Oracle se mantiene mientras la instancia esté en uso**, pero Oracle puede suspender recursos inactivos o cambiar las condiciones del tier gratuito. Si algún día la instancia deja de existir, el renombrado vuelve a hacerse a mano: nada se pierde, las fotos y la Hoja siguen en Drive.
- **El límite gratuito ARM cambió en 2026**: las guías viejas dicen 4 OCPU / 24 GB, pero la documentación actual de Oracle habla de 2 OCPU / 12 GB en total para cuentas nuevas. Por eso esta guía usa **1 OCPU / 6 GB**: cabe dentro del límite nuevo y deja margen. Si Oracle te muestra otro límite en pantalla, avísame antes de crear la instancia.
- **El JSON de la cuenta de servicio es una credencial**: trátalo como una contraseña. Nunca se publica, nunca se sube a GitHub, nunca se manda por un grupo. Va solo al VPS, en `/opt/impacto-tools/service-account.json`.
- **La clave privada SSH también es una credencial**: solo me la pasas a mí, por el chat, y no se la pases a nadie más.
- **Si el VPS falla un día, el trabajo manual sigue funcionando**: las fotos quedan con su nombre de WhatsApp y se emparejan a mano con "Elegir de Drive". El VPS es un refuerzo, no una dependencia.
- **Capacidad ARM gratuita agotada:** si al crear la instancia sale "Out of capacity", es normal en algunas regiones y horas: hay que reintentarlo otro día. No es un error tuyo.
- **La región principal (home region) no se cambia después de elegirla.** Elige bien en el paso A6.

---

# Lista de verificación (checklist)

Marca cada casilla cuando lo tengas hecho:

- [ ] Cuenta de Oracle Cloud creada (paso A).
- [ ] Región principal elegida y anotada.
- [ ] Instancia `impacto-renombrar` creada: shape VM.Standard.A1.Flex, Ubuntu 22.04, 1 OCPU / 6 GB RAM, con etiqueta "Always Free-eligible".
- [ ] IP pública de la instancia anotada.
- [ ] Clave privada SSH guardada en el teléfono.
- [ ] Proyecto `impacto-renombrar-fotos` creado en Google Cloud Console.
- [ ] API de Google Drive habilitada.
- [ ] API de Google Sheets habilitada.
- [ ] Cuenta de servicio `impacto-renombrar` creada.
- [ ] Correo de la cuenta de servicio anotado (termina en `@impacto-renombrar-fotos.iam.gserviceaccount.com`).
- [ ] Clave JSON descargada en el teléfono.
- [ ] Las 21 carpetas de Fotos compartidas con la cuenta de servicio (permiso Editor).
- [ ] Hoja "Impacto — Catálogo (datos)" compartida con la cuenta de servicio (permiso Lector).
- [ ] IP pública pasada a Max por el chat.
- [ ] Archivo JSON pasado a Max (por el chat o subido a Drive).
- [ ] Clave privada SSH pasada a Max cuando la pida.
- [ ] Prueba `--dry-run` de Max revisada y aprobada por ti.
- [ ] Cron de las 02:00 activado por Max con tu visto bueno.

---

# Dudas sin verificar (para revisar en pantalla)

1. **Límite ARM Always Free en 2026:** varias guías actualizadas en 2026 dicen que Oracle recortó el límite a 2 OCPU / 12 GB totales, frente a los 4 OCPU / 24 GB de las guías viejas. La configuración de esta guía (1 OCPU / 6 GB) cabe en ambos límites, pero el número exacto que te muestre tu cuenta puede variar: fíjate en la etiqueta "Always Free-eligible" al crear la instancia.
2. **Monto de la retención de verificación de la tarjeta:** Oracle hace una retención temporal pequeña y la libera, pero el monto exacto varía según el país y la tarjeta. No se verificó un monto concreto para Cuba.
3. **Nombre exacto de la imagen de Ubuntu:** las guías coinciden en "Canonical Ubuntu 22.04", pero Oracle puede mostrarla como "Canonical Ubuntu 22.04" o "Ubuntu 22.04 Minimal aarch64". Elige la versión normal (no "Minimal") si te aparecen las dos.
4. **Disponibilidad de capacidad ARM en la región elegida:** el error "Out of capacity for shape VM.Standard.A1.Flex" es frecuente y depende de la región y la hora. No se puede verificar por adelantado qué región tendrá capacidad.

---

*Fuentes consultadas (13/11/2026): guía de Oracle Cloud Free Tier 2026 (subcreadores.com), guía de servidor gratis en Oracle Cloud 2026 (seoetico.com), guía de instancia Ampere A1 Ubuntu 22.04 (mundogps.org), tutorial de cuenta de servicio Google Cloud 2026 (javadex.es), guía de cuenta de servicio en n8n 2026 (dev.to), documentación de cuentas de servicio de Google (docs.cadense.io).*
