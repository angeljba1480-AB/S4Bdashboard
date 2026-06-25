# -*- coding: utf-8 -*-
import csv, os
OUT = os.path.dirname(os.path.abspath(__file__))

# Regiones / variedades de EE. UU.
REGIONS = {
 "NE":("🗽","Northeast / NYC"),
 "BOS":("☘️","Boston / New England"),
 "PHL":("🔔","Philadelphia"),
 "SOUTH":("🤠","South / Dixie"),
 "TX":("⭐","Texas"),
 "MIDWEST":("🌽","Midwest"),
 "CHI":("🌭","Chicago"),
 "WEST":("🌴","West Coast / California"),
 "PNW":("🌲","Pacific Northwest"),
 "HI":("🌺","Hawaii (Pidgin)"),
 "AAVE":("🎤","AAVE (African American Vernacular)"),
 "GENZ":("📱","Gen-Z (nationwide)"),
}

# (word, emoji, category, meaning, [(region_code, note_optional), ...])
DATA = [
 ("Wicked","💯","Intensifier","'very / really' (wicked good)", [("BOS","wicked cold = very cold")]),
 ("Y'all","🤠","Pronoun","'you all' (plural you)", [("SOUTH",None),("TX",None)]),
 ("Yinz","👥","Pronoun","'you all' (Pittsburgh)", [("MIDWEST","Pittsburgh-specific")]),
 ("Youse / Youse guys","👥","Pronoun","'you all'", [("NE","NY/NJ"),("CHI",None)]),
 ("Pop","🥤","Noun","carbonated soft drink", [("MIDWEST",None),("PNW",None)]),
 ("Soda","🥤","Noun","carbonated soft drink", [("NE",None),("WEST",None)]),
 ("Coke","🥤","Noun","ANY soft drink (generic)", [("SOUTH","'what kind of coke?'")]),
 ("Hella","💯","Intensifier","'a lot / very'", [("WEST","NorCal origin")]),
 ("Jawn","🫳","Noun","catch-all noun for anything/anyone", [("PHL","'pass me that jawn'")]),
 ("Bodega","🏪","Noun","corner store", [("NE","NYC")]),
 ("The City","🏙️","Noun","refers to the nearest big city (often NYC/SF)", [("NE","= Manhattan"),("WEST","= San Francisco")]),
 ("Bubbler","⛲","Noun","water/drinking fountain", [("BOS",None),("MIDWEST","Wisconsin")]),
 ("Frappe","🥤","Noun","milkshake (with ice cream)", [("BOS",None)]),
 ("Grinder / Hoagie / Sub / Hero","🥪","Noun","long sandwich", [("BOS","grinder"),("PHL","hoagie"),("NE","hero (NYC)")]),
 ("Pop / Soda / Coke","🥤","Noun","(see regional split for soft drink)", [("MIDWEST",None)]),
 ("Tennis shoes / Sneakers / Gym shoes","👟","Noun","athletic shoes", [("SOUTH","tennis shoes"),("NE","sneakers"),("CHI","gym shoes")]),
 ("Buggy","🛒","Noun","shopping cart", [("SOUTH",None)]),
 ("Fixin' to","⏳","Phrase","'about to / getting ready to'", [("SOUTH",None),("TX",None)]),
 ("Bless your heart","😇","Phrase","sympathy OR subtle insult (context!)", [("SOUTH",None)]),
 ("Reckon","🤔","Verb","'think / suppose'", [("SOUTH",None)]),
 ("Ope","😯","Interjection","'oops / excuse me' (bumping into someone)", [("MIDWEST",None)]),
 ("You betcha","👍","Phrase","'yes, absolutely'", [("MIDWEST","Minnesota/Dakotas")]),
 ("Uff da","😅","Interjection","exclamation of surprise/dismay (Scandinavian)", [("MIDWEST","Minnesota")]),
 ("Cattywampus","↩️","Adjective","crooked / askew / messed up", [("SOUTH",None),("MIDWEST",None)]),
 ("Janky","🔧","Adjective","low quality / unreliable", [("GENZ",None),("WEST",None)]),
 ("Hyphy","🔊","Adjective","hyped / wild (Bay Area)", [("WEST","Oakland")]),
 ("Gnarly","🤙","Adjective","intense (good or bad) / surfer term", [("WEST",None)]),
 ("Stoked","🤩","Adjective","very excited", [("WEST",None)]),
 ("Bet","✅","Interjection","'okay / it's a deal / for sure'", [("GENZ",None),("AAVE",None)]),
 ("Finna","⏳","Verb","'fixing to / about to'", [("AAVE",None),("SOUTH",None)]),
 ("Cap / No cap","🧢","Slang","lie / 'no lie, for real'", [("AAVE",None),("GENZ",None)]),
 ("Bussin'","🤤","Adjective","really good (esp. food)", [("AAVE",None),("GENZ",None)]),
 ("Drip","💧","Noun","stylish outfit / swagger", [("AAVE",None),("GENZ",None)]),
 ("Salty","🧂","Adjective","bitter / upset", [("GENZ",None)]),
 ("Lowkey / Highkey","🤫","Adverb","'secretly / openly'", [("GENZ",None)]),
 ("Sus","🤨","Adjective","suspicious", [("GENZ",None)]),
 ("Rizz","😏","Noun","charisma / flirting skill", [("GENZ",None)]),
 ("Bougie","💅","Adjective","fancy / upper-class (from bourgeois)", [("AAVE",None),("GENZ",None)]),
 ("Tight","😤","Adjective","cool OR annoyed (regional)", [("NE","'that's tight' = cool"),("WEST",None)]),
 ("Dank","🔥","Adjective","high quality (esp. memes/weed)", [("GENZ",None),("WEST",None)]),
 ("Crunchy","🥾","Adjective","hippie / granola lifestyle", [("PNW",None),("WEST",None)]),
 ("Spendy","💸","Adjective","expensive", [("PNW",None),("MIDWEST",None)]),
 ("Spilling tea","☕","Phrase","sharing gossip", [("GENZ",None),("AAVE",None)]),
 ("Whip","🚗","Noun","car", [("AAVE",None),("GENZ",None)]),
 ("Plug","🔌","Noun","connection / supplier", [("AAVE",None),("GENZ",None)]),
 ("Slaps","🔊","Verb","'this song slaps' = is great", [("GENZ",None)]),
 ("Mid","😐","Adjective","mediocre", [("GENZ",None)]),
 ("Glizzy","🌭","Noun","hot dog", [("GENZ",None),("AAVE",None)]),
 ("Da kine","🤙","Noun","catch-all word for anything (like 'jawn')", [("HI","Pidgin")]),
 ("Shoots","👍","Interjection","'okay / sounds good'", [("HI","Pidgin")]),
 ("Brah","🤙","Noun","bro / friend", [("HI",None),("WEST",None)]),
 ("Slippahs","🩴","Noun","flip-flops / sandals", [("HI","Pidgin")]),
 ("Wicked pissah","💢","Phrase","'awesome / excellent'", [("BOS",None)]),
 ("Down the shore","🏖️","Phrase","going to the beach", [("PHL","NJ/Philly"),("NE",None)]),
 ("Water ice","🍧","Noun","Italian ice / shaved-ice dessert", [("PHL",None)]),
 ("Drawlin'","😒","Verb","acting up / being extra", [("AAVE","Atlanta")]),
 ("Pull up","🚙","Phrase","'come over / show up'", [("AAVE",None),("GENZ",None)]),
 ("Cap city","🧢","Phrase","total lie", [("AAVE",None)]),
 ("Gucci","👌","Adjective","good / fine ('we're gucci')", [("GENZ",None)]),
 ("Sketchy / Sketch","👀","Adjective","shady / unsafe", [("WEST",None),("GENZ",None)]),
 ("Catch a vibe","✨","Phrase","get into a good mood", [("GENZ",None),("AAVE",None)]),
]

rows = []
md = []
md.append("# 🇺🇸 US English slang — modismos por región\n")
md.append("> Palabras y expresiones de inglés que **cambian según la región de EE. UU.** "
          "(o por variedad como AAVE y la jerga Gen-Z nacional), con su **emoji**. "
          "Datos en [`us-slang-regional.csv`](./us-slang-regional.csv).\n")
md.append("\n| # | Word/Phrase | Meaning | Region(s) | Emoji |\n|---|---|---|---|---|")
for i,(word,emoji,cat,meaning,regs) in enumerate(DATA,1):
    reg_str = " · ".join(
        f"{REGIONS[rc][0]} {REGIONS[rc][1]}" + (f" ({note})" if note else "")
        for rc,note in regs if rc in REGIONS)
    md.append(f"| {i} | **{word}** | {meaning} | {reg_str} | {emoji} |")
    for rc,note in regs:
        if rc in REGIONS:
            flag,name = REGIONS[rc]
            rows.append([word, rc, name, flag, meaning, note or "", emoji, cat])

with open(os.path.join(OUT,"us-slang-regional.md"),"w",encoding="utf-8") as f:
    f.write("\n".join(md)+"\n\n---\n\n## Leyenda de regiones\n\n" +
            "\n".join(f"- {flag} **{name}** (`{code}`)" for code,(flag,name) in REGIONS.items()) +
            "\n\n> Nota: la jerga regional evoluciona y se mezcla; muchos términos AAVE/Gen-Z "
            "se usan en todo el país gracias a la música y las redes.\n")

with open(os.path.join(OUT,"us-slang-regional.csv"),"w",encoding="utf-8",newline="") as f:
    w = csv.writer(f)
    w.writerow(["word","region_code","region","flag","meaning","note","emoji","category"])
    w.writerows(rows)

print("US terms:", len(DATA), "| filas CSV:", len(rows))
