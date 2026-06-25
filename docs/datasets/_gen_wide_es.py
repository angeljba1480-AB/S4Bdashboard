# -*- coding: utf-8 -*-
import csv, os
from _gen_es100 import DATA as BASE, PAISES, ALL
OUT = os.path.dirname(os.path.abspath(__file__))

# Nuevas palabras (mismo formato): (palabra, emoji, cat, general, [(sig,[codes])])
EXTRA = [
 ("tinto","☕🍷","Comida","vino tinto",
   [("café negro", ["CO"])]),
 ("perico","☕🦜","Doble sentido","loro / perico (ave)",
   [("café con leche", ["CO"]),
    ("cocaína (jerga) ⚠️", ["ES","CO"])]),
 ("guaro","🥃","Comida","aguardiente / licor",
   [("aguardiente", ["CR","CO","NI","HN","SV"])]),
 ("completo","🌭","Comida","completo / lleno (adj.)",
   [("hot dog con todo", ["CL"])]),
 ("pastel","🎂","Comida","pastel / torta",
   [("'torta'", ["AR","UY","ES"]),
    ("'queque'", ["CR","GT","PE"]),
    ("'ponqué'", ["CO","VE"]),
    ("'bizcocho'", ["DO","PR"]),
    ("'cake / keik'", ["VE","PR"]),
    ("'pastel'", ["MX","CL","EC","BO"])]),
 ("sorbete","🍦","Doble sentido","sorbete / pajita (popote)",
   [("helado / nieve", ["DO"]),
    ("popote / pajita", ["AR","UY","PE"])]),
 ("helado","🍨","Comida","helado",
   [("'mantecado'", ["PR"]),
    ("'nieve' (de agua)", ["MX"]),
    ("'helado'", ["ES","AR","CO","CL","PE","VE","EC","UY"])]),
 ("arepa","🫓","Doble sentido","pan de maíz (plato típico)",
   [("arepa (comida)", ["VE","CO"]),
    ("⚠️ doble sentido sexual", ["VE"])]),
 ("arrecho","😡🔥","Estado ⚠️","enojado / bravo",
   [("enojado / bravo", ["VE","CO","EC"]),
    ("excitado sexualmente ⚠️", ["MX","PE"]),
    ("genial / valiente ('qué arrecho')", ["CO"])]),
 ("templado","😍","Estado","entibiado / templado",
   [("enamorado", ["EC"]),
    ("valiente / firme", ["ES","MX"])]),
 ("gamba","🦐💵","Doble sentido","camarón (marisco)",
   [("cien (de dinero)", ["AR"]),
    ("'meter la gamba' = meter la pata / pierna", ["ES"])]),
 ("palo","🪵","Doble sentido","palo / vara",
   [("un millón (de dinero)", ["AR","ES"]),
    ("trago de licor", ["DO","PR","VE"]),
    ("'qué palo' = problema/golpe", ["ES"])]),
 ("feria","🎡💰","Doble sentido","feria / mercado / kermés",
   [("dinero / cambio en monedas", ["MX"])]),
 ("billete","💵","Dinero","billete (papel moneda)",
   [("dinero / 'tener billete' = ser rico", ["MX","CO","VE"])]),
 ("molestar","😩","Verbo","fastidiar / incomodar",
   [("'fregar / dar lata'", ["MX","CO"]),
    ("'joder / dar la lata'", ["ES"]),
    ("'embromar / hinchar / romper'", ["AR","UY"]),
    ("'fastidiar'", ["VE","PE"]),
    ("'mamar gallo' = bromear/molestar", ["CO","VE"])]),
 ("entender","💡","Verbo","comprender",
   [("'cachar'", ["CL","PE"]),
    ("'manyar' (lunfardo)", ["AR"]),
    ("'pillar / coger la onda'", ["ES"]),
    ("'agarrar la onda / caer el veinte'", ["MX"]),
    ("'captar / coger'", ["CO","VE"])]),
 ("tipo","🧑","Persona","individuo / sujeto",
   [("'chabón / loco / pibe'", ["AR"]),
    ("'man / parce'", ["CO"]),
    ("'tío / tipo'", ["ES"]),
    ("'cuate / wey'", ["MX"]),
    ("'pana / chamo'", ["VE"]),
    ("'gallo / weón'", ["CL"]),
    ("'pata / causa'", ["PE"])]),
 ("novio","💑","Persona","novio / pareja",
   [("'pololo'", ["CL"]),
    ("'enamorado'", ["PE","EC","BO"]),
    ("'jevo / cuadre'", ["VE","DO"]),
    ("'pelado'", ["EC"]),
    ("'novio'", ["MX","ES","AR","CO","UY","GT","SV","HN","NI","CR","PA","CU","PR"])]),
 ("tonto","🤪","Insulto","poco listo",
   [("'menso / baboso / tarugo'", ["MX"]),
    ("'boludo / pelotudo / gil / sonso'", ["AR"]),
    ("'huevón / weón'", ["CL"]),
    ("'cojudo / huevas'", ["PE"]),
    ("'güevón / bobo'", ["CO"]),
    ("'pendejo'", ["VE","MX"]),
    ("'gil / tonto / lerdo'", ["ES"]),
    ("'baboso / maje'", ["SV","HN","NI"])]),
 ("borracho","🥴","Estado","ebrio",
   [("'pedo / jalado / hasta atrás'", ["MX"]),
    ("'curado / curao'", ["CL"]),
    ("'rascado / prendido'", ["VE"]),
    ("'en pedo / mamado'", ["AR"]),
    ("'jumado / chumado'", ["EC"]),
    ("'bolo'", ["GT","SV"]),
    ("'jincho'", ["PR"]),
    ("'borracho / tomado'", ["ES","CO","PE","UY"])]),
 ("enojado","😠","Estado","molesto / con rabia",
   [("'emputado / encabronado'", ["MX"]),
    ("'arrecho / emputado'", ["VE","CO"]),
    ("'encachimbado'", ["NI","SV"]),
    ("'caliente / picado'", ["PE"]),
    ("'con bronca / caliente'", ["AR"]),
    ("'cabreado / mosqueado'", ["ES"]),
    ("'achacado'", ["CL"])]),
 ("guapo","😍","Persona","atractivo / bien parecido",
   [("'churro / papacito / buenote'", ["MX"]),
    ("'churro / pintón'", ["AR"]),
    ("'papito / mango'", ["VE","DO"]),
    ("'buenmozo / pinta'", ["CO","PE"]),
    ("'guapo / bueno'", ["ES"]),
    ("'rico / regio'", ["CL"]),
    ("'guapo' = valiente/bravucón", ["CU","PR"])]),
 ("bolígrafo","🖊️","Objeto","instrumento para escribir",
   [("'pluma'", ["MX"]),
    ("'birome / lapicera'", ["AR","UY"]),
    ("'esfero / esferográfico'", ["CO","EC"]),
    ("'lapicero'", ["PE","GT","SV","HN"]),
    ("'boli / bolígrafo'", ["ES"]),
    ("'lápiz de pasta'", ["CL"]),
    ("'pluma / bolígrafo'", ["VE","CR","PA","DO","PR","CU","BO","NI","PY"])]),
 ("golosinas","🍬","Comida","dulces / caramelos",
   [("'chuches'", ["ES"]),
    ("'gomitas / dulces'", ["MX"]),
    ("'chucherías'", ["VE","ES"]),
    ("'caramelos / golosinas'", ["AR","CO","PE","CL","UY","EC"]),
    ("'confites'", ["CR","GT"]),
    ("'frunas / dulces'", ["PE"])]),
 ("globo","🎈","Objeto","globo (de aire)",
   [("'bomba'", ["CO","VE","SV","GT"]),
    ("'vejiga'", ["NI","HN"]),
    ("'globo'", ["MX","ES","AR","CL","PE","EC","UY","CR","PA","DO","PR","CU","BO","PY"])]),
 ("cometa","🪁","Objeto","cometa / juguete de viento",
   [("'papalote'", ["MX","CU"]),
    ("'barrilete'", ["AR","UY"]),
    ("'volantín'", ["CL"]),
    ("'chiringa'", ["PR"]),
    ("'pandorga'", ["PY"]),
    ("'piscucha'", ["SV"]),
    ("'papagayo'", ["VE","CO"]),
    ("'cometa'", ["ES","PE","EC"])]),
 ("acera","🚶","Objeto / lugar","borde peatonal de la calle",
   [("'banqueta'", ["MX"]),
    ("'vereda'", ["AR","CL","PE","UY","BO"]),
    ("'andén'", ["CO"]),
    ("'acera'", ["ES","VE","EC","CR","PA","DO","PR","CU","GT","SV","HN","NI","PY"])]),
 ("atasco","🚗💢","Objeto / lugar","congestión de tráfico",
   [("'trancón'", ["CO"]),
    ("'taco'", ["CL"]),
    ("'presa'", ["CR"]),
    ("'tapón'", ["PR","DO"]),
    ("'tranque'", ["PA"]),
    ("'embotellamiento'", ["MX","AR","VE","PE","EC"]),
    ("'atasco / atochamiento'", ["ES"])]),
 ("cuadra","🏘️","Objeto / lugar","tramo de calle entre esquinas",
   [("'manzana'", ["ES"]),
    ("'cuadra'", ["MX","AR","CO","CL","PE","VE","EC","UY"])]),
 ("chévere","😎","Cualidad","genial / bien",
   [("genial / bueno", ["VE","CO","PE","EC","CU","DO","PA"])]),
 ("bacán","😎","Cualidad","genial / de calidad",
   [("genial / de buena calidad", ["CL","PE","CO","EC"]),
    ("buena persona / generoso", ["CU"])]),
 ("chamba","💼","Dinero","trabajo / empleo",
   [("trabajo", ["MX","PE","EC","GT","SV","HN","NI"])]),
 ("chivo","🐐","Doble sentido","cabra macho",
   [("genial / cool", ["SV"]),
    ("soborno / 'hacer chivo'", ["HN"]),
    ("inquieto / nervioso", ["DO"]),
    ("apestoso (olor a sudor)", ["CR"])]),
 ("pelado","🧑","Doble sentido","sin pelo / calvo",
   [("niño / joven", ["CO","EC"]),
    ("sin dinero ('estar pelado')", ["MX","AR","VE"]),
    ("grosero / maleducado ('pelado')", ["CO"])]),
 ("man","🧑","Persona","tipo / individuo (del inglés)",
   [("tipo / persona (incluso mujer: 'esa man')", ["CO","EC"]),
    ("'man / amigo'", ["VE","PA"])]),
 ("chao","👋","Expresión","adiós / hasta luego",
   [("'chao / chau'", ["AR","CL","UY","CO","VE","PE","EC","ES"]),
    ("'bye / nos vemos'", ["MX"])]),
 ("rico","😋","Cualidad","sabroso / delicioso",
   [("delicioso", ALL),
    ("atractivo ('está rico/a') ⚠️", ["MX","CO","VE","CL"])]),
 ("chucho","🐕","Doble sentido","perro callejero",
   [("frío ('hace chucho')", ["MX(sur)","GT","HN"]),
    ("astuto / listo", ["GT"]),
    ("cárcel", ["GT"]),
    ("escalofrío / susto", ["CR"])]),
 ("bomba","💣","Doble sentido","bomba explosiva",
   [("globo", ["CO","VE"]),
    ("gasolinera", ["CL","CR","EC"]),
    ("borrachera ('agarrar una bomba')", ["AR"]),
    ("copla / verso (folclor)", ["EC"])]),
 ("micro","🚐","Objeto","autobús pequeño",
   [("microbús", ["CL","AR"]),
    ("microondas / lo pequeño", ["ES"])]),
 ("once","🕚🍞","Doble sentido","el número 11",
   [("merienda de la tarde ('tomar once')", ["CL"])]),
 ("tuani / tuanis","👌","Cualidad","genial / bien",
   [("genial / bien", ["CR","NI"])]),
 ("fresco","😎","Doble sentido","frío / fresco (temperatura)",
   [("tranquilo ('fresco, todo bien')", ["CO","CR"]),
    ("descarado / atrevido", ["ES","MX"]),
    ("refresco / jugo natural", ["CO","CR"])]),
 ("pelar","🍌","Verbo","quitar la cáscara",
   [("ignorar ('no me pela')", ["MX"]),
    ("criticar / chismear", ["CR","CO"]),
    ("'pelar billete' = mostrar dinero", ["VE"])]),
 ("nota","🎵","Doble sentido","nota musical / calificación",
   [("'qué nota' = qué bueno/genial", ["CO","VE"]),
    ("efecto de droga/alcohol ('en nota')", ["MX","CO"])]),
 ("vaina","🤷","Comodín","cosa / asunto",
   [("cosa / asunto (comodín)", ["VE","CO","DO","PA","EC","CR"]),
    ("'qué vaina' = qué problema/lástima", ["VE","DO"])]),
 ("man / mano","✋","Persona","mano / amigo",
   [("'mano / manito' = amigo", ["MX","DO"]),
    ("'mae / mano'", ["CR"])]),
 ("chimbo","👎","Doble sentido","falso / de mala calidad",
   [("falso / malo", ["VE"]),
    ("⚠️ relativo a 'chimba'", ["CO"])]),
 ("pinta","🎨","Doble sentido","aspecto / facha",
   [("buena apariencia ('tener pinta')", ["AR","CO","ES"]),
    ("graffiti / pintada", ["MX"]),
    ("novillos: 'irse de pinta' = faltar a clase", ["MX"]),
    ("cerveza (medida) / trago", ["ES"])]),
 ("chela","🍺","Doble sentido","cerveza",
   [("cerveza", ["MX","GT","BO","PE"]),
    ("persona rubia/de piel clara ('chele/chela')", ["NI","HN"])]),
 ("mecato","🍿","Comida","picadera / botana entre comidas",
   [("snack / pasaboca", ["CO"])]),
 ("botana","🍢","Comida","aperitivo / snack",
   [("'botana'", ["MX"]),
    ("'pasapalos'", ["VE"]),
    ("'picada / picoteo'", ["AR","CL"]),
    ("'pasabocas / mecato'", ["CO"]),
    ("'piqueo'", ["PE"]),
    ("'tapas / picoteo'", ["ES"]),
    ("'bocadillo / picadera'", ["DO","PR"])]),
 ("chamo / chamito","🧒","Persona","niño / joven",
   [("niño / joven", ["VE"])]),
]

import json as _json
_WF=[]
_wf_path=os.path.join(OUT,"workflow_words.json")
if os.path.exists(_wf_path):
    for _w in _json.load(open(_wf_path,encoding="utf-8"))["words"]:
        _vs=[(v["sig"],[c.strip() for c in v["paises"].split(",") if c.strip()]) for v in _w.get("variantes",[])]
        _WF.append((_w["palabra"],_w.get("emoji",""),_w.get("categoria","Varios"),_w.get("general",""),_vs))
DATA = BASE + EXTRA + _WF
# Dedupe por palabra (conserva la última aparición = versión más completa)
_seen = {}
for _w in DATA:
    _seen[_w[0]] = _w
DATA = list(_seen.values())

# ---- Construir tabla ANCHA: una columna por país ----
def meanings(word):
    palabra, emoji, cat, general, variantes = word
    asign = {}
    for sig, codes in variantes:
        for c in codes:
            if c in PAISES: asign[c] = sig
    return {c: asign.get(c, general) for c in ALL}

# CSV ancho
header = ["palabra","emoji","categoria"] + [PAISES[c][1] for c in ALL]
rows = []
for w in DATA:
    palabra, emoji, cat, general, variantes = w
    m = meanings(w)
    rows.append([palabra, emoji, cat] + [m[c] for c in ALL])

with open(os.path.join(OUT,"es-todos-paises-ANCHO.csv"),"w",encoding="utf-8",newline="") as f:
    wr = csv.writer(f); wr.writerow(header); wr.writerows(rows)

# MD ancho (tabla con una columna por país, con bandera en el encabezado)
md = ["# 🌎 Español — tabla ANCHA: una columna por país\n",
      f"> {len(DATA)} palabras × {len(ALL)} países (20 hispanohablantes + 🇬🇶). "
      "Cada celda = significado en ESE país. Datos en "
      "[`es-todos-paises-ANCHO.csv`](./es-todos-paises-ANCHO.csv).\n",
      "> ⚠️ = sentido vulgar/sexual en algún país. La tabla es muy ancha: "
      "ábrela en el CSV/dashboard para mejor lectura.\n"]
head_cells = ["Palabra","Emoji"] + [PAISES[c][0] for c in ALL]
md.append("\n| " + " | ".join(head_cells) + " |")
md.append("|" + "|".join(["---"]*len(head_cells)) + "|")
for w in DATA:
    palabra, emoji, cat, general, variantes = w
    m = meanings(w)
    cells = [f"**{palabra}**", emoji] + [m[c].replace("|","/") for c in ALL]
    md.append("| " + " | ".join(cells) + " |")
md.append("\n\n## Países (columnas)\n")
md.append(" · ".join(f"{PAISES[c][0]} {PAISES[c][1]}" for c in ALL))
with open(os.path.join(OUT,"es-todos-paises-ANCHO.md"),"w",encoding="utf-8") as f:
    f.write("\n".join(md)+"\n")

print("Total palabras ES:", len(DATA), "| columnas país:", len(ALL))
