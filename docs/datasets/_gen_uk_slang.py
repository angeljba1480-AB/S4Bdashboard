# -*- coding: utf-8 -*-
import csv, os
OUT = os.path.dirname(os.path.abspath(__file__))

REGIONS = {
 "LDN":("🎩","London / Cockney & MLE"),
 "SCO":("🏴󠁧󠁢󠁳󠁣󠁴󠁿","Scotland"),
 "WAL":("🏴󠁧󠁢󠁷󠁬󠁳󠁿","Wales"),
 "NI":("☘️","Northern Ireland"),
 "LIV":("⚓","Liverpool (Scouse)"),
 "NCL":("🌉","Newcastle (Geordie)"),
 "MAN":("🐝","Manchester (Mancunian)"),
 "BIR":("🔧","Birmingham (Brummie)"),
 "YOR":("🐑","Yorkshire"),
 "WC":("🤳","Gen-Z UK (nationwide)"),
}

# (word, emoji, category, meaning, [(region, note)])
DATA = [
 ("Mate","🤝","Person","friend / pal", [("LDN",None),("YOR",None),("WC","also general UK")]),
 ("Innit","💬","Tag","'isn't it' (agreement tag)", [("LDN","MLE/Cockney"),("WC",None)]),
 ("Bruv","🤝","Person","brother / friend", [("LDN",None),("WC",None)]),
 ("Bredren / Fam","👨‍👩‍👦","Person","close friend (MLE)", [("LDN",None),("WC",None)]),
 ("Peng","🔥","Adjective","very attractive / great (MLE)", [("LDN",None),("WC",None)]),
 ("Bait","👀","Adjective","obvious / well-known (MLE)", [("LDN",None),("WC",None)]),
 ("Peak","😩","Adjective","unfortunate / harsh (MLE)", [("LDN",None),("WC",None)]),
 ("Long","🥱","Adjective","tedious / too much effort", [("LDN",None),("WC",None)]),
 ("Wagwan","👋","Greeting","'what's going on?' (MLE)", [("LDN",None)]),
 ("Safe","👌","Interjection","'cool / thanks / ok'", [("LDN",None),("WC",None)]),
 ("Bloke","🧑","Person","man / guy", [("LDN",None),("YOR",None),("MAN",None)]),
 ("Knackered","😴","Adjective","exhausted", [("LDN",None),("YOR",None),("MAN",None)]),
 ("Gutted","😞","Adjective","very disappointed", [("LDN",None),("LIV",None),("YOR",None)]),
 ("Chuffed","😄","Adjective","very pleased", [("YOR",None),("MAN",None),("LDN",None)]),
 ("Cheeky","😏","Adjective","playfully rude / a little ('cheeky pint')", [("LDN",None),("WC",None)]),
 ("Minging","🤮","Adjective","disgusting / ugly", [("SCO",None),("NCL",None),("LIV",None)]),
 ("Wee","🤏","Adjective","small / little", [("SCO",None),("NI",None)]),
 ("Aye","👍","Interjection","yes", [("SCO",None),("NCL",None),("YOR",None)]),
 ("Bonnie","😍","Adjective","pretty / beautiful", [("SCO",None)]),
 ("Ken","🧠","Verb","know ('d'ye ken?')", [("SCO",None)]),
 ("Bairn","👶","Noun","child / baby", [("SCO",None),("NCL",None)]),
 ("Dinnae","🚫","Verb","'don't'", [("SCO",None)]),
 ("Bampot","🤪","Noun","idiot / fool", [("SCO",None)]),
 ("Canny","😌","Adjective","nice/good (Geordie) / careful (Scots)", [("NCL","= nice/very"),("SCO","= careful")]),
 ("Howay","🗣️","Interjection","'come on!'", [("NCL",None)]),
 ("Pet","💚","Term of address","'love / dear' (affectionate)", [("NCL",None)]),
 ("Toon","🏟️","Noun","the town / Newcastle Utd", [("NCL",None)]),
 ("Geordie","🌉","Noun","person from Newcastle", [("NCL",None)]),
 ("Scran","🍽️","Noun","food", [("NCL",None),("LIV",None),("SCO",None)]),
 ("La / Lad","🧑","Person","mate (Scouse)", [("LIV",None)]),
 ("Boss","👌","Adjective","great / excellent", [("LIV",None)]),
 ("Made up","😁","Phrase","very happy / delighted", [("LIV",None),("MAN",None)]),
 ("Sound","👍","Adjective","good / reliable / 'no problem'", [("LIV",None),("MAN",None)]),
 ("Devo'd","😢","Adjective","devastated", [("LIV",None),("WC",None)]),
 ("Our kid","👦","Phrase","sibling / close family", [("MAN",None),("LIV",None)]),
 ("Mint","✨","Adjective","excellent / great", [("MAN",None),("NCL",None),("YOR",None)]),
 ("Buzzin'","🤩","Adjective","very excited / happy", [("MAN",None),("LIV",None)]),
 ("Bostin'","👍","Adjective","excellent / great", [("BIR",None)]),
 ("Bab","💛","Term of address","'love / dear'", [("BIR",None)]),
 ("Yampy","🤪","Adjective","crazy / daft", [("BIR",None)]),
 ("Ta-ra / Tara","👋","Interjection","goodbye", [("BIR",None),("LIV",None),("YOR",None)]),
 ("Owt / Nowt","🔁","Noun","'anything' / 'nothing'", [("YOR",None),("NCL",None)]),
 ("Ey up","👋","Greeting","'hello / watch out'", [("YOR",None),("MAN",None)]),
 ("Summat","❓","Noun","'something'", [("YOR",None)]),
 ("Nesh","🥶","Adjective","feeling the cold easily", [("YOR",None),("BIR",None)]),
 ("Craic","🎉","Noun","fun / good time / gossip", [("NI",None),("SCO",None)]),
 ("Wee buns","🧁","Phrase","very easy", [("NI",None)]),
 ("Boyo","🧑","Person","boy / mate", [("WAL",None)]),
 ("Cwtch","🤗","Noun","a cuddle / cosy hug", [("WAL",None)]),
 ("Tidy","👌","Adjective","good / great / fine", [("WAL",None)]),
 ("Lush","😍","Adjective","lovely / delicious", [("WAL",None),("WC",None)]),
 ("Now in a minute","⏳","Phrase","soon / shortly (paradoxical)", [("WAL",None)]),
 ("Butty","🥪","Noun","sandwich", [("LIV",None),("MAN",None),("WAL",None)]),
 ("Skint","💸","Adjective","broke / no money", [("LDN",None),("YOR",None),("WC",None)]),
 ("Quid","💷","Noun","pound (£)", [("LDN",None),("WC",None)]),
 ("Tenner / Fiver","💷","Noun","£10 / £5 note", [("LDN",None),("WC",None)]),
 ("Dodgy","👀","Adjective","suspicious / unreliable", [("LDN",None),("WC",None)]),
 ("Gaff","🏠","Noun","house / home", [("LDN",None),("MAN",None)]),
 ("Naff","👎","Adjective","tacky / uncool", [("LDN",None),("YOR",None)]),
 ("Rinsed","💀","Verb","mocked / used up", [("WC",None),("LDN",None)]),
]

rows=[]; md=[]
md.append("# 🇬🇧 UK English slang — modismos por región\n")
md.append("> Slang del Reino Unido por **región/nación** (Londres/MLE, Escocia, Gales, "
          "Irlanda del Norte, Liverpool, Newcastle, Manchester, Birmingham, Yorkshire) "
          "+ jerga Gen-Z UK, con su **emoji**. Datos en "
          "[`uk-slang-regional.csv`](./uk-slang-regional.csv).\n")
md.append("\n| # | Word/Phrase | Meaning | Region(s) | Emoji |\n|---|---|---|---|---|")
for i,(word,emoji,cat,meaning,regs) in enumerate(DATA,1):
    reg_str=" · ".join(f"{REGIONS[rc][0]} {REGIONS[rc][1]}"+(f" ({n})" if n else "")
                       for rc,n in regs if rc in REGIONS)
    md.append(f"| {i} | **{word}** | {meaning} | {reg_str} | {emoji} |")
    for rc,n in regs:
        if rc in REGIONS:
            flag,name=REGIONS[rc]
            rows.append([word,rc,name,flag,meaning,n or "",emoji,cat])
with open(os.path.join(OUT,"uk-slang-regional.md"),"w",encoding="utf-8") as f:
    f.write("\n".join(md)+"\n\n---\n\n## Leyenda de regiones\n\n"+
            "\n".join(f"- {fl} **{nm}** (`{c}`)" for c,(fl,nm) in REGIONS.items())+
            "\n\n> Nota: el MLE (Multicultural London English) y el slang Gen-Z se "
            "difunden por todo el país vía música (grime/drill) y redes.\n")
with open(os.path.join(OUT,"uk-slang-regional.csv"),"w",encoding="utf-8",newline="") as f:
    w=csv.writer(f); w.writerow(["word","region_code","region","flag","meaning","note","emoji","category"]); w.writerows(rows)
print("UK terms:", len(DATA), "| filas CSV:", len(rows))
