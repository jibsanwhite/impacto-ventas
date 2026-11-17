# Guía OMC Cloud — Prueba de 30 días para el renombrado de fotos de Impacto

**Para D.J. (Dariel Alonso), dueño de Alo Rico Rico. Solo necesitas tu teléfono Android.**

## Qué es esto y por qué

Esto es una **prueba gratis de 30 días** en OMC Cloud para comprobar que el renombrado de fotos de Impacto funciona solo, sin Max y sin tarjeta de crédito. El script con RapidOCR correrá en el servidor cada 15 minutos y renombrará las fotos que llegan de WhatsApp con nombres tipo `IMG-...-WA....jpg`, poniéndoles el código del producto.

**Lo importante de esta prueba:**

- **No pide tarjeta de crédito.** Te registras solo con correo y contraseña.
- **Nada se cobra solo.** Como no hay ningún método de pago guardado, a los 30 días el servidor simplemente se elimina si no decides seguir.
- **Un servidor de hasta 100 $.** Dentro de ese valor eliges la configuración que quieras.
- **Si la prueba funciona**, el hogar permanente sigue siendo Oracle Cloud gratis (o ClawCloud, o pagar OMC desde 4 $/mes). Esta prueba es solo para comprobar que todo corre sin Max.

Si el servidor no corre un día, **nada se rompe**: las fotos quedan con su nombre de WhatsApp y se emparejan a mano con el botón "Elegir de Drive". El trabajo manual sigue funcionando siempre.

**Regla de esta guía:** hay dos partes bien separadas. La Parte 1 es **LO QUE HACES TÚ** (cuenta, servidor y permisos, desde el teléfono). La Parte 2 es **LO QUE HACE MAX** (instalar, probar y activar el cron por SSH). Tú no tienes que escribir ningún comando ni usar ninguna terminal: eso lo hace Max.

---

# PARTE 1 — LO QUE HACES TÚ

## A) Crear la cuenta de OMC Cloud (sin tarjeta)

1. Abre el navegador del teléfono y entra a **omc.cloud/30-day-free-trial**.
2. Escribe tu **correo electrónico** y una **contraseña** para la cuenta de OMC. Toca **"Create an account"** (Crear cuenta) o **"Start my free trial"** (Empezar mi prueba gratis).
3. Si te llega un correo de OMC, ábrelo y toca el enlace de verificación para confirmar el correo.
4. Entra a la consola de OMC Cloud con tu correo y contraseña: **console.omc.cloud**. Ya tienes la cuenta.
5. **Guarda en un lugar seguro** (por ejemplo, en tus notas del teléfono): el correo de la cuenta de OMC y la contraseña. Max no necesita tu contraseña de OMC para nada: **no la pases por chat**.

## B) Crear el servidor

1. Entra a la consola de OMC Cloud desde el navegador del teléfono: **console.omc.cloud**. Inicia sesión con tu correo y contraseña.
2. Toca el botón **"Create New App"** (Crear nueva aplicación) o **"Create Server"** (Crear servidor).
3. Elige el **centro de datos (data center)**: **US: Florida, Miami**. Es el más cercano a Cuba. Si Miami no aparece en la lista, elige **US: New York, New York** o **US: Georgia, Atlanta**.
4. Elige el **sistema operativo**: **Ubuntu 22.04**. Si aparecen varias versiones de Ubuntu, elige la 22.04 normal (no "Minimal").
5. Elige el **tamaño del servidor**: **2 vCPU, 4 GB de RAM, 40 GB de disco**. La prueba cubre un servidor de hasta 100 $, así que este tamaño cabe de sobra. **OJO: no elijas el más pequeño (1 vCPU, 1 GB de RAM)**, porque el OCR necesita al menos 1–2 GB y con 1 GB puede quedarse sin memoria.
6. En el campo **"Name"** (Nombre), escribe: **impacto-renombrar**.
7. **Ponle una contraseña al servidor** (la contraseña de root). Tiene que ser una contraseña fuerte, distinta a las que usas en otros sitios. **Guárdala en tus notas**: la vas a necesitar para pasársela a Max de forma segura.
8. Toca el botón **"Create Server"** (Crear servidor) al final de la página.
9. Espera 2 o 3 minutos. Cuando el servidor pase a estado **"Running"** (En ejecución), toca su nombre para abrir sus detalles.
10. En la página de detalles, busca el campo **"Public IP"** (IP pública) y **anótala**: es un número con cuatro grupos separados por puntos (por ejemplo, 129.146.10.25). **Pásame esa IP por el chat.**
11. Si al crear el servidor te sale algún error, no hiciste nada mal: avísame con una captura y lo vemos juntos.

## C) Crear la cuenta de servicio de Google

La cuenta de servicio es una identidad "robot" de Google: no es una persona, es la credencial que el script del servidor usará para leer la Hoja y renombrar las fotos en Drive. Es **otra identidad distinta a Max**: aunque yo ya tengo permiso para renombrar, esta cuenta necesita que tú le compartas las carpetas por separado.

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
20. **Pásame ese archivo JSON a mí (Max)**: puedes enviármelo por el chat o subirlo a Drive y decirme dónde quedó. Yo lo coloco en el servidor como `/opt/impacto-tools/service-account.json`. **Nunca va a GitHub ni a ningún lugar público.**

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
5. Toca el selector de permiso y elige **"Lector"** (Viewer). La Hoja solo se lee, nunca se escribe desde el servidor.
6. **Desmarca** la casilla **"Notificar a las personas"**.
7. Toca **"Compartir"** (Share) o **"Enviar"**.

## E) Pasar la información a Max

Cuando termines todo lo de arriba, pásame por el chat estas 5 cosas:

1. La **IP pública** del servidor (paso B10).
2. El **archivo JSON** de la cuenta de servicio (paso C19-C20), por el chat o subido a Drive.
3. El **correo de la cuenta de servicio** (paso C15), para verificar los permisos.
4. La **contraseña del servidor** (paso B7): te la pediré por el formulario seguro, **no la escribas en el chat**. La uso una sola vez para entrar y poner mi propia llave; después ya no hace falta.
5. La **fecha en que creaste la cuenta**, para saber cuándo se acaban los 30 días.

Con eso yo instalo y pruebo. **No me pases tu contraseña de OMC ni tu contraseña de Google.**

---

# PARTE 2 — LO QUE HACE MAX

(Esta parte no la haces tú. Es lo que yo hago en el servidor, para que sepas qué esperar.)

1. Me conecto al servidor por SSH con la IP pública y la contraseña que me pasaste. En la primera entrada instalo mi propia llave SSH para no volver a usar la contraseña.
2. Copio el código del repo (carpeta `tools/`) al servidor, en `/opt/impacto-tools/`.
3. Coloco el JSON de la cuenta de servicio en `/opt/impacto-tools/service-account.json`. **Ese archivo nunca entra al repo ni a GitHub.**
4. Corro el instalador: `sudo bash /opt/impacto-tools/install.sh`. Instala Python, RapidOCR y las dependencias del script.
5. Hago la prueba en seco, sin renombrar nada: `python3 /opt/impacto-tools/renombrar_fotos.py --dry-run`. El registro queda en `/var/log/impacto-renombrar.log`.
6. **Te muestro el resultado de la prueba** (qué fotos renombraría y cuáles no pudo emparejar) y espero tu visto bueno.
7. Solo con tu visto bueno, activo el cron cada 15 minutos para que el script revise las carpetas solo. Una foto subida a las 10:03 queda renombrada a las 10:18 como tarde.
8. Te confirmo que el cron quedó activo y te digo qué día se hizo la primera corrida real.

---

# Advertencias honestas

- **La prueba dura 30 días.** Cuando se acaben, el servidor se elimina si no agregas un método de pago. Si la prueba funciona y quieres quedarte en OMC, el plan más barato es desde 4 $/mes; si no, el hogar permanente es Oracle Cloud gratis (guía GUIA-VPS-DJ.md) o ClawCloud.
- **No se cobra nada solo.** Como no hay tarjeta guardada, es imposible que te llegue un cobro sorpresa: sin pago, el servidor simplemente desaparece a los 30 días.
- **El JSON de la cuenta de servicio es una credencial**: trátalo como una contraseña. Nunca se publica, nunca se sube a GitHub, nunca se manda por un grupo. Va solo al servidor, en `/opt/impacto-tools/service-account.json`.
- **La contraseña del servidor también es una credencial**: solo me la pasas a mí, por el formulario seguro, y no se la pases a nadie más.
- **Si el servidor falla un día, el trabajo manual sigue funcionando**: las fotos quedan con su nombre de WhatsApp y se emparejan a mano con "Elegir de Drive". El servidor es un refuerzo, no una dependencia.
- **OMC es un proveedor más pequeño** (empresa holandesa, desde 1995, 25 centros de datos). La prueba es gratis y sin tarjeta, así que el riesgo es cero, pero no es el hogar permanente: para eso sigue Oracle.
- **No verifiqué si el registro funciona desde Cuba.** OMC no dice nada de Cuba en su página. Si al crear la cuenta te da error, avísame con una captura y lo vemos.

---

# Lista de verificación (checklist)

Marca cada casilla cuando lo tengas hecho:

- [ ] Cuenta de OMC Cloud creada (paso A).
- [ ] Servidor `impacto-renombrar` creado: Ubuntu 22.04, 2 vCPU / 4 GB RAM / 40 GB, centro de datos Miami.
- [ ] IP pública del servidor anotada.
- [ ] Contraseña del servidor guardada en tus notas.
- [ ] Fecha de creación de la cuenta anotada (para saber cuándo se acaban los 30 días).
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
- [ ] Contraseña del servidor pasada a Max por el formulario seguro.
- [ ] Prueba `--dry-run` de Max revisada y aprobada por ti.
- [ ] Cron cada 15 minutos activado por Max con tu visto bueno.

---

# Dudas sin verificar (para revisar en pantalla)

1. **Registro desde Cuba:** OMC no publica ninguna restricción por país, pero tampoco se verificó que el registro funcione desde una IP cubana. Si da error, avísame.
2. **Precio exacto del tamaño 2 vCPU / 4 GB:** la prueba cubre un servidor de hasta 100 $, así que cabe de sobra, pero el precio mensual exacto de ese tamaño se ve en la consola al crearlo. Si el precio que muestra es mayor de 15 $/mes, avísame antes de crear el servidor.
3. **Nombre exacto de la imagen de Ubuntu:** OMC recomienda Ubuntu 22.04 o superior. En la consola puede aparecer como "Ubuntu 22.04" o "Ubuntu 22.04 LTS". Elige la versión normal (no "Minimal") si te aparecen las dos.

---

*Fuentes consultadas (17/11/2026): página de prueba gratuita de OMC Cloud (omc.cloud/30-day-free-trial), página de centros de datos de OMC Cloud (omc.cloud/data-centers), página de OpenClaw de OMC Cloud (flujo de creación del servidor en console.omc.cloud), guía de hosting con prueba sin tarjeta de hostagentes.com.*
