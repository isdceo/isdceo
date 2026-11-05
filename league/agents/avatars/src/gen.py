"""캐리커처 화풍 캐릭터 14명 SVG 생성 (viewBox 0 0 120 120, #av-<이름>)."""
import random, sys, json, pathlib

OL = "#2a1a12"          # 외곽선
def stubble(pid, seed, x0, x1, y0, y1, n=70, col="#3a2a20", op=.45):
    r = random.Random(seed)
    dots = "".join(f'<circle cx="{r.uniform(x0,x1):.1f}" cy="{r.uniform(y0,y1):.1f}" r="{r.uniform(.35,.7):.2f}"/>' for _ in range(n))
    return f'<g clip-path="url(#{pid}-jaw)" fill="{col}" opacity="{op}">{dots}</g>'

HEAD = {
  "round":  "M33 52 C33 29 48 17 63 17 C81 17 92 31 91 50 C90 67 84 80 70 86 C61 90 49 88 43 80 C36 72 33 63 33 52 Z",
  "long":   "M35 50 C35 26 49 15 63 15 C80 15 90 29 89 48 C88 68 82 86 68 92 C59 95 49 91 44 82 C38 72 35 62 35 50 Z",
  "square": "M33 50 C33 27 47 16 63 16 C81 16 92 29 92 48 C92 64 89 78 80 86 C71 92 52 92 44 85 C36 78 33 64 33 50 Z",
  "kid":    "M31 56 C31 33 45 21 62 21 C80 21 93 34 92 54 C91 70 83 82 68 86 C57 89 45 86 39 78 C33 71 31 64 31 56 Z",
}
JAW = "M30 66 H95 V96 H30 Z"

def body(pid, c):
    o = c["outfit"]
    s = f'<path d="M8 124 Q12 98 38 90 L60 100 L84 90 Q110 98 114 124 Z" fill="{o["color"]}" stroke="{OL}" stroke-width="2"/>'
    if o.get("plaid"):
        s += (f'<g clip-path="url(#{pid}-body)" stroke="{o["plaid"]}" stroke-width="1.6" opacity=".7">'
              + "".join(f'<path d="M{x} 86 L{x-8} 124"/>' for x in range(14, 116, 11))
              + "".join(f'<path d="M0 {y} H120" />' for y in range(96, 124, 9)) + "</g>")
    if o.get("stripes"):
        s += f'<g clip-path="url(#{pid}-body)" stroke="{o["stripes"]}" stroke-width="3">' + "".join(f'<path d="M0 {y} H120"/>' for y in range(97, 124, 7)) + "</g>"
    if o.get("dots"):
        r = random.Random(7)
        s += f'<g clip-path="url(#{pid}-body)" fill="{o["dots"]}">' + "".join(f'<circle cx="{r.uniform(10,110):.0f}" cy="{r.uniform(94,122):.0f}" r="2.2"/>' for _ in range(26)) + "</g>"
    # 몸 그늘
    s += f'<path d="M8 124 Q12 98 38 90 L46 94 Q30 104 28 124 Z" fill="#000" opacity=".22"/>'
    inner = o.get("inner")
    if inner:
        s += f'<path d="M46 92 L60 100 L74 92 L72 124 H48 Z" fill="{inner}" stroke="{OL}" stroke-width="1.6"/>'
    col = o.get("collar", "shirt")
    if col == "shirt":
        cc = o.get("collarc", o["color"])
        s += (f'<path d="M44 89 L60 101 L50 106 L40 94 Z" fill="{cc}" stroke="{OL}" stroke-width="1.8" stroke-linejoin="round"/>'
              f'<path d="M76 89 L60 101 L70 106 L80 94 Z" fill="{cc}" stroke="{OL}" stroke-width="1.8" stroke-linejoin="round"/>')
    elif col == "sailor":
        s += (f'<path d="M36 92 L60 112 L84 92 L90 100 L60 122 L30 100 Z" fill="#1f3f73" stroke="{OL}" stroke-width="1.8"/>'
              f'<path d="M37 97 L60 116 L83 97" stroke="#fff" stroke-width="1.8" fill="none"/>'
              f'<path d="M54 110 L60 118 L66 110 L63 124 H57 Z" fill="#c0392b" stroke="{OL}" stroke-width="1.4"/>')
    elif col == "hood":
        s += f'<path d="M30 96 Q60 84 90 96 Q86 106 60 106 Q34 106 30 96 Z" fill="{o.get("collarc", o["color"])}" stroke="{OL}" stroke-width="1.8"/>'
    tie = o.get("tie")
    if tie == "bow":
        s += f'<path d="M50 99 L60 103 L70 99 L70 109 L60 105 L50 109 Z" fill="{o["tiec"]}" stroke="{OL}" stroke-width="1.6"/><circle cx="60" cy="104" r="2.6" fill="{o["tiec"]}" stroke="{OL}" stroke-width="1.4"/>'
    elif tie:
        s += f'<path d="M57 101 L63 101 L65 106 L62 124 H58 L55 106 Z" fill="{o["tiec"]}" stroke="{OL}" stroke-width="1.6"/>'
    return s

def eyes(c):
    e = c.get("eyes", {})
    lx, rx, y = 51, 73, 54
    lr, rr = e.get("lr", 8.5), e.get("rr", 6.8)
    look = e.get("look", (1.6, .6))
    s = ""
    for x, r, k in ((lx, lr, "l"), (rx, rr, "r")):
        if e.get(k) == "squint":
            s += f'<path d="M{x-r} {y} Q{x} {y-r*.55} {x+r} {y}" stroke="{OL}" stroke-width="2.6" fill="none" stroke-linecap="round"/>'
            continue
        if e.get(k) == "wink":
            s += f'<path d="M{x-r} {y+1} Q{x} {y+r*.7} {x+r} {y+1}" stroke="{OL}" stroke-width="2.8" fill="none" stroke-linecap="round"/>'
            continue
        ry_ = r * e.get("open", 1.0)
        s += f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{ry_:.1f}" fill="#fff" stroke="{OL}" stroke-width="1.8"/>'
        pr = r * .46
        s += f'<circle cx="{x+look[0]}" cy="{y+look[1]}" r="{pr:.1f}" fill="{e.get("iris", "#3a2414")}"/><circle cx="{x+look[0]}" cy="{y+look[1]}" r="{pr*.55:.1f}" fill="#120a06"/>'
        s += f'<circle cx="{x+look[0]-pr*.45:.1f}" cy="{y+look[1]-pr*.45:.1f}" r="{pr*.32:.1f}" fill="#fff"/>'
        if e.get("lid"):
            s += f'<path d="M{x-r-.5} {y-1} Q{x} {y-r*1.05} {x+r+.5} {y-1} L{x+r} {y-r*.25} Q{x} {y-r*.55} {x-r} {y-r*.25} Z" fill="{c["skin"]}" stroke="{OL}" stroke-width="1.6"/>'
    return s

def glasses(c):
    g = c.get("glasses")
    if not g: return ""
    lx, rx, y = 51, 73, 54
    col = c.get("glassc", OL)
    if g == "round":
        return (f'<circle cx="{lx}" cy="{y}" r="11.5" fill="#cfe6ff" fill-opacity=".18" stroke="{col}" stroke-width="3.2"/>'
                f'<circle cx="{rx}" cy="{y}" r="9" fill="#cfe6ff" fill-opacity=".18" stroke="{col}" stroke-width="3"/>'
                f'<path d="M62.5 53 Q63 50 64.2 52.5" stroke="{col}" stroke-width="2.6" fill="none"/>'
                f'<path d="M39.5 53 L33 51" stroke="{col}" stroke-width="2.6"/>'
                f'<path d="M45 47 Q48 45 51 46" stroke="#fff" stroke-width="1.6" fill="none" opacity=".8"/>')
    if g == "half":
        return (f'<path d="M40 54 H62 Q61 64 51 64 Q41 64 40 54 Z" fill="#cfe6ff" fill-opacity=".2" stroke="{col}" stroke-width="2.6"/>'
                f'<path d="M64.5 54 H82 Q81 62 73 62 Q65 62 64.5 54 Z" fill="#cfe6ff" fill-opacity=".2" stroke="{col}" stroke-width="2.4"/>'
                f'<path d="M62 54 H64.5 M40 54 L33 52" stroke="{col}" stroke-width="2.4"/>')
    if g == "square":
        return (f'<rect x="39" y="45" width="24" height="18" rx="3" fill="#cfe6ff" fill-opacity=".18" stroke="{col}" stroke-width="3.4"/>'
                f'<rect x="64.5" y="46" width="18" height="15" rx="3" fill="#cfe6ff" fill-opacity=".18" stroke="{col}" stroke-width="3"/>'
                f'<path d="M63 52 H64.5 M39 52 L33 51" stroke="{col}" stroke-width="2.6"/>')
    if g == "sun":
        return (f'<path d="M37 47 H63 Q63 62 50 62 Q38 62 37 47 Z" fill="#1d2a3a" stroke="{OL}" stroke-width="2.4"/>'
                f'<path d="M64.5 47 H85 Q85 60 74 60 Q65 60 64.5 47 Z" fill="#1d2a3a" stroke="{OL}" stroke-width="2.2"/>'
                f'<path d="M63 48 H64.5 M37 48 L32 47" stroke="{OL}" stroke-width="2.6"/>'
                f'<path d="M41 50 L48 57 M44 49 L52 57 M68 50 L74 56" stroke="#9fd8ff" stroke-width="1.6" opacity=".85"/>')
    if g == "goggles":
        return (f'<path d="M30 38 Q60 28 92 36" stroke="#5a3a22" stroke-width="5" fill="none"/>'
                f'<circle cx="49" cy="36" r="8.5" fill="#7fd6c4" stroke="#8a6414" stroke-width="3.2"/><circle cx="71" cy="35" r="7.5" fill="#7fd6c4" stroke="#8a6414" stroke-width="3"/>'
                f'<path d="M45 32 Q48 30 51 31 M68 31 Q70 30 72 31" stroke="#fff" stroke-width="1.6" fill="none"/>')
    if g == "loupe":
        return (f'<circle cx="{rx}" cy="{y}" r="11" fill="#cfe6ff" fill-opacity=".25" stroke="#1d1d22" stroke-width="5"/>'
                f'<path d="M84 54 L92 56" stroke="#1d1d22" stroke-width="3"/>')
    return ""

def nose(c):
    n = c.get("nose", "bulb")
    col = c.get("nosec", "#e58a74")
    if n == "bulb":
        return (f'<path d="M62 56 Q60 63 58 66 Q56 72 63 73 Q70 74 71 68 Q71 63 66 62 Z" fill="{col}" stroke="{OL}" stroke-width="1.8" stroke-linejoin="round"/>'
                f'<ellipse cx="66" cy="66" rx="2.4" ry="1.6" fill="#fff" opacity=".65"/>')
    if n == "long":
        return (f'<path d="M62 54 Q61 63 57 69 Q56 73 62 73 Q69 73 69 69 Q66 64 65 56 Z" fill="{col}" stroke="{OL}" stroke-width="1.8" stroke-linejoin="round"/>'
                f'<ellipse cx="63" cy="69" rx="2" ry="1.3" fill="#fff" opacity=".6"/>')
    if n == "button":
        return f'<ellipse cx="63" cy="66" rx="4.6" ry="3.6" fill="{col}" stroke="{OL}" stroke-width="1.6"/><circle cx="64.5" cy="64.8" r="1.2" fill="#fff" opacity=".7"/>'
    return ""

def mouth(c):
    m = c.get("mouth", "grin")
    if m == "grin":
        return (f'<path d="M46 74 Q62 90 80 72 Q63 79 46 74 Z" fill="#fff" stroke="{OL}" stroke-width="2.2" stroke-linejoin="round"/>'
                f'<path d="M48 75.5 Q62 82 79 73.5" stroke="#c9c2b2" stroke-width="1" fill="none"/>'
                f'<path d="M55 77 V80 M62 77.6 V82 M69 77 V80.5" stroke="#c9c2b2" stroke-width=".9"/>'
                f'<path d="M44 72 Q45 75 47 75.5 M79 70.5 Q81 71 81 73" stroke="{OL}" stroke-width="1.6" fill="none" stroke-linecap="round"/>')
    if m == "smirk":
        return (f'<path d="M50 78 Q62 80 77 70" stroke="{OL}" stroke-width="2.6" fill="none" stroke-linecap="round"/>'
                f'<path d="M76 68.5 Q79 70 77.5 72.5" stroke="{OL}" stroke-width="1.8" fill="none" stroke-linecap="round"/>')
    if m == "laugh":
        return (f'<path d="M47 73 Q62 94 80 71 Q63 78 47 73 Z" fill="#7a2a1e" stroke="{OL}" stroke-width="2.2" stroke-linejoin="round"/>'
                f'<path d="M49 74.2 Q63 80 78 72.2 L77 75 Q63 81 50 76.5 Z" fill="#fff"/>'
                f'<path d="M56 84 Q62 81 68 84 Q63 88 56 84 Z" fill="#e0675a"/>')
    if m == "tongue":
        return (f'<path d="M48 74 Q62 88 79 72 Q63 78 48 74 Z" fill="#fff" stroke="{OL}" stroke-width="2.2" stroke-linejoin="round"/>'
                f'<path d="M63 78.5 Q64 88 70 87 Q74 85 72 77 Z" fill="#e0675a" stroke="{OL}" stroke-width="1.6"/>')
    if m == "gap":
        return (f'<path d="M48 74 Q62 88 78 72 Q63 78 48 74 Z" fill="#fff" stroke="{OL}" stroke-width="2.2" stroke-linejoin="round"/>'
                f'<rect x="60.5" y="76.5" width="3" height="5" fill="#7a2a1e"/>')
    return ""

def brows(c):
    b = c.get("brows", "up")
    col = c.get("browc", c["hairc"])
    w = c.get("broww", 4.6)
    d = {"up": "M40 41 Q48 34 58 40 M65 39 Q73 34 81 40",
         "skeptic": "M40 45 L58 44 M65 37 Q74 30 82 37",
         "worry": "M40 44 Q48 38 57 42 M66 41 Q74 37 82 42",
         "angry": "M40 39 L58 45 M65 45 L82 38",
         "bushy": "M38 43 Q48 33 59 41 M64 40 Q74 32 84 42"}[b]
    return f'<path d="{d}" stroke="{col}" stroke-width="{w}" fill="none" stroke-linecap="round"/>'

def char(name, c):
    pid = f"av-{name}"
    head = HEAD[c.get("head", "round")]
    s = [f'<g id="{pid}">']
    s.append(f'<defs><clipPath id="{pid}-h"><path d="{head}"/></clipPath>'
             f'<clipPath id="{pid}-jaw"><path d="{head}" transform="translate(0 0)"/></clipPath>'
             f'<clipPath id="{pid}-body"><path d="M8 124 Q12 98 38 90 L60 100 L84 90 Q110 98 114 124 Z"/></clipPath></defs>')
    bg = "av-bgC" if c["team"] == "c" else "av-bgS"
    s.append(f'<circle cx="60" cy="60" r="57" fill="url(#{bg})"/>')
    s.append('<g clip-path="url(#av-disc)">')
    s.append('<path d="M70 -4 L104 -4 L50 124 L22 124 Z" fill="#fff" opacity=".10"/><path d="M98 -4 L112 -4 L64 124 L54 124 Z" fill="#fff" opacity=".07"/>')
    s.append(c.get("back", ""))
    s.append(body(pid, c))
    # 목
    s.append(f'<path d="M50 80 L50 96 Q60 102 70 96 L70 80 Z" fill="{c["skin"]}" stroke="{OL}" stroke-width="1.8"/><path d="M50 86 Q60 94 70 86 L70 80 H50 Z" fill="#000" opacity=".2"/>')
    s.append(c.get("over_body", ""))
    s.append("</g>")
    s.append(c.get("hair_back", ""))
    # 귀
    s.append(f'<path d="M36 52 Q26 50 27 60 Q28 70 38 68 Z" fill="{c["skin"]}" stroke="{OL}" stroke-width="2"/><path d="M34 56 Q30 58 33 63" stroke="{OL}" stroke-width="1.4" fill="none" opacity=".7"/>')
    # 얼굴
    s.append(f'<path d="{head}" fill="{c["skin"]}" stroke="{OL}" stroke-width="2.4"/>')
    s.append(f'<g clip-path="url(#{pid}-h)"><ellipse cx="30" cy="70" rx="22" ry="34" fill="{c["shade"]}" opacity=".55"/>'
             f'<ellipse cx="60" cy="94" rx="34" ry="12" fill="{c["shade"]}" opacity=".5"/>'
             f'<ellipse cx="72" cy="30" rx="14" ry="8" fill="#fff" opacity=".22"/></g>')
    if c.get("stubble"):
        s.append(stubble(pid, name, 36, 90, 66, 92, n=c.get("stubn", 80), col=c.get("stubc", "#3a2a20")))
    s.append(f'<ellipse cx="44" cy="66" rx="5" ry="3" fill="#f07a6a" opacity=".35"/><ellipse cx="81" cy="64" rx="4" ry="2.6" fill="#f07a6a" opacity=".3"/>')
    if c.get("head") != "kid":
        s.append(f'<path d="M44 63 Q51 67 58 63 M67 61.5 Q73 64.5 79 61.5" stroke="{c["shade"]}" stroke-width="1.3" fill="none" opacity=".9"/>')
    s.append(f'<path d="M44 69 Q40 74 43.5 79 M82 67 Q86 71 84 76" stroke="{OL}" stroke-width="1.5" fill="none" opacity=".55" stroke-linecap="round"/>'
             f'<path d="M57 73.5 Q63 76 69 73" stroke="{c["shade"]}" stroke-width="2.2" fill="none" opacity=".6"/>'
             f'<path d="M57 89 Q63 91.5 69 88.5" stroke="{OL}" stroke-width="1.3" fill="none" opacity=".45"/>'
             f'<ellipse cx="80" cy="58" rx="4" ry="2.2" fill="#fff" opacity=".22"/>')
    s.append(c.get("face_extra", ""))
    if c.get("mouth_over"):
        s.append(c.get("beard", "")); s.append(mouth(c))
    else:
        s.append(mouth(c)); s.append(c.get("beard", ""))
    s.append(eyes(c))
    s.append(nose(c))
    s.append(c.get("mustache", ""))
    s.append(brows(c))
    s.append(glasses(c))
    s.append(c.get("hair", ""))
    s.append(c.get("front", ""))
    if c.get("prop"):
        s.append(f'<g clip-path="url(#av-disc)"><g transform="{c.get('propt', '')}">{c["prop"]}</g></g>')
    s.append('<circle cx="60" cy="60" r="57" fill="none" stroke="#fff" stroke-opacity=".75" stroke-width="3"/>')
    s.append("</g>")
    return "".join(s)

SKIN = {"tan": ("#e7a77a", "#b86b45"), "light": ("#f3c7a2", "#c98a63"), "deep": ("#c98457", "#8e5432"), "pale": ("#f6d6bd", "#d09a7c"), "brown": ("#a8693f", "#6e3f22")}
def sk(k): return {"skin": SKIN[k][0], "shade": SKIN[k][1]}

C = json.loads(pathlib.Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 else None
