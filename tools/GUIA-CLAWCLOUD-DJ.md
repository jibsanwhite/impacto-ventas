# Guía ClawCloud Run — Renombrado automático sin tarjeta, con QLPanel

**Para D.J. (Dariel Alonso), dueño de Alo Rico Rico. Solo necesitas tu teléfono Android.**

## Qué es esto y por qué

OMC Cloud quedó descartado: en el perfil de facturación pidió tarjeta y te rechazó, aunque su página dice que no hace falta. Así que vamos con la otra opción sin tarjeta: **ClawCloud Run**.

ClawCloud Run te da **5 $ de crédito todos los meses, sin tarjeta**, si tu cuenta de GitHub tiene más de 180 días. Tu cuenta (jibsanwhite) es de marzo de 2021, así que calificas. Con ese crédito corre un contenedor con **QLPanel**, un programador de tareas que ejecuta el script de renombrado (RapidOCR) cada 15 minutos.

**Lo importante de esta opción:**

- **No pide tarjeta de crédito.** Te registras con tu cuenta de GitHub.
- **El crédito se renueva cada mes.** Si el contenedor gasta menos de 5 $ al mes, no pagas nada nunca. La configuración de esta guía (CPU 0.5, RAM 1 GB) cuesta unos 0,15 $ al día, unos 4,50 $ al mes.
- **No es un VPS.** Es un contenedor: no hay cron del sistema ni acceso root por SSH. El que programa las tareas es QLPanel, que es justo para lo que sirve.
- **La duda grande es la RAM.** El OCR necesita 1–2 GB y aquí el contenedor llevará 1 GB. La primera prueba dirá si cabe o no. Si no cabe, subir la RAM puede pasar de los 5 $ y el contenedor se pararía: eso se mide primero, no se sube a ciegas.
- **Si funciona, este es el hogar permanente sin tarjeta.** Si no funciona, el plan B sigue siendo Oracle Cloud gratis (que sí pide tarjeta) o emparejar a mano.

Si el contenedor no corre un día, **nada se rompe**: las fotos quedan con su nombre de WhatsApp y se emparejan a mano con el botón "Elegir de Drive". El trabajo manual sigue funcionando siempre.

**Regla de esta guía:** hay dos partes bien separadas. La Parte 1 es **LO QUE HACES TÚ** (cuenta, QLPanel y permisos, desde el teléfono). La Parte 2 es **LO QUE HACE MAX** (subir el script, instalar dependencias y programar la tarea dentro de QLPanel). Tú no tienes que escribir ningún comando ni usar ninguna terminal: eso lo hace Max.

---

# PARTE 1 — LO QUE HACES TÚ

## A) Crear la cuenta de ClawCloud Run (sin tarjeta)

1. Abre el navegador del teléfono y entra a **console.run.claw.cloud**.
2. Toca **"Sign in with GitHub"** (Entrar con GitHub) o el botón de registro con GitHub.
3. Inicia sesión con tu cuenta de GitHub (**jibsanwhite**) y autoriza a ClawCloud a usarla para el registro. Si GitHub te pide el código 2FA, ponlo.
4. Cuando entres al panel de ClawCloud, busca el saldo o los créditos de la cuenta: tiene que aparecer el **crédito gratis de 5 $ al mes**. Si no aparece, avísame antes de seguir.
5. **Si en algún paso te pide una tarjeta de crédito, PARA y avísame.** Esta opción no debe pedirla.
6. **Guarda en un lugar seguro** (por ejemplo, en tus notas del teléfono): que entraste con GitHub. Max no necesita tu contraseña de GitHub para nada: **no la pases por chat**.

## B) Instalar QLPanel

1. En el panel de ClawCloud, toca **"App Store"** (Tienda de aplicaciones).
2. En el buscador, escribe **qinglong**.
3. Toca **"Deploy"** (Desplegar) en la aplicación **QLPanel (Qinglong)**.
4. Espera a que el estado cambie a **"Running"** (En ejecución). Toca **"Details"** (Detalles) a la derecha para ver la información del contenedor.
5. Baja hasta la tarjeta **"Network Management"** (Gestión de red) y ajusta los recursos: **CPU: 0.5** y **RAM: 1 GB**. **No subas la RAM por encima de 1 GB**: con más RAM el gasto mensual pasaría de los 5 $ de crédito y el contenedor se pararía.
6. Toca **"Update"** (Actualizar) para guardar los cambios.
7. En la misma tarjeta de "Network Management", toca la **dirección pública (URL)** del panel para abrir QLPanel. **Anota esa URL**: es la dirección del programador de tareas.
8. La primera vez que abras QLPanel, sigue el **asistente de configuración**: crea un **nombre de usuario y una contraseña** para QLPanel. **Guárdalos en tus notas**: me los pasarás de forma segura.
9. Entra a QLPanel con el usuario y la contraseña que acabas de crear. Ya está instalado.

## C) Crear la cuenta de servicio de Google

La cuenta de servicio es una identidad "robot" de Google: no es una persona, es la credencial que el script usará para leer la Hoja y renombrar las fotos en Drive. Es **otra identidad distinta a Max**: aunque yo ya tengo permiso para renombrar, esta cuenta necesita que tú le compartas las carpetas por separado.

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
20. **Pásame ese archivo JSON a mí (Max)**: puedes enviármelo por el chat o subirlo a Drive y decirme dónde quedó. Yo lo coloco dentro de QLPanel. **Nunca va a GitHub ni a ningún lugar público.**

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

Cuando termines todo lo de arriba, pásame por el chat estas 4 cosas:

1. La **URL pública de QLPanel** (paso B7).
2. El **archivo JSON** de la cuenta de servicio (paso C19-C20), por el chat o subido a Drive.
3. El **correo de la cuenta de servicio** (paso C15), para verificar los permisos.
4. El **usuario y la contraseña de QLPanel** (paso B8): te los pediré por el formulario seguro, **no los escribas en el chat**.

Con eso yo configuro la tarea. **No me pases tu contraseña de GitHub ni tu contraseña de Google.**

---

# PARTE 2 — LO QUE HACE MAX

(Esta parte no la haces tú. Es lo que yo hago dentro de QLPanel, para que sepas qué esperar.)

1. Entro a QLPanel con la URL y las credenciales que me pasaste.
2. Subo el script `renombrar_fotos.py` (el mismo del repo) y coloco el JSON de la cuenta de servicio dentro del contenedor. **Ese archivo nunca entra al repo ni a GitHub.**
3. Instalo las dependencias de Python del script (RapidOCR y las librerías de Google) desde el gestor de dependencias de QLPanel.
4. Creo la tarea programada en QLPanel: `python3 renombrar_fotos.py --live` **cada 15 minutos** (expresión cron `*/15 * * * *`).
5. Hago la prueba en seco primero, sin renombrar nada (`--dry-run`), para ver si el OCR cabe en 1 GB de RAM y qué fotos renombraría.
6. **Te muestro el resultado de la prueba** (qué fotos renombraría, si el OCR cupo en la RAM o no) y espero tu visto bueno.
7. Solo con tu visto bueno, activo la tarea cada 15 minutos. Una foto subida a las 10:03 queda renombrada a las 10:18 como tarde.
8. Te confirmo que la tarea quedó activa y te digo qué día se hizo la primera corrida real.

---

# Advertencias honestas

- **La RAM es la duda grande.** El contenedor llevará 1 GB y el OCR necesita 1–2 GB. La prueba en seco dirá si cabe. Si no cabe, subir la RAM puede pasar de los 5 $ de crédito y el contenedor se pararía: eso se mide primero, no se sube a ciegas.
- **Esto no es un VPS.** No hay cron del sistema ni SSH con root: todo pasa por QLPanel. Por eso la configuración la hago yo dentro del panel, no por terminal.
- **El crédito se renueva cada mes.** Con CPU 0.5 y RAM 1 GB el gasto es de unos 4,50 $ al mes, dentro de los 5 $. Si el contenedor gastara más, no te cobran nada porque no hay tarjeta guardada: se pararía.
- **El JSON de la cuenta de servicio es una credencial**: trátalo como una contraseña. Nunca se publica, nunca se sube a GitHub, nunca se manda por un grupo. Va solo dentro de QLPanel.
- **El usuario y la contraseña de QLPanel también son credenciales**: solo me los pasas a mí, por el formulario seguro, y no se los pases a nadie más.
- **Si el contenedor falla un día, el trabajo manual sigue funcionando**: las fotos quedan con su nombre de WhatsApp y se emparejan a mano con "Elegir de Drive". El contenedor es un refuerzo, no una dependencia.
- **OMC Cloud quedó descartado el 17/11**: su página dice que no pide tarjeta, pero en el perfil de facturación la pidió y te rechazó. Por eso vamos con ClawCloud.
- **No verifiqué si el registro funciona desde Cuba.** ClawCloud no dice nada de Cuba en su página. Si al entrar con GitHub te da error, avísame con una captura y lo vemos.

---

# Lista de verificación (checklist)

Marca cada casilla cuando lo tengas hecho:

- [ ] Cuenta de ClawCloud Run creada con GitHub (jibsanwhite).
- [ ] Crédito gratis de 5 $ al mes visible en la cuenta.
- [ ] QLPanel desplegado desde la App Store, estado "Running".
- [ ] Recursos ajustados: CPU 0.5, RAM 1 GB.
- [ ] URL pública de QLPanel anotada.
- [ ] Usuario y contraseña de QLPanel creados y guardados en tus notas.
- [ ] Proyecto `impacto-renombrar-fotos` creado en Google Cloud Console.
- [ ] API de Google Drive habilitada.
- [ ] API de Google Sheets habilitada.
- [ ] Cuenta de servicio `impacto-renombrar` creada.
- [ ] Correo de la cuenta de servicio anotado (termina en `@impacto-renombrar-fotos.iam.gserviceaccount.com`).
- [ ] Clave JSON descargada en el teléfono.
- [ ] Las 21 carpetas de Fotos compartidas con la cuenta de servicio (permiso Editor).
- [ ] Hoja "Impacto — Catálogo (datos)" compartida con la cuenta de servicio (permiso Lector).
- [ ] URL de QLPanel pasada a Max por el chat.
- [ ] Archivo JSON pasado a Max (por el chat o subido a Drive).
- [ ] Usuario y contraseña de QLPanel pasados a Max por el formulario seguro.
- [ ] Prueba `--dry-run` de Max revisada y aprobada por ti.
- [ ] Tarea cada 15 minutos activada por Max con tu visto bueno.

---

# Dudas sin verificar (para revisar en pantalla)

1. **Registro desde Cuba:** ClawCloud no publica ninguna restricción por país, pero tampoco se verificó que el registro con GitHub funcione desde una IP cubana. Si da error, avísame.
2. **RAM por defecto del contenedor de QLPanel:** la guía pide ajustar CPU a 0.5 y RAM a 1 GB. Si la consola muestra otros valores al desplegar, avísame antes de tocarlos.
3. **Ruta exacta para subir el JSON dentro de QLPanel:** Max la decide al ver el panel (subida de archivo o editor). Si no hay forma de subirlo, se buscará otra vía.
4. **Si RapidOCR cabe en 1 GB:** es lo que decide la prueba en seco. Si no cabe, se mide cuánto pide y se decide si vale la pena subir la RAM o buscar otro hogar.

---

*Fuentes consultadas (17/11/2026): guía de despliegue de QLPanel en ClawCloud Run (github.com/ClawCloud/Run-Blog, 2025-04-18), ficha de ClawCloud Run en toolin.ai (crédito de 5 $, sin tarjeta, sin apagado forzado), guía de hosting con prueba sin tarjeta de hostagentes.com.*
