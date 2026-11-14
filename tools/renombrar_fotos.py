#!/usr/bin/env python3
"""
Renombrado de fotos de Impacto por OCR (proyecto sin IA).

Que hace:
  1. Lee los productos "disponible" de la Hoja "Impacto - Catalogo (datos)".
  2. Lista las fotos sin renombrar de Drive (carpeta Fotos/<GRUPO>/).
  3. Le pasa RapidOCR (local, gratis, sin tokens) a cada foto.
  4. Si marca+modelo del OCR coinciden con UN SOLO producto del grupo,
     renombra el archivo en Drive con el patron:
         <Tipo>-<Marca>-<Modelo>-WAxxxx.jpg
     Ejemplo real: Lavadora-automatica-Wynwood-9kg-WA0107.jpg
     El id WA del nombre original se conserva para trazabilidad.

REGLA DE SEGURIDAD (aprobada por D.J., innegociable):
  - Exactamente 1 candidato  -> renombrar.
  - 0 candidatos             -> NO tocar, queda "sin_coincidencia".
  - 2 o mas candidatos       -> NO tocar, queda "ambiguo".
  - El OCR no devuelve texto -> NO tocar, queda "sin_texto".
  - El precio impreso en la foto NUNCA manda: si difiere del precio de
    la Hoja, se renombra igual (puede estar desactualizado por una rebaja)
    y solo se registra la advertencia "precio_foto_difiere" en el log.
  - Solo se empareja contra tipo+modelo (la identidad corta del
    producto). Las caracteristicas NO se usan para puntuar: son fichas
    larguisimas y genericas que casan con cualquier foto del grupo.
  - Un renombre exige AL MENOS UN token fuerte: marca, codigo de modelo
    o medida con unidad (#12, 9kg, 1 ton, 43"). Coincidir solo por
    palabras genericas o por el tipo ("TV", "bicicleta", "split") nunca
    renombra. Los numeros casan solo como token completo con unidad,
    nunca por subcadena dentro de otro numero.
  - Cuatro vetos antes de puntuar (solo pueden convertir un renombre en
    pendiente manual, nunca al reves):
    * Veto de marca: si en la foto se lee una marca (de la Hoja o de la
      lista curada de marcas vistas en fotos pero ausentes de la Hoja:
      JMD, Midonkey, Laituning, Panther, Midea, Unizuki...), solo quedan
      los candidatos de esa marca. Asi una foto Mikasuki no se renombra
      como VEDCA, y una foto JMD no se renombra como la TV generica de
      43 pulgadas. La marca se reconoce tambien con 1 letra de error
      del OCR (MIKAZUKI -> Mikasuki) en palabras de 6+ letras.
    * Veto de tipo: si la foto trae un tipo claro distinto al del
      candidato ("lavadora-secadora" no es "secadora a vapor";
      "triciclo de carga" no es "bicicleta"), el candidato queda fuera.
    * Veto de medida: si la foto trae una medida que contradice la del
      candidato, fuera. Se comparan TODAS las medidas (kg, pulgadas,
      aro, voltios, vatios y capacidad: toneladas, K y BTU en la misma
      escala, 12K BTU = 1 ton). Asi un split Milexus de 2 ton (24K)
      no se renombra como el de 1 ton.
    * Veto de capacidad por familia de marca: si la capacidad que trae
      la foto no la tiene NINGUN producto de esa marca en el grupo, no
      queda ningun candidato de la marca (ni siquiera el que no declara
      capacidad en la Hoja). Asi el split de 2 ton tampoco cae en el
      "Split Milexus" sin datos.
  - El nombre nuevo sale SOLO de tipo+modelo, sin marcadores, sin
    palabras repetidas y con tope de 120 caracteres.
  - El script NUNCA borra, mueve ni sobrescribe nada: solo cambia el
    nombre (files.update) o, en modo local, renombra el archivo en disco.

Modos:
  - Por defecto es --dry-run: NO escribe nada, solo informa que haria.
  - --live es obligatorio para renombrar de verdad.
  - --local-dir <carpeta> + --products-file <json> procesa fotos locales
    contra un JSON de productos, sin tocar ninguna API de Google.
    Es el modo que usa el agente de pruebas.

Credenciales (solo para el modo Drive/Sheets):
  - Cuenta de servicio de Google, con el JSON en --credentials o en la
    variable de entorno GOOGLE_APPLICATION_CREDENTIALS.
  - El JSON vive FUERA del repo, por ejemplo en
    /opt/impacto-tools/service-account.json. Nunca se sube a GitHub.
  - Scopes: Drive completo (para renombrar) + Sheets solo lectura.

Salida: codigo 0 aunque haya fotos saltadas; distinto de 0 solo si falla
algo grave (sin credenciales, sin acceso a la Hoja, etc.).

Uso tipico:
  python3 renombrar_fotos.py --dry-run
  python3 renombrar_fotos.py --live --group LAVADORAS
  python3 renombrar_fotos.py --dry-run --local-dir ./fotos-prueba \\
      --products-file ./productos-prueba.json
"""

import argparse
import io
import json
import os
import re
import sys
import tempfile
import unicodedata
from datetime import datetime

# ---------------------------------------------------------------------------
# Constantes del proyecto (ids publicos del proyecto, no son secretos).
# Se pueden cambiar con --sheet-id y --photos-folder-id.
# ---------------------------------------------------------------------------
DEFAULT_SHEET_ID = "1Kn9inb-Zitgx_h-65OQ4q7YrA7tSegzTW0l7aNFmIhU"
DEFAULT_PHOTOS_FOLDER_ID = "13JcB0oGPWZkDXuo6O7Nr-HJpnzhVGEGh"

# Scopes de Google: Drive (renombrar) + Sheets (solo lectura).
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

# Nombre sin renombrar: IMG-20261113-WA0107.jpg (mayusculas/minusculas da igual).
SIN_RENOMBRAR_RE = re.compile(
    r"^IMG-\d{8}-WA\d+\.(jpg|jpeg|png)$", re.IGNORECASE
)
WA_ID_RE = re.compile(r"WA(\d+)", re.IGNORECASE)

# Palabras genericas que NO distinguen un producto de otro dentro de su grupo.
# NUNCA suman puntos: ni el tipo ("tv", "bicicleta", "split", "linterna")
# ni atributos que trae casi cualquier foto del grupo (solar, recargable,
# control, motor, bateria...). Sin ellas, una foto de una motorina
# cualquiera casaba con la VEDCA N3 por "motor, bateria, frenos, usb".
PALABRAS_GENERICAS = {
    "de", "con", "la", "el", "en", "y", "para", "por", "sin", "su", "del",
    "los", "las", "un", "una", "unos", "unas", "al", "a", "se",
    "lavadora", "lavadoras", "automatica", "automaticas", "automatico",
    "automaticos", "semiautomatica", "semiautomaticas",
    "secadora", "secadoras", "tv", "televisor", "televisores", "smart", "split", "splits",
    "aire", "acondicionado", "lampara", "lamparas", "luminaria", "luz",
    "calle", "bicicleta", "bicicletas", "bici", "bicimoto", "bicimotos",
    "motorina", "motorinas", "moto", "motos", "motocicleta", "motocicletas",
    "triciclo", "triciclos", "cocina", "cocinas", "horno", "hornos",
    "nevera", "neveras", "refrigerador", "refrigeradores", "freidora",
    "freidoras", "olla", "ollas", "ventilador", "ventiladores",
    "licuadora", "licuadoras", "cafetera", "cafeteras",
    "colchon", "colchones", "microondas", "bocina", "bocinas",
    "transporte", "farol", "reflector", "linterna",
    "arana", "colgante", "vapor",
    # Atributos genericos de las fichas: los trae cualquier foto del grupo.
    "solar", "recargable", "recargables", "control", "remoto", "electrica",
    "electricas", "electrico", "electricos", "electronica", "electronicas",
    "electronico", "electronicos",
    "motor", "bateria", "frenos", "freno", "voltaje", "usb", "bluetooth",
    "mp3", "nfc", "sensor", "movimiento", "duracion", "horas", "corriente",
    "capacidad", "potencia", "velocidad", "autonomia", "digital", "tablero",
    "boton", "encendido", "reproductor", "interna", "interno", "marca",
    "mara", "tipo", "volt", "led", "pulgada", "pulgadas", "tonelada",
    "toneladas",
}

# Rasgos que SI distinguen (estan en tipo+modelo y son propios de un
# producto o de muy pocos): "barra de sonido" frente a "cajita interna"
# distingue las dos TV Premier de 32"; "pista", "cambio" o "para ninos"
# igual. Suman puntos, pero NO bastan solos: un renombre exige ademas un
# token fuerte (marca, codigo o medida con unidad).
RASGOS_DISTINTIVOS = {
    "barra", "sonido", "cajita", "cajitas", "pista", "cambio", "ninos",
    "ninas", "pared", "base", "bases",
}

# Marcas vistas en fotos de vendedores pero AUSENTES de la Hoja: sin esta
# lista el veto de marca no las detecta (JMD no esta en ningun producto
# de la Hoja, y su foto se renombraba como la TV generica de 43"). Solo
# marcas que NO estan en la Hoja: si una marca esta en la Hoja, el veto
# la saca de los productos del grupo. Si aparece una marca nueva en una
# foto, se anade aqui (una linea) y el veto la cubre.
MARCAS_CURADAS = {
    "jmd", "midonkey", "laituning", "panther", "midea", "unizuki",
    "usuzuki", "eben",
}

# Caracteristicas que son solo un marcador ("pendiente"), no datos del
# producto: nunca deben acabar en el nombre del archivo renombrado.
CARACTERISTICAS_MARCADOR = {
    "pendiente especificar",
    "pendiente",
    "en la imagen promocional",
    "en la imagen",
    "en la foto promocional",
    "en la foto",
}

# Unidades de medida: un numero seguido de una de estas se une en un solo
# token ("1 ton" -> "1ton", "9 kg" -> "9kg"). "a"/"ah"/"km"/"hz" NO estan:
# amperios, kilometros y hercios son autonomia/velocidad, no capacidad,
# y compararlos vetaria fotos correctas (la VEDCA N3 dice "0km" porque
# es 0 km recorridos, no porque mida 0 km).
UNIDADES_MEDIDA = {"kg", "g", "ton", "v", "w", "kw", "kwh", "btu", "l", "ml",
                   "lb", "pulg", "aro", "k"}

# Unidades que se comparan en el veto de medida (pares y por familia).
# Capacidad = toneladas, K y BTU en la misma escala (12K BTU = 1 ton).
UNIDADES_VETO = {"kg", "g", "lb", "l", "ml", "pulg", "aro", "v", "w", "kw"}
UNIDADES_CAPACIDAD = {"ton", "k", "btu"}

# Palabras de unidad (el OCR las pega al numero: "1TONELADA", "32pulgadas").
_MAPA_UNIDAD = {
    "toneladas": "ton", "tonelada": "ton",
    "pulgadas": "pulg", "pulgada": "pulg", "inch": "pulg", "inches": "pulg",
    "kilogramos": "kg", "kilogramo": "kg",
    "libras": "lb", "libra": "lb",
    "voltios": "v", "voltio": "v",
    "watts": "w", "watt": "w", "vatios": "w", "vatio": "w",
    "kwh": "kw",
}
_PATRON_MEDIDA = re.compile(
    r"^(\d+(?:[.,]\d+)?)(kg|g|ton|k|v|w|kwh|kw|btu|lb|l|ml|hz|pulg|aro|km|ah|a|"
    r"toneladas?|pulgadas?|inch|inches|kilogramos?|libras?|voltios?|"
    r"watts?|vatios?)$")
# Igual que el anterior pero sin el "$": para casar una medida al inicio
# de un token pegado ("8kgmilexus" -> "8kg" + resto). Sin "a"/"ah": con
# ellos, "n3ah" se partia en "n"+"3ah" y el codigo N3 se perdia (la
# "n3Ah" es la bateria de 3Ah, no el modelo N3).
_PATRON_MEDIDA_INICIO = re.compile(
    r"^(\d+(?:[.,]\d+)?)(kg|g|ton|k|v|w|kwh|kw|btu|lb|l|ml|hz|pulg|aro|km|"
    r"toneladas?|pulgadas?|inch|inches|kilogramos?|libras?|voltios?|"
    r"watts?|vatios?)")

# Palabras que el OCR pega a otras ("Lavadorade8kg", "7.5kgMilexus",
# "MarcaEKO", "LAMPARASOLARCON"): el divisor las separa. Se construye en
# cada emparejamiento con las marcas del grupo + las genericas.
# Sin "farol": "FaroLED" (el faro de una moto) se partiria en "farol"
# y el veto de tipo lo confundiria con una lampara-farol. Como palabra
# suelta ("FAROL LL-7104S") se sigue detectando igual.
_PALABRAS_DIVISOR_BASE = (set(PALABRAS_GENERICAS) | RASGOS_DISTINTIVOS | {
    "capacidad", "voltaje", "frecuencia", "consumo", "funciones",
    "temporizador", "filtro", "ruido", "peso", "accesorios", "manual",
    "guia", "instalacion", "tuberias", "cobre", "espuma", "sellado",
    "drenaje", "condensados", "medidas", "estandar", "pilas", "basicas",
    "interior", "exterior", "refrigerante", "ecologico", "cobertura",
    "unidad", "pared", "sonido", "interna", "electrica", "electrico",
    "recargable", "lavado", "secado", "carga", "hibrido", "hibridos",
    "montana", "disco", "llantas", "suspension", "marco", "acero",
    "resistente", "potencia", "energia", "ahorro", "facil", "usar",
    "diseno", "moderno", "nueva", "nuevo", "disponible", "disponibles",
    "colores", "rojo", "azul", "negro", "blanco", "rosado", "morado",
    "pulgadas", "pulgada", "tonelada", "toneladas", "modelo",
}) - {"farol"}

# ---------------------------------------------------------------------------
# Normalizacion y emparejamiento (funciones puras, testeables sin Google)
# ---------------------------------------------------------------------------

def normalizar(texto):
    """Minusculas, sin tildes, guiones y comillas convertidos en espacios.

    Las medidas con unidad se conservan juntas y canonicas:
    - "#12" -> "aro12" (la "#" se pierde si no; "20" solo no es medida).
    - '43"' / '43″' / '43”' -> "43pulg" (la comilla se pierde si no).
    - "220-230V" -> "220v 230v" (un rango son sus dos extremos: la foto
      de un equipo 220-230V no contradice un producto de 220V).
    - "ñ" -> "n" (si no, "niños" se parte en "ni"+"os" y no casa nunca).
    """
    if not texto:
        return ""
    texto = str(texto)
    texto = texto.replace("ñ", "n").replace("Ñ", "n")
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.lower()
    texto = re.sub(r"#\s*(\d+(?:[.,]\d+)?)", r" aro\1 ", texto)
    # "Aro12"" es medida de aro, no pulgadas: la comilla es del aro.
    texto = re.sub(r"aro\s*(\d+(?:[.,]\d+)?)\s*[\"”″]", r" aro\1 ", texto)
    texto = re.sub(r"(\d+(?:[.,]\d+)?)\s*[\"”″]", r" \1pulg ", texto)
    texto = re.sub(
        r"(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*"
        r"(v|w|kwh|kw|kg|btu|ton|k|hz|a|ah|l|lb|pulg|km)",
        r" \1\3 \2\3 ", texto)
    texto = re.sub(r"[-_/\"'“”‘’()\[\]+×]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _numero_canonico(num_txt):
    """'12,000' -> '12000'; '12.000' -> '12000'; '7,5' -> '7.5';
    '9.0' -> '9'. La coma o el punto seguidos de 3 digitos son miles;
    si no, son decimales (norma cubana/latina)."""
    if "," in num_txt and "." not in num_txt:
        entero, dec = num_txt.split(",", 1)
        num_txt = entero + dec if len(dec) == 3 else entero + "." + dec
    elif "." in num_txt:
        entero, dec = num_txt.split(".", 1)
        if len(dec) == 3:
            num_txt = entero + dec
    try:
        valor = float(num_txt)
    except ValueError:
        return num_txt
    if valor == int(valor):
        return str(int(valor))
    return str(valor)


def _canonizar_medida(token):
    """'12,000btu' -> '12000btu'; '1tonelada' -> '1ton';
    '8.5inch' -> '8.5pulg'; '9.0kg' -> '9kg'. None si no es medida."""
    m = _PATRON_MEDIDA.match(token)
    if not m:
        return None
    unidad = _MAPA_UNIDAD.get(m.group(2), m.group(2))
    return _numero_canonico(m.group(1)) + unidad


def _despegar(token, vocab):
    """Parte un token pegado por el OCR en sus palabras.

    Ej: '7.5kgmilexus' -> ['7.5kg', 'milexus'];
    'lavadorade8kg' -> ['lavadora', 'de', '8kg'];
    'marcaeko' -> ['marca', 'eko']; 'oipremier' -> ['oi', 'premier'].
    Solo se parte por palabras del vocabulario (marcas del grupo,
    genericas, rasgos, unidades) o por una medida al inicio; lo demas
    queda entero ('zj150uk', 'n3ah' no se parten: 'n3ah' es la bateria
    de 3Ah, no el modelo N3).
    """
    if not token:
        return []
    partes = []
    resto = ""
    i = 0
    while i < len(token):
        # Medida al inicio del resto ("8kg..." -> "8kg").
        m = _PATRON_MEDIDA_INICIO.match(token[i:])
        if m:
            if resto:
                partes.append(resto)
                resto = ""
            partes.append(_canonizar_medida(m.group(0)))
            i += len(m.group(0))
            continue
        # Palabra del vocabulario mas larga que case aqui. Solo palabras
        # de 3+ letras: las de 2 ("de", "la", "un") parten marcas por
        # dentro ("rudenkov" -> "ru"+"de"+"nkov"); el "de" que queda
        # entre dos palabras conocidas sale solo como resto.
        mejor = None
        for palabra in vocab:
            if token.startswith(palabra, i) and (
                    mejor is None or len(palabra) > len(mejor)):
                mejor = palabra
        if mejor:
            if resto:
                partes.append(resto)
                resto = ""
            partes.append(mejor)
            i += len(mejor)
            continue
        resto += token[i]
        i += 1
    if resto:
        partes.append(resto)
    return partes


def tokens(texto, vocab_extra=None):
    """Palabras/numeros de un texto ya normalizado, con las pegadas partidas.

    Ej: '7.5kg' -> ['7.5kg']; '1 ton' -> ['1ton'];
    '7.5kgMilexus' -> ['7.5kg', 'milexus'].
    `vocab_extra` son las marcas del grupo (para partir 'Milexus' cuando
    viene pegada a otra palabra). Sin el, el divisor usa solo el
    vocabulario fijo.
    """
    vocab = set(_PALABRAS_DIVISOR_BASE) | set(MARCAS_CURADAS)
    if vocab_extra:
        vocab |= {str(v).lower() for v in vocab_extra}
    vocab = {v for v in vocab if len(v) >= 3}
    crudos = re.findall(r"[a-z0-9]+(?:[.,][0-9]+)?[a-z]*", normalizar(texto))
    salida = []
    i = 0
    while i < len(crudos):
        actual = crudos[i]
        medida = _canonizar_medida(actual)
        if medida is not None:
            salida.append(medida)
            i += 1
            continue
        if re.fullmatch(r"[0-9]+(?:[.,][0-9]+)?", actual) and i + 1 < len(crudos):
            # Numero + unidad, con abreviatura ("9 kg") o con palabra
            # ("55 pulgadas", "1 tonelada"): la misma medida.
            unidad = crudos[i + 1]
            if unidad in UNIDADES_MEDIDA:
                salida.append(_numero_canonico(actual) + unidad)
                i += 2
                continue
            if unidad in _MAPA_UNIDAD:
                salida.append(_numero_canonico(actual) + _MAPA_UNIDAD[unidad])
                i += 2
                continue
        salida.extend(_despegar(actual, vocab))
        i += 1
    return salida


def texto_identidad(producto):
    """Solo tipo+modelo: la identidad corta del producto.

    Las caracteristicas NO entran aqui: son fichas larguisimas y
    genericas ("Motor de 2000w, Velocidad max 50km/h, Autonomia 80km,
    Bateria LiFePO4, Boton de encendido, Tablero digital, Reproductor
    MP3...") que casan con cualquier foto del grupo.
    """
    return " ".join([
        str(producto.get("tipo") or ""),
        str(producto.get("modelo") or ""),
    ]).strip()


def tokens_identidad(producto, vocab_extra=None):
    """Tokens de tipo+modelo, con las palabras pegadas partidas."""
    return tokens(texto_identidad(producto), vocab_extra)


def _es_codigo(token):
    """True si el token parece un codigo de modelo: letras y digitos
    mezclados, sin ser una medida ('n3', 'zj150uk', '85vh5q', 'rled5025').
    '220v' o '12k' son medidas, no codigos."""
    if _canonizar_medida(token) is not None:
        return False
    if not re.search(r"[a-z]", token) or not re.search(r"[0-9]", token):
        return False
    return len(token) >= 2


def extraer_codigos(texto):
    """Codigos de modelo de un texto crudo, normalizados sin guiones.

    'ML-SPAC-12K-220V' -> {'mlspac12k220v'}; 'JD-ST-43' -> {'jdst43'};
    'ZJ150UK' -> {'zj150uk'}. Los codigos con guion se pierden si se
    tokeniza primero (el guion se vuelve espacio), por eso se sacan del
    texto crudo. Tambien recoge los codigos que ya son un token.
    """
    if not texto:
        return set()
    texto = normalizar(texto)
    codigos = set()
    for trozo in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)+", texto):
        junto = trozo.replace("-", "")
        if _es_codigo(junto):
            codigos.add(junto)
    for token in tokens(texto):
        if _es_codigo(token):
            codigos.add(token)
    return codigos


def codigos_de(producto):
    """Codigos de modelo de tipo+modelo (nunca de caracteristicas)."""
    return extraer_codigos(texto_identidad(producto))


def marcas_de(producto, vocab_extra=None):
    """Marcas del producto: palabras alfabeticas de tipo+modelo que no
    son genericas, ni rasgos, ni medidas, ni codigos.

    Ej: "Lavadora automatica Wynwood de 9 kg" -> {"wynwood"};
    "SPLIT 220V 1 TONELADA MILEXUS (VPT)" -> {"milexus", "vpt"};
    "Bicicletas #26" -> set() (no hay marca en la Hoja);
    "TV de 32 pulgadas Mara konka" -> {"konka"} ("mara" es la errata
    de "marca" y es generica).
    """
    return {
        t for t in tokens_identidad(producto, vocab_extra)
        if t.isalpha() and len(t) >= 3
        and t not in PALABRAS_GENERICAS
        and t not in RASGOS_DISTINTIVOS
    }


def marca_de(producto):
    """Compatibilidad: primera marca del producto, o None si no hay."""
    marcas = sorted(marcas_de(producto))
    return marcas[0] if marcas else None


def tokens_distintivos(producto, vocab_extra=None):
    """Tokens de tipo+modelo que distinguen al producto.

    Devuelve (fuertes, apoyo):
    - fuertes: marcas, codigos de modelo y medidas con unidad
      ("wynwood", "n3", "9kg", "1ton", "32pulg", "aro20"). Un renombre
      exige al menos uno de estos.
    - apoyo: rasgos ("barra", "cajita", "pista", "cambio", "ninos",
      "base", "pared"). Suman puntos y deshacen empates, pero solos
      nunca renombran.
    Las palabras genericas y los numeros sueltos ("20", "32", "55")
    no estan en ninguno de los dos: un numero solo casa por subcadena
    dentro de otro ("20" dentro de "210km") y no distingue nada.
    """
    fuertes = set()
    apoyo = set()
    for t in tokens_identidad(producto, vocab_extra):
        if t in PALABRAS_GENERICAS or len(t) < 2:
            continue
        if t in RASGOS_DISTINTIVOS:
            apoyo.add(t)
        elif t.isalpha() or _es_codigo(t) or _canonizar_medida(t):
            fuertes.add(t)
    for codigo in codigos_de(producto):
        fuertes.add(codigo)
    return fuertes, apoyo


def medidas_de_tokens(lista_tokens):
    """Medidas con unidad: {"kg": {"9"}, "v": {"220"}, "pulg": {"32"}}.

    La capacidad (ton, k, btu) va aparte, en toneladas, porque 12K BTU
    es 1 ton y hay que compararlas entre si (ver capacidad_toneladas).
    Solo se miran tokens con unidad: un numero suelto ("32", "20") no
    es una medida y vetar por el seria un error.
    """
    medidas = {}
    for t in lista_tokens:
        canonica = _canonizar_medida(t)
        if canonica is None:
            continue
        m = re.match(r"^(\d+(?:[.,]\d+)?|\d+)(kg|g|lb|l|ml|pulg|aro|v|w|kw)$",
                     canonica)
        if not m:
            continue
        medidas.setdefault(m.group(2), set()).add(
            _numero_canonico(m.group(1)))
    return medidas


def capacidad_toneladas(lista_tokens):
    """Capacidad en toneladas, de tokens ton/k/btu (12K BTU = 1 ton).

    "1ton" -> {1.0}; "12k" -> {1.0}; "12000btu" -> {1.0};
    "2k" (el split de 2 ton mal leido como 2K) -> {1/6}: distinto de
    1.0, asi que veta al de 1 ton. Devuelve set de floats redondeados.
    """
    toneladas = set()
    for t in lista_tokens:
        canonica = _canonizar_medida(t)
        if canonica is None:
            continue
        m = re.match(r"^(\d+(?:\.\d+)?)(ton|k|btu)$", canonica)
        if not m:
            continue
        valor = float(m.group(1))
        if m.group(2) == "ton":
            toneladas.add(round(valor, 3))
        elif m.group(2) == "k":
            toneladas.add(round(valor / 12.0, 3))
        else:  # btu
            toneladas.add(round(valor / 12000.0, 3))
    return toneladas


def hay_conflicto_medidas(medidas_ocr, ton_ocr, producto,
                          vocab_extra=None):
    """True si el OCR trae una medida que contradice la del producto.

    Se comparan TODAS las medidas con unidad que traigan ambos lados:
    kg, pulgadas, aro, voltios, vatios y capacidad (ton/k/btu en la
    misma escala). km, Hz y Ah NO se comparan: son autonomia, frecuencia
    y bateria, y vetarian fotos correctas (la VEDCA N3 dice "0km"
    porque es 0 km recorridos). Solo se compara cuando AMBOS traen esa
    unidad; si el OCR no trae la medida, no hay conflicto.
    """
    toks_prod = tokens_identidad(producto, vocab_extra)
    medidas_prod = medidas_de_tokens(toks_prod)
    for unidad, valores_ocr in medidas_ocr.items():
        valores_prod = medidas_prod.get(unidad)
        if valores_prod and not (valores_ocr & valores_prod):
            return True
    ton_prod = capacidad_toneladas(toks_prod)
    if ton_ocr and ton_prod and not (ton_ocr & ton_prod):
        return True
    return False


def tokens_capacidad(lista_tokens):
    """Compatibilidad: medidas con unidad como {"kg": {"9"}}."""
    return medidas_de_tokens(lista_tokens)


def hay_conflicto_capacidad(tokens_ocr, producto):
    """Compatibilidad: True si el OCR contradice una medida del producto."""
    return hay_conflicto_medidas(
        medidas_de_tokens(tokens_ocr),
        capacidad_toneladas(tokens_ocr), producto)


# --- Tipos de producto (para el veto de tipo) -------------------------------

def tipo_de_tokens(lista_tokens):
    """Tipo especifico que traen unos tokens, o None si no hay.

    "lavadora" + "secadora" juntos son "lavadora-secadora" (un combo,
    no una lavadora ni una secadora). "motocicleta" NO es un tipo: los
    vendedores llaman asi a bicimotos y a motos, no distingue.
    """
    t = set(lista_tokens)
    if "lavadora" in t or "lavadoras" in t:
        if "secadora" in t or "secadoras" in t:
            return "lavadora-secadora"
        return "lavadora"
    if "secadora" in t or "secadoras" in t:
        return "secadora"
    if "triciclo" in t or "triciclos" in t:
        if "carga" in t:
            return "triciclo-carga"
        return "triciclo"
    if "bicimoto" in t or "bicimotos" in t:
        return "bicimoto"
    if "motorina" in t or "motorinas" in t:
        return "motorina"
    if "moto" in t or "motos" in t:
        return "moto-electrica"
    if "bicicleta" in t or "bicicletas" in t or "bici" in t:
        return "bicicleta"
    if "aire" in t and "ventana" in t:
        return "aire-ventana"
    if "split" in t or "splits" in t:
        return "split"
    if "aire" in t:
        return "aire-acondicionado"
    if "lampara" in t or "lamparas" in t:
        if "pista" in t:
            return "lampara-pista"
        if "solar" in t:
            return "lampara-solar"
        return "lampara"
    if "luminaria" in t:
        return "lampara"
    if "luz" in t and "calle" in t:
        return "luz-calle"
    if "reflector" in t:
        return "reflector"
    if "farol" in t:
        return "farol"
    if "linterna" in t:
        return "linterna"
    if "arana" in t:
        return "arana"
    if "colgante" in t:
        return "colgante"
    if ("tv" in t or "televisor" in t or "televisores" in t
            or any(tok.startswith("smarttv") for tok in t)):
        return "tv"
    return None


_COMPAT_TIPO = {
    # Un tipo solo es compatible consigo mismo y con su generico.
    "lavadora-secadora": {"lavadora-secadora"},
    "lavadora": {"lavadora"},
    "secadora": {"secadora"},
    "split": {"split", "aire-acondicionado"},
    "aire-acondicionado": {"split", "aire-ventana", "aire-acondicionado"},
    "aire-ventana": {"aire-ventana", "aire-acondicionado"},
    "triciclo-carga": {"triciclo-carga", "triciclo"},
    "triciclo": {"triciclo", "triciclo-carga"},
    "bicimoto": {"bicimoto"},
    "motorina": {"motorina", "moto-electrica"},
    "moto-electrica": {"motorina", "moto-electrica"},
    "bicicleta": {"bicicleta"},
    "tv": {"tv"},
    "lampara": {"lampara", "lampara-solar", "lampara-pista"},
    "lampara-solar": {"lampara", "lampara-solar"},
    "lampara-pista": {"lampara", "lampara-pista"},
    "luz-calle": {"luz-calle"},
    "reflector": {"reflector"},
    "farol": {"farol"},
    "linterna": {"linterna"},
    "arana": {"arana"},
    "colgante": {"colgante"},
}


def tipo_de_producto(producto, vocab_extra=None):
    """Tipo especifico del producto, de su tipo+modelo."""
    return tipo_de_tokens(tokens_identidad(producto, vocab_extra))


def _levenshtein_1(a, b):
    """True si a y b se diferencian en 1 sola letra como mucho.

    El OCR confunde letras parecidas (MIKAZUKI por Mikasuki, MLEXUS por
    Milexus). Solo se aplica a marcas de 6+ letras: con menos, 1 letra
    de error es demasiado (SACO/SAPO, EKO/AKO).
    """
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    # Distancia de Levenshtein con parada temprana en 2.
    anterior = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        actual = [i]
        minimo = i
        for j, cb in enumerate(b, 1):
            coste = 0 if ca == cb else 1
            valor = min(anterior[j] + 1, actual[j - 1] + 1,
                        anterior[j - 1] + coste)
            actual.append(valor)
            minimo = min(minimo, valor)
        if minimo > 1:
            return False
        anterior = actual
    return anterior[-1] <= 1


def marcas_en_texto(tokens_ocr, marcas_conocidas):
    """Marcas que trae el OCR: exactas, o con 1 letra de error del OCR
    (solo palabras de 6+ letras). Devuelve el conjunto de marcas
    conocidas detectadas."""
    encontradas = set()
    for token in tokens_ocr:
        if token in marcas_conocidas:
            encontradas.add(token)
            continue
        if token.isalpha() and len(token) >= 6:
            for marca in marcas_conocidas:
                if len(marca) >= 6 and _levenshtein_1(token, marca):
                    encontradas.add(marca)
    return encontradas


def candidatos_por_puntuacion(texto_ocr, productos, vocab_extra=None,
                              marcas_ocr=None):
    """Devuelve [(producto, aciertos, fuertes, apoyo)] ordenado.

    Solo entran productos con al menos 1 token FUERTE acertado (marca,
    codigo o medida con unidad). Los rasgos solos no bastan. Una marca
    reconocida con 1 letra de error del OCR (MIKAZUKI -> Mikasuki)
    cuenta igual que la exacta: el veto ya la acepto como esa marca.
    """
    palabras_ocr = set(tokens(texto_ocr, vocab_extra))
    codigos_ocr = extraer_codigos(texto_ocr)
    resultado = []
    for producto in productos:
        fuertes, apoyo = tokens_distintivos(producto, vocab_extra)
        acertados_f = sorted(
            (fuertes & palabras_ocr) |
            (codigos_de(producto) & codigos_ocr) |
            (fuertes & (marcas_ocr or set())))
        acertados_a = sorted(apoyo & palabras_ocr)
        if acertados_f:
            resultado.append((producto, len(acertados_f) + len(acertados_a),
                              acertados_f, acertados_a))
    resultado.sort(key=lambda item: item[1], reverse=True)
    return resultado


def match_product(texto_ocr, productos):
    """Empareja el texto OCR con UN producto, o con ninguno.

    Devuelve (producto | None, motivo), donde motivo es uno de:
      "unico"           -> hay un solo candidato con la puntuacion maxima.
      "sin_coincidencia"-> ningun producto comparte tokens fuertes con el OCR.
      "ambiguo"         -> dos o mas productos empatan en la puntuacion maxima.
      "sin_texto"       -> el OCR no devolvio texto.

    Solo se puntua contra tipo+modelo. Un renombre exige al menos un
    token fuerte (marca, codigo o medida con unidad) y que el ganador
    tenga MAS aciertos que los demas; el empate en el maximo es ambiguo.

    Cuatro vetos de seguridad, antes de puntuar (solo pueden convertir
    un renombre en pendiente manual, nunca al reves):
    - Veto de marca: si en el OCR se lee una marca (de la Hoja o de la
      lista curada), solo quedan los candidatos de esa marca. Un
      candidato sin marca en la Hoja tambien queda fuera: la foto trae
      una marca legible y el producto no es de esa marca.
    - Veto de tipo: si la foto trae un tipo claro distinto al del
      candidato, fuera ("lavadora-secadora" no es "secadora a vapor").
    - Veto de medida: si el OCR trae una medida que contradice la del
      candidato (2 ton frente a 1 ton, 24K frente a 12K, 43" frente a
      32", 110V frente a 220V), fuera.
    - Veto de capacidad por familia de marca: si la capacidad de la
      foto no la tiene ningun producto de esa marca en el grupo, fuera
      todos los de la marca (el split de 2 ton no cae en el "Split
      Milexus" sin datos).
    """
    if not texto_ocr or not texto_ocr.strip():
        return None, "sin_texto"
    if not productos:
        return None, "sin_coincidencia"

    vocab_extra = set()
    for producto in productos:
        vocab_extra |= marcas_de(producto)
    vocab_extra |= MARCAS_CURADAS

    toks_ocr = tokens(texto_ocr, vocab_extra)
    set_ocr = set(toks_ocr)
    medidas_ocr = medidas_de_tokens(set_ocr)
    ton_ocr = capacidad_toneladas(set_ocr)
    tipo_ocr = tipo_de_tokens(set_ocr)

    # 1. Veto de marca (Hoja + lista curada; con 1 letra de error OCR).
    marcas_ocr = marcas_en_texto(set_ocr, vocab_extra)
    candidatos = list(productos)
    if marcas_ocr:
        candidatos = [p for p in candidatos
                      if marcas_de(p, vocab_extra) & marcas_ocr]
        if not candidatos:
            return None, "sin_coincidencia"

    # 2. Veto de tipo.
    if tipo_ocr:
        candidatos = [p for p in candidatos
                      if tipo_de_producto(p, vocab_extra) is None
                      or tipo_de_producto(p, vocab_extra)
                      in _COMPAT_TIPO.get(tipo_ocr, {tipo_ocr})]
        if not candidatos:
            return None, "sin_coincidencia"

    # 3. Veto de medida (todas las medidas con unidad).
    candidatos = [p for p in candidatos
                  if not hay_conflicto_medidas(medidas_ocr, ton_ocr, p,
                                               vocab_extra)]
    if not candidatos:
        return None, "sin_coincidencia"

    # 4. Veto de capacidad por familia de marca.
    if marcas_ocr and ton_ocr:
        for marca in sorted(marcas_ocr):
            familia = [p for p in productos
                       if marca in marcas_de(p, vocab_extra)]
            tons_familia = set()
            for p in familia:
                tons_familia |= capacidad_toneladas(
                    tokens_identidad(p, vocab_extra))
            if tons_familia and not (ton_ocr & tons_familia):
                candidatos = [p for p in candidatos
                              if marca not in marcas_de(p, vocab_extra)]
        if not candidatos:
            return None, "sin_coincidencia"

    puntuados = candidatos_por_puntuacion(texto_ocr, candidatos, vocab_extra,
                                          marcas_ocr)
    if not puntuados:
        return None, "sin_coincidencia"

    mejor_puntuacion = puntuados[0][1]
    mejores = [p for p in puntuados if p[1] == mejor_puntuacion]
    if len(mejores) > 1:
        return None, "ambiguo"

    producto, _aciertos, _fuertes, _apoyo = mejores[0]
    return producto, "unico"


def precio_foto_difiere(texto_ocr, producto):
    """True si la foto trae un numero de precio distinto al de la Hoja.

    Solo es una advertencia: NUNCA bloquea el renombre. El precio de la
    foto puede estar desactualizado (rebaja) y manda el de la Hoja.
    Solo se miran numeros sueltos >= 100 que no sean medidas (220V,
    5000 BTU, 9kg...) ni codigos de modelo. Si la Hoja no trae precio,
    no hay nada con que comparar y devuelve False.
    """
    precio = producto.get("precio")
    if precio is None or precio == "":
        return False
    try:
        precio_hoja = float(str(precio).replace(",", "").replace("$", ""))
    except ValueError:
        return False

    # Numeros del texto OCR, con la unidad que les sigue (si la hay).
    numeros = re.findall(r"(\d[\d.,]*)\s*([a-z%]*)", normalizar(texto_ocr))
    unidades_medida = UNIDADES_MEDIDA | {"%"}
    for numero_txt, unidad in numeros:
        if unidad in unidades_medida:
            continue
        try:
            numero = float(numero_txt.replace(",", ""))
        except ValueError:
            continue
        if numero < 100:
            continue
        if abs(numero - precio_hoja) > 0.01:
            return True
        return False  # Hay un precio y coincide: no hay diferencia.
    return False


# Palabras de enlace que no entran en el nombre renombrado. Las de tipo
# ("Lavadora", "Tv", "Split") SI entran: son el <producto> del patron.
_PALABRAS_NOMBRE_ENLACE = {
    "de", "con", "la", "el", "en", "y", "para", "por", "sin", "su", "del",
    "los", "las", "un", "una", "unos", "unas", "al", "a", "se",
}

# Marcadores que nunca entran en el nombre renombrado (por si aparecen
# en tipo/modelo y no solo en caracteristicas).
_PALABRAS_NOMBRE_FUERA = {
    "pendiente", "especificar", "imagen", "promocional", "foto", "fotos",
}


def construir_nombre(producto, nombre_original):
    """Nuevo nombre: <Tipo>-<Marca>-<Modelo>-WAxxxx.jpg, o None.

    - SOLO tipo+modelo de la Hoja (las caracteristicas NO entran: son
      fichas enteras y el nombre viejo del split llegaba a 600 caracteres).
    - Sin marcadores ("pendiente especificar", "en la imagen
      promocional", "en la foto"), sin parentesis ("(VPT)", "(no lava
      la ropa solo seca)"), sin la palabra "marca" (ni su errata
      "mara": "Mara konka" -> "Konka") y sin palabras de enlace
      ("de", "con", "la", "el"...).
    - Sin palabras repetidas ("Eko Eko" -> "Eko"; "Tv Premier ... con
      Tv Premier ..." -> "Tv-Premier...").
    - El id WA se conserva del nombre original (trazabilidad) y la
      extension tambien (.jpg, .jpeg o .png).
    - Tope de 120 caracteres en total. Si tras limpiar no queda nada
      distintivo, devuelve None y la foto NO se renombra (queda como
      pendiente manual en vez de llamarse "Producto-WA....jpg").
    """
    match_wa = WA_ID_RE.search(nombre_original or "")
    wa = "WA" + match_wa.group(1).zfill(4) if match_wa else "WA0000"
    extension = os.path.splitext(nombre_original or "")[1].lower() or ".jpg"

    texto = texto_identidad(producto)
    # Quitar parentesis con su contenido ("(VPT)", "(no lava...)").
    texto = re.sub(r"\([^)]*\)", " ", texto)
    palabras = []
    vistos = set()
    for palabra in tokens(texto):
        # Palabras de enlace ("de", "con"...), "marca" (y su errata
        # "mara") y marcadores ("pendiente especificar", "en la imagen
        # promocional") no entran en el nombre. Las de tipo si entran:
        # "Lavadora-Automatica-Wynwood-9kg" es el patron en uso.
        if (palabra in _PALABRAS_NOMBRE_ENLACE
                or palabra in ("marca", "mara")
                or palabra in _PALABRAS_NOMBRE_FUERA):
            continue
        if len(palabra) < 2:
            continue
        if palabra in vistos:
            continue
        vistos.add(palabra)
        palabras.append(palabra.capitalize())
    if not palabras:
        return None
    base = "-".join(palabras)
    sufijo = "-" + wa + extension
    max_base = 120 - len(sufijo)
    if len(base) > max_base:
        base = base[:max_base].rstrip("-")
    return base + sufijo


def grupo_desde_carpeta(ruta_carpeta):
    """Grupo a partir de una carpeta local: 'LAVADORAS-20261113' -> 'LAVADORAS'."""
    nombre = os.path.basename(os.path.normpath(ruta_carpeta))
    nombre = re.sub(r"-\d{8}$", "", nombre)  # quita el sufijo -AAAAMMDD
    return nombre.upper()


# ---------------------------------------------------------------------------
# OCR (RapidOCR, local)
# ---------------------------------------------------------------------------

_motor_ocr = None


def leer_texto_ocr(ruta_foto):
    """Pasa RapidOCR a una foto y devuelve todo el texto junto en un string."""
    global _motor_ocr
    if _motor_ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _motor_ocr = RapidOCR()
    resultado, _ = _motor_ocr(str(ruta_foto))
    if not resultado:
        return ""
    return " ".join(texto for _, texto, _ in resultado)


# ---------------------------------------------------------------------------
# Registro (log) y resumen
# ---------------------------------------------------------------------------

class Registro:
    """Log linea por linea + contadores del resumen final."""

    def __init__(self, ruta_log=None):
        self.ruta_log = ruta_log
        self.archivo = open(ruta_log, "a", encoding="utf-8") if ruta_log else None
        self.conteos = {
            "revisadas": 0,
            "renombradas": 0,
            "sin_texto": 0,
            "sin_coincidencia": 0,
            "ambiguo": 0,
            "precio_foto_difiere": 0,
            "error": 0,
        }

    def linea(self, archivo, decision, motivo, producto=None):
        """Una linea de log: fecha-hora, archivo, decision, motivo, producto."""
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        nombre_producto = ""
        if producto:
            nombre_producto = " | producto=%s id=%s" % (
                " ".join(str(producto.get(k) or "") for k in
                         ("tipo", "modelo")).strip(),
                producto.get("id", ""),
            )
        texto = "[%s] %s | %s | %s%s" % (
            ahora, archivo, decision, motivo, nombre_producto)
        print(texto, flush=True)
        if self.archivo:
            self.archivo.write(texto + "\n")
            self.archivo.flush()
        if decision in self.conteos:
            self.conteos[decision] += 1
        if motivo == "precio_foto_difiere":
            self.conteos["precio_foto_difiere"] += 1

    def resumen(self):
        lineas = ["", "RESUMEN:"]
        for clave in ("revisadas", "renombradas", "sin_texto",
                      "sin_coincidencia", "ambiguo", "precio_foto_difiere",
                      "error"):
            lineas.append("  %s: %d" % (clave, self.conteos[clave]))
        texto = "\n".join(lineas)
        print(texto, flush=True)
        if self.archivo:
            self.archivo.write(texto + "\n")
            self.archivo.close()


# ---------------------------------------------------------------------------
# Procesar UNA foto (comun al modo Drive y al modo local)
# ---------------------------------------------------------------------------

def procesar_foto(nombre_archivo, ruta_local, productos_del_grupo, registro,
                  en_vivo, renombrar):
    """OCR + emparejamiento + (si toca) renombre de una foto.

    'renombrar' es una funcion (nombre_archivo, nuevo_nombre) que hace el
    renombre real en Drive o en disco. Solo se llama en modo --live.
    Devuelve el nuevo nombre o None.
    """
    registro.conteos["revisadas"] += 1
    try:
        texto_ocr = leer_texto_ocr(ruta_local)
    except Exception as error:  # noqa: BLE001 - el OCR no debe tumbar la corrida
        registro.linea(nombre_archivo, "error", "ocr_fallo: %s" % error)
        return None

    producto, motivo = match_product(texto_ocr, productos_del_grupo)
    if producto is None:
        registro.linea(nombre_archivo, motivo, motivo)
        return None

    nuevo_nombre = construir_nombre(producto, nombre_archivo)
    if nuevo_nombre is None:
        # Tras limpiar tipo+modelo no queda nada distintivo: no se
        # renombra (un "Producto-WA....jpg" no dice nada y tapa el
        # trabajo manual). Queda como pendiente manual.
        registro.linea(nombre_archivo, "sin_coincidencia",
                       "sin_nombre_distintivo", producto)
        return None
    advertencia = ""
    if precio_foto_difiere(texto_ocr, producto):
        # Advertencia, NO bloqueo: el precio de la Hoja manda.
        advertencia = "precio_foto_difiere"
        registro.conteos["precio_foto_difiere"] += 1

    if not en_vivo:
        registro.linea(nombre_archivo, "renombradas",
                       "dry-run -> %s%s" % (
                           nuevo_nombre,
                           " | ADVERTENCIA: " + advertencia if advertencia else ""),
                       producto)
        # En dry-run se cuenta como "renombrada" (lo que se haria).
        return nuevo_nombre

    if nuevo_nombre.lower() == nombre_archivo.lower():
        registro.linea(nombre_archivo, "renombradas",
                       "ya_tenia_ese_nombre", producto)
        return nuevo_nombre

    try:
        renombrar(nombre_archivo, nuevo_nombre)
    except Exception as error:  # noqa: BLE001 - seguir con la siguiente foto
        registro.linea(nombre_archivo, "error", "renombre_fallo: %s" % error)
        return None
    registro.linea(nombre_archivo, "renombradas",
                   "renombrado -> %s%s" % (
                       nuevo_nombre,
                       " | ADVERTENCIA: " + advertencia if advertencia else ""),
                   producto)
    return nuevo_nombre


# ---------------------------------------------------------------------------
# Modo local (sin Google): fotos en disco + JSON de productos
# ---------------------------------------------------------------------------

def cargar_productos_json(ruta):
    """JSON: lista de {id, grupo, tipo, modelo, caracteristicas, precio, moneda}."""
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    if isinstance(datos, dict):
        datos = datos.get("productos", [])
    return [p for p in datos if isinstance(p, dict)]


def modo_local(carpeta, ruta_productos, grupo_filtro, en_vivo, registro):
    """Procesa fotos locales. En --live renombra los archivos en disco."""
    productos = cargar_productos_json(ruta_productos)
    if not productos:
        print("ERROR: el JSON de productos esta vacio o no tiene productos.",
              file=sys.stderr)
        return 2

    # Recoger fotos: archivos IMG-...-WA.... en la carpeta y subcarpetas.
    fotos = []
    for raiz, _dirs, archivos in os.walk(carpeta):
        for nombre in sorted(archivos):
            if not SIN_RENOMBRAR_RE.match(nombre):
                continue  # ya renombradas o no son fotos de WhatsApp: se saltan
            ruta = os.path.join(raiz, nombre)
            if os.path.abspath(raiz) == os.path.abspath(carpeta):
                grupo = grupo_filtro or None
            else:
                grupo = grupo_desde_carpeta(raiz)
            fotos.append((nombre, ruta, grupo))

    if grupo_filtro:
        fotos = [f for f in fotos
                 if f[2] is None or f[2] == grupo_filtro.upper()]

    print("Modo local: %d fotos sin renombrar en %s" % (len(fotos), carpeta))
    for nombre, ruta, grupo in fotos:
        if grupo:
            del_grupo = [p for p in productos
                         if str(p.get("grupo") or "").upper() == grupo]
        else:
            del_grupo = productos

        def renombrar_local(_viejo, nuevo, ruta=ruta):
            destino = os.path.join(os.path.dirname(ruta), nuevo)
            if os.path.exists(destino):
                raise FileExistsError("ya existe %s, no se sobrescribe" % nuevo)
            os.rename(ruta, destino)

        procesar_foto(nombre, ruta, del_grupo, registro, en_vivo,
                      renombrar_local)
    registro.resumen()
    return 0


# ---------------------------------------------------------------------------
# Modo Google (Drive + Sheets) - solo se importa google aqui dentro
# ---------------------------------------------------------------------------

def construir_servicios_google(ruta_credenciales):
    """Autentica con la cuenta de servicio. Falla con mensaje claro."""
    ruta = ruta_credenciales or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not ruta or not os.path.exists(ruta):
        print("ERROR: no hay credenciales de cuenta de servicio.\n"
              "Pasa el JSON con --credentials <ruta> o con la variable\n"
              "GOOGLE_APPLICATION_CREDENTIALS. El JSON vive fuera del repo\n"
              "(por ejemplo /opt/impacto-tools/service-account.json).",
              file=sys.stderr)
        return None, None

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        print("ERROR: faltan las librerias de Google. Corre:\n"
              "  pip install -r requirements.txt",
              file=sys.stderr)
        return None, None

    try:
        creds = service_account.Credentials.from_service_account_file(
            ruta, scopes=SCOPES)
        drive = build("drive", "v3", credentials=creds)
        sheets = build("sheets", "v4", credentials=creds)
    except Exception as error:  # noqa: BLE001 - mensaje claro, sin traceback
        print("ERROR: no se pudo autenticar con la cuenta de servicio: %s"
              % error, file=sys.stderr)
        return None, None
    return drive, sheets


def leer_productos_hoja(sheets, sheet_id):
    """Lee la pestana Productos y se queda con estado 'disponible'."""
    try:
        resp = sheets.spreadsheets().values().get(
            spreadsheetId=sheet_id, range="Productos!A1:K2000").execute()
    except Exception as error:  # noqa: BLE001
        print("ERROR: no se pudo leer la Hoja: %s" % error, file=sys.stderr)
        print("Revisa que la cuenta de servicio tenga acceso de lectura a "
              "la Hoja (compartirla con su correo).", file=sys.stderr)
        return None
    filas = resp.get("values", [])
    if not filas:
        print("ERROR: la pestana Productos esta vacia.", file=sys.stderr)
        return None
    cabecera = [normalizar(c) for c in filas[0]]
    productos = []
    for fila in filas[1:]:
        fila = fila + [""] * (len(cabecera) - len(fila))
        p = dict(zip(cabecera, fila))
        if str(p.get("estado") or "").strip().lower() != "disponible":
            continue
        productos.append({
            "id": p.get("id", ""),
            "grupo": str(p.get("grupo") or "").strip().upper(),
            "tipo": p.get("tipo", ""),
            "modelo": p.get("modelo", ""),
            "caracteristicas": p.get("caracteristicas", ""),
            "precio": p.get("precio", ""),
            "moneda": p.get("moneda", ""),
        })
    return productos


def buscar_carpeta_grupo(drive, carpeta_padre_id, nombre_grupo):
    """Busca la subcarpeta <GRUPO> dentro de la carpeta Fotos."""
    resp = drive.files().list(
        q=("'%s' in parents and name = '%s' and "
           "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
           % (carpeta_padre_id, nombre_grupo)),
        fields="files(id, name)").execute()
    archivos = resp.get("files", [])
    return archivos[0]["id"] if archivos else None


def listar_fotos_sin_renombrar(drive, carpeta_id):
    """Archivos de la carpeta que aun tienen nombre IMG-...-WA...."""
    fotos = []
    token_pagina = None
    while True:
        resp = drive.files().list(
            q=("'%s' in parents and trashed = false" % carpeta_id),
            fields="nextPageToken, files(id, name, mimeType)",
            pageSize=200, pageToken=token_pagina).execute()
        for f in resp.get("files", []):
            if (f.get("mimeType", "").startswith("image/")
                    and SIN_RENOMBRAR_RE.match(f.get("name", ""))):
                fotos.append(f)
        token_pagina = resp.get("nextPageToken")
        if not token_pagina:
            break
    return sorted(fotos, key=lambda f: f["name"])


def modo_google(drive, sheets, sheet_id, carpeta_fotos_id, grupo_filtro,
                en_vivo, registro):
    """Procesa las carpetas de Drive grupo por grupo."""
    productos = leer_productos_hoja(sheets, sheet_id)
    if productos is None:
        return 2
    if not productos:
        print("ERROR: no hay productos 'disponible' en la Hoja.",
              file=sys.stderr)
        return 2

    grupos = sorted({p["grupo"] for p in productos if p["grupo"]})
    if grupo_filtro:
        grupo_filtro = grupo_filtro.upper()
        if grupo_filtro not in grupos:
            print("ERROR: el grupo %s no tiene productos 'disponible' en "
                  "la Hoja." % grupo_filtro, file=sys.stderr)
            return 2
        grupos = [grupo_filtro]

    for grupo in grupos:
        carpeta_id = buscar_carpeta_grupo(drive, carpeta_fotos_id, grupo)
        if not carpeta_id:
            print("Aviso: no hay carpeta Fotos/%s en Drive, se salta."
                  % grupo)
            continue
        fotos = listar_fotos_sin_renombrar(drive, carpeta_id)
        print("Grupo %s: %d fotos sin renombrar" % (grupo, len(fotos)))
        del_grupo = [p for p in productos if p["grupo"] == grupo]
        for foto in fotos:
            # Bajar a un temporal, pasar OCR, borrar el temporal.
            with tempfile.NamedTemporaryFile(
                    suffix=os.path.splitext(foto["name"])[1],
                    delete=False) as tmp:
                ruta_tmp = tmp.name
            try:
                from googleapiclient.http import MediaIoBaseDownload
                req = drive.files().get_media(fileId=foto["id"])
                with io.FileIO(ruta_tmp, "wb") as fh:
                    downloader = MediaIoBaseDownload(fh, req)
                    done = False
                    while not done:
                        _estado, done = downloader.next_chunk()
            except Exception as error:  # noqa: BLE001
                registro.linea(foto["name"], "error",
                               "descarga_fallo: %s" % error)
                continue
            try:
                def renombrar_drive(_viejo, nuevo, fid=foto["id"]):
                    # Solo cambia el nombre. Nunca borra, mueve ni sobrescribe.
                    drive.files().update(
                        fileId=fid, body={"name": nuevo}).execute()

                procesar_foto(foto["name"], ruta_tmp, del_grupo, registro,
                              en_vivo, renombrar_drive)
            finally:
                try:
                    os.unlink(ruta_tmp)
                except OSError:
                    pass
    registro.resumen()
    return 0


# ---------------------------------------------------------------------------
# Entrada principal
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Renombra fotos de Impacto por OCR (RapidOCR, local). "
                    "Por defecto es --dry-run: no escribe nada.")
    parser.add_argument("--credentials",
                        help="JSON de la cuenta de servicio (o variable "
                             "GOOGLE_APPLICATION_CREDENTIALS).")
    parser.add_argument("--sheet-id", default=DEFAULT_SHEET_ID,
                        help="Id de la Hoja 'Impacto - Catalogo (datos)'.")
    parser.add_argument("--photos-folder-id",
                        default=DEFAULT_PHOTOS_FOLDER_ID,
                        help="Id de la carpeta Fotos en Drive.")
    parser.add_argument("--group",
                        help="Solo una categoria, p. ej. LAVADORAS.")
    parser.add_argument("--live", action="store_true",
                        help="Renombrar de verdad. Sin este flag es dry-run.")
    parser.add_argument("--dry-run", action="store_true",
                        help="No escribir nada (es el comportamiento por "
                             "defecto).")
    parser.add_argument("--log",
                        help="Ruta del archivo de registro (si no se da, "
                             "solo stdout).")
    parser.add_argument("--local-dir",
                        help="Carpeta local con fotos (modo sin Google).")
    parser.add_argument("--products-file",
                        help="JSON de productos para el modo local.")
    args = parser.parse_args(argv)

    en_vivo = args.live and not args.dry_run
    if args.live and args.dry_run:
        print("Aviso: --live y --dry-run a la vez: manda --dry-run, "
              "no se escribe nada.")
        en_vivo = False

    registro = Registro(args.log)
    print("Renombrar fotos Impacto | modo: %s"
          % ("LIVE (renombra de verdad)" if en_vivo
             else "DRY-RUN (no escribe nada)"))

    if args.local_dir:
        if not args.products_file:
            print("ERROR: --local-dir necesita --products-file <json>.",
                  file=sys.stderr)
            return 2
        if not os.path.isdir(args.local_dir):
            print("ERROR: no existe la carpeta %s" % args.local_dir,
                  file=sys.stderr)
            return 2
        return modo_local(args.local_dir, args.products_file, args.group,
                          en_vivo, registro)

    # Modo Google: sin credenciales no se puede ni empezar.
    drive, sheets = construir_servicios_google(args.credentials)
    if drive is None or sheets is None:
        return 2
    return modo_google(drive, sheets, args.sheet_id, args.photos_folder_id,
                       args.group, en_vivo, registro)


if __name__ == "__main__":
    sys.exit(main())
