#!/usr/bin/env python3
"""Pruebas de renombrar_fotos.py contra la prueba del coordinador (14/11).

No toca Drive ni la Hoja: usa el JSON de productos de la prueba
(productos-test-completo.json, 49 productos de la Hoja real) y los
textos OCR reales volcados de las 99 fotos (ocr-textos-20261114.json,
RapidOCR 1.4.4, determinista: 3 corridas identicas en WA0099/0100/0101).

Verdad conocida: emparejamiento-13-11-reporte.md (manual, 13/11) y los
13 renombres FALSOS + 17 correctos del informe del coordinador.

Se corre asi (sin Google, sin OCR en vivo: rapido):
    python3 test_renombrar.py

Sale con codigo 1 si alguna prueba falla.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import renombrar_fotos as rf

BASE = os.path.dirname(os.path.abspath(__file__))
OCR_TEST = os.path.join(BASE, "..", "..", "ocr-test")


def cargar_productos(grupo=None):
    with open(os.path.join(OCR_TEST, "productos-test-completo.json"),
              encoding="utf-8") as f:
        datos = json.load(f)
    productos = datos["productos"] if isinstance(datos, dict) else datos
    if grupo:
        productos = [p for p in productos
                     if str(p.get("grupo") or "").upper() == grupo]
    return productos


def cargar_ocr():
    with open(os.path.join(OCR_TEST, "ocr-textos-20261114.json"),
              encoding="utf-8") as f:
        return json.load(f)


FALLOS = []


def comprobar(nombre, obtenido, esperado):
    if obtenido != esperado:
        FALLOS.append("%s: obtenido %r, esperado %r"
                      % (nombre, obtenido, esperado))
        print("FALLO %s: obtenido %r, esperado %r"
              % (nombre, obtenido, esperado))
    else:
        print("ok    %s -> %r" % (nombre, obtenido))


def id_o_motivo(producto, motivo):
    return ("id=%s" % producto.get("id")) if producto else motivo


def main():
    ocr = cargar_ocr()
    grupos = {g: cargar_productos(g) for g in
              ("LAVADORAS", "SPLITS", "LUMINARIA", "TRANSPORTE", "TV")}

    # --- 13 renombres FALSOS del coordinador: ninguno puede renombrar.
    # (WA0054 es la excepcion: su verdad es la Mikasuki, oferta 50.)
    falsos = [
        ("IMG-20261113-WA0114.jpg", "LAVADORAS", "sin_coincidencia"),
        ("IMG-20261113-WA0099.jpg", "SPLITS", "ambiguo"),
        ("IMG-20261113-WA0101.jpg", "SPLITS", "sin_coincidencia"),
        ("IMG-20261113-WA0045.jpg", "TRANSPORTE", "sin_coincidencia"),
        ("IMG-20261113-WA0053.jpg", "TRANSPORTE", "sin_coincidencia"),
        ("IMG-20261113-WA0077.jpg", "TRANSPORTE", "sin_coincidencia"),
        ("IMG-20261113-WA0078.jpg", "TRANSPORTE", "sin_coincidencia"),
        ("IMG-20261113-WA0043.jpg", "TRANSPORTE", "sin_coincidencia"),
        ("IMG-20261113-WA0075.jpg", "TRANSPORTE", "sin_coincidencia"),
        ("IMG-20261113-WA0121.jpg", "LUMINARIA", "sin_coincidencia"),
        ("IMG-20261113-WA0129.jpg", "LUMINARIA", "sin_coincidencia"),
        ("IMG-20261113-WA0094.jpg", "TV", "sin_coincidencia"),
    ]
    print("== 13 falsos (ninguno puede renombrar) ==")
    for archivo, grupo, esperado in falsos:
        producto, motivo = rf.match_product(ocr[archivo], grupos[grupo])
        comprobar("FALSO %s" % archivo, id_o_motivo(producto, motivo),
                  esperado if esperado.startswith("id=") else esperado)
    producto, motivo = rf.match_product(
        ocr["IMG-20261113-WA0054.jpg"], grupos["TRANSPORTE"])
    comprobar("FALSO->CORRECTO WA0054 (Mikasuki, oferta 50)",
              id_o_motivo(producto, motivo), "id=133")

    # Sin verificar por el coordinador: WA0066 (bici infantil #12 EKO).
    # El OCR trae Aro 12" y es el unico #12 del grupo: renombra a 125.
    producto, motivo = rf.match_product(
        ocr["IMG-20261113-WA0066.jpg"], grupos["TRANSPORTE"])
    comprobar("SIN-VERIFICAR WA0066 (Aro 12)",
              id_o_motivo(producto, motivo), "id=125")

    # --- 17 correctos del coordinador: 14 deben seguir, 3 se pierden
    # a pendiente manual seguro (documentado en el informe de entrega).
    print("== 17 correctos (14 siguen, 3 a manual seguro) ==")
    correctos = [
        ("IMG-20261113-WA0107.jpg", "LAVADORAS", "id=145"),
        ("IMG-20261113-WA0110.jpg", "LAVADORAS", "id=147"),
        ("IMG-20261113-WA0112.jpg", "LAVADORAS", "id=149"),
        ("IMG-20261113-WA0100.jpg", "SPLITS", "ambiguo"),  # PERDIDA segura
        ("IMG-20261113-WA0104.jpg", "SPLITS", "id=140"),
        ("IMG-20261113-WA0106.jpg", "SPLITS", "id=144"),
        ("IMG-20261113-WA0127.jpg", "LUMINARIA",
         "sin_coincidencia"),  # PERDIDA segura
        ("IMG-20261113-WA0044.jpg", "TRANSPORTE", "id=136"),
        ("IMG-20261113-WA0063.jpg", "TRANSPORTE",
         "ambiguo"),  # PERDIDA segura
        ("IMG-20261113-WA0071.jpg", "TRANSPORTE", "id=130"),
        ("IMG-20261111-WA0213.jpg", "TV", "id=15"),
        ("IMG-20261111-WA0215.jpg", "TV", "id=18"),
        ("IMG-20261111-WA0217.jpg", "TV", "id=20"),
        ("IMG-20261111-WA0219.jpg", "TV", "id=23"),
        ("IMG-20261111-WA0220.jpg", "TV", "id=23"),
        ("IMG-20261113-WA0095.jpg", "TV", "id=22"),
        ("IMG-20261113-WA0096.jpg", "TV", "id=22"),
    ]
    for archivo, grupo, esperado in correctos:
        producto, motivo = rf.match_product(ocr[archivo], grupos[grupo])
        comprobar("CORRECTO %s" % archivo,
                  id_o_motivo(producto, motivo), esperado)

    # --- Renombres nuevos correctos segun el informe manual 13/11
    # (la version vieja los dejaba en ambiguo/sin_coincidencia).
    print("== Nuevos correctos (informe manual 13/11) ==")
    nuevos = [
        ("IMG-20261113-WA0111.jpg", "LAVADORAS", "id=148"),
        ("IMG-20261113-WA0115.jpg", "LAVADORAS", "id=153"),
        ("IMG-20261113-WA0116.jpg", "LAVADORAS", "id=152"),
        ("IMG-20261113-WA0102.jpg", "SPLITS", "id=141"),
        ("IMG-20261113-WA0105.jpg", "SPLITS", "id=143"),
        ("IMG-20261111-WA0211.jpg", "TV", "id=24"),
        ("IMG-20261113-WA0051.jpg", "TRANSPORTE", "id=134"),
    ]
    for archivo, grupo, esperado in nuevos:
        producto, motivo = rf.match_product(ocr[archivo], grupos[grupo])
        comprobar("NUEVO %s" % archivo,
                  id_o_motivo(producto, motivo), esperado)

    # --- Otros casos seguros (ni falsos ni correctos antes).
    print("== Otros casos seguros ==")
    otros = [
        ("IMG-20261113-WA0091.jpg", "TRANSPORTE", "ambiguo"),
        ("IMG-20261113-WA0103.jpg", "SPLITS", "ambiguo"),
        ("IMG-20261111-WA0214.jpg", "TV", "ambiguo"),
        ("IMG-20261111-WA0218.jpg", "TV", "ambiguo"),
        ("IMG-20261111-WA0216.jpg", "TV", "sin_coincidencia"),
        ("IMG-20261113-WA0097.jpg", "SPLITS", "sin_coincidencia"),
        ("IMG-20261113-WA0098.jpg", "SPLITS", "sin_coincidencia"),
        ("IMG-20261113-WA0108.jpg", "LAVADORAS", "sin_texto"),
        ("IMG-20261113-WA0113.jpg", "LAVADORAS", "sin_coincidencia"),
        ("IMG-20261113-WA0109.jpg", "LAVADORAS", "sin_coincidencia"),
        ("IMG-20261113-WA0072.jpg", "TRANSPORTE", "sin_coincidencia"),
        ("IMG-20261113-WA0050.jpg", "TRANSPORTE", "sin_coincidencia"),
        ("IMG-20261113-WA0088.jpg", "TRANSPORTE", "sin_coincidencia"),
        ("IMG-20261113-WA0122.jpg", "LUMINARIA", "sin_coincidencia"),
        ("IMG-20261113-WA0130.jpg", "LUMINARIA", "sin_coincidencia"),
        ("IMG-20261113-WA0124.jpg", "LUMINARIA", "sin_coincidencia"),
        ("IMG-20261113-WA0125.jpg", "LUMINARIA", "sin_coincidencia"),
        ("IMG-20261113-WA0070.jpg", "TRANSPORTE", "sin_coincidencia"),
        ("IMG-20261113-WA0067.jpg", "TRANSPORTE", "sin_coincidencia"),
    ]
    for archivo, grupo, esperado in otros:
        producto, motivo = rf.match_product(ocr[archivo], grupos[grupo])
        comprobar("OTRO %s" % archivo,
                  id_o_motivo(producto, motivo), esperado)

    # --- Vetos sinteticos (sin depender del OCR de una foto).
    print("== Vetos sinteticos ==")
    sinteticos = [
        ("MILEXUS SPLIT 2 TONELADAS 24K 220V", "SPLITS",
         "sin_coincidencia"),  # 2 ton: ni el 140 ni el 141 sin datos
        ("JMD JD-ST-43 SMARTTV 43", "TV",
         "sin_coincidencia"),  # marca curada, no es la TV generica 43
        ("EKO LAVADORA SECADORA A VAPOR 11KG", "LAVADORAS",
         "sin_coincidencia"),  # combo: ni secadora ni lavadora
        ("PANTHER TRICICLO DE CARGA ZJ150UK 1500W", "TRANSPORTE",
         "sin_coincidencia"),  # marca curada + tipo distinto de bici
        ("MIKAZUKI", "TRANSPORTE", "id=133"),  # 1 letra OCR
        ("VEDCA N3 MOTORINA", "TRANSPORTE", "id=136"),  # codigo N3
        ("TV 55 PULGADAS", "TV", "id=18"),  # medida sola, unica
        ("LINTERNA LED RECARGABLE", "LUMINARIA",
         "sin_coincidencia"),  # solo genericas: nunca renombra
        ("TV 50 PULGADAS", "TV", "ambiguo"),  # 50" lo tienen 21 y 22
        ("BICICLETA 20", "TRANSPORTE",
         "sin_coincidencia"),  # "20" solo no es medida
        ("MILEXUS SPLIT 1 TONELADA 110V", "SPLITS",
         "id=141"),  # 110V veta al 220V, queda el sin datos
        ("SACO ML-SPAC-12K-220V", "SPLITS",
         "id=143"),  # marca SACO, no Milexus aunque el codigo lo sea
    ]
    for texto, grupo, esperado in sinteticos:
        producto, motivo = rf.match_product(texto, grupos[grupo])
        comprobar("SINTETICO %r" % texto[:40],
                  id_o_motivo(producto, motivo), esperado)

    # --- Tokenizacion (palabras pegadas del OCR, medidas, numeros).
    print("== Tokenizacion ==")
    comprobar("tokens 7.5kgMilexus",
              rf.tokens("7.5kgMilexus", {"milexus"}),
              ["7.5kg", "milexus"])
    comprobar("tokens Lavadorade8kg", rf.tokens("Lavadorade8kg"),
              ["lavadora", "de", "8kg"])
    comprobar("tokens MOTORINAN3", rf.tokens("MOTORINAN3"),
              ["motorina", "n3"])
    comprobar("tokens 12,000BTU/h", rf.tokens("12,000BTU/h"),
              ["12000btu", "h"])
    comprobar("tokens 9.0kg", rf.tokens("9.0kg"), ["9kg"])
    comprobar("tokens #12", rf.tokens("#12"), ["aro12"])
    comprobar("tokens 43\"", rf.tokens('43"'), ["43pulg"])
    comprobar("tokens rudenkov intacto",
              rf.tokens("RUDENKOV LAVADORA"), ["rudenkov", "lavadora"])
    comprobar("tokens n3ah intacto", rf.tokens("48V/n3Ah"),
              ["48v", "n3ah"])
    comprobar("levenshtein mikazuki/mikasuki",
              rf._levenshtein_1("mikazuki", "mikasuki"), True)
    comprobar("levenshtein mlexus/milexus",
              rf._levenshtein_1("mlexus", "milexus"), True)
    comprobar("levenshtein conka/konka (corta, no vale)",
              rf._levenshtein_1("conka", "konka"), True)  # dist 1, pero
    # el umbral de 6 letras esta en marcas_en_texto, no aqui:
    comprobar("fuzzy conka no casa konka (len<6)",
              rf.marcas_en_texto({"conka"}, {"konka"}), set())

    # --- Nombres nuevos (regla 6).
    print("== Nombres nuevos ==")
    por_id = {}
    for g in grupos.values():
        for p in g:
            por_id[str(p.get("id"))] = p
    comprobar("nombre 140 (sin ficha de 600 caracteres)",
              rf.construir_nombre(por_id["140"],
                                  "IMG-20261113-WA0100.jpg"),
              "Split-220v-1ton-Milexus-WA0100.jpg")
    comprobar("nombre 150 (sin Eko Eko)",
              rf.construir_nombre(por_id["150"],
                                  "IMG-20261113-WA0114.jpg"),
              "Secadora-Vapor-Eko-WA0114.jpg")
    comprobar("nombre 15 (sin Tv Premier repetido)",
              rf.construir_nombre(por_id["15"],
                                  "IMG-20261111-WA0213.jpg"),
              "Tv-Premier-32pulg-Barra-Sonido-WA0213.jpg")
    comprobar("nombre 24 (Mara -> fuera)",
              rf.construir_nombre(por_id["24"],
                                  "IMG-20261111-WA0211.jpg"),
              "Tv-32pulg-Konka-WA0211.jpg")
    comprobar("nombre 126 (sin caracteristicas)",
              rf.construir_nombre(por_id["126"],
                                  "IMG-20261113-WA0043.jpg"),
              "Bicicletas-Aro26-WA0043.jpg")
    comprobar("nombre 136",
              rf.construir_nombre(por_id["136"],
                                  "IMG-20261113-WA0044.jpg"),
              "Motos-Electricas-Vedca-N3-0km-WA0044.jpg")
    comprobar("nombre 145 (ejemplo del docstring)",
              rf.construir_nombre(por_id["145"],
                                  "IMG-20261113-WA0107.jpg"),
              "Lavadora-Automatica-Wynwood-9kg-WA0107.jpg")
    for pid in ("140", "150", "15", "24", "126", "136", "145"):
        nombre = rf.construir_nombre(por_id[pid], "IMG-20261113-WA0001.jpg")
        comprobar("nombre %s <= 120 caracteres" % pid, len(nombre) <= 120,
                  True)

    print()
    if FALLOS:
        print("FALLOS: %d" % len(FALLOS))
        for f in FALLOS:
            print("  - %s" % f)
        return 1
    print("TODAS LAS PRUEBAS PASAN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
