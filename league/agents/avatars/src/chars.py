import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen import *
O = OL
def strands(pts, col, w=1.4, op=.6):
    return "".join(f'<path d="{p}" stroke="{col}" stroke-width="{w}" fill="none" stroke-linecap="round" opacity="{op}"/>' for p in pts)

CH = {}
# 1 뚝심이: 거북이 등껍질 배낭을 멘 대머리 할아버지
CH["ttukshim"] = dict(team="c", **sk("light"), hairc="#f2f2f2", browc="#f7f7f7", brows="bushy", broww=6.2,
  glasses="round", glassc="#8a6414", nose="bulb", mouth="grin", eyes={"lr": 7.5, "rr": 6, "lid": True},
  back=f'<ellipse cx="60" cy="104" rx="56" ry="30" fill="#7a5a2b" stroke="{O}" stroke-width="2.2"/>'
       + strands(["M10 100 L26 88 L44 92", "M110 100 L94 88 L76 92", "M26 88 L22 76", "M94 88 L98 76"], "#4a3416", 2.4, .9),
  outfit={"color": "#5f8a4e", "inner": "#f4ecd6", "collar": "shirt", "collarc": "#f4ecd6"},
  over_body=f'<path d="M34 92 L40 124 M86 92 L80 124" stroke="#5e3c1a" stroke-width="6"/><path d="M34 92 L40 124 M86 92 L80 124" stroke="#a87a3a" stroke-width="2" stroke-dasharray="3 3"/>',
  mustache=f'<path d="M48 72 Q55 64 63 69 Q71 64 79 71 Q74 78 64 74 Q55 79 48 72 Z" fill="#f7f7f7" stroke="#a9a9a9" stroke-width="1.4"/>',
  hair=f'<path d="M34 54 Q27 40 37 33 Q37 41 42 44 Q37 47 34 54 Z" fill="#f2f2f2" stroke="#9a9a9a" stroke-width="1.4"/>'
       f'<path d="M88 46 Q95 36 89 28 Q90 37 85 40 Z" fill="#f2f2f2" stroke="#9a9a9a" stroke-width="1.4"/>'
       f'<ellipse cx="66" cy="24" rx="12" ry="5" fill="#fff" opacity=".5" transform="rotate(-12 66 24)"/>')

# 2 발굴왕: 헤드랜턴 안전모의 광부
CH["balgul"] = dict(team="c", **sk("tan"), hairc="#2b1d14", brows="up", broww=5, stubble=True, nose="bulb", mouth="laugh",
  eyes={"lr": 8.5, "rr": 7},
  outfit={"color": "#3a6ea8", "plaid": "#1f3f73", "collar": "shirt"},
  over_body=f'<path d="M40 104 H80 L86 124 H34 Z" fill="#e07a2a" stroke="{O}" stroke-width="1.8"/><path d="M44 104 L40 92 M76 104 L80 92" stroke="#e07a2a" stroke-width="5"/><circle cx="46" cy="106" r="2" fill="#f2c230" stroke="{O}"/><circle cx="74" cy="106" r="2" fill="#f2c230" stroke="{O}"/>',
  face_extra='<ellipse cx="42" cy="58" rx="5" ry="3" fill="#2b1d14" opacity=".28"/><ellipse cx="80" cy="74" rx="4" ry="2" fill="#2b1d14" opacity=".25"/>',
  hair=f'<path d="M33 48 Q30 40 36 38 L40 46 Z M89 44 Q94 38 91 34 L86 42 Z" fill="#2b1d14"/>',
  front=f'<circle cx="62" cy="23" r="15" fill="#fff6a0" opacity=".35"/>'
        f'<path d="M29 41 Q30 10 62 9 Q92 10 94 38 Z" fill="#f2c230" stroke="{O}" stroke-width="2.4"/>'
        f'<path d="M44 14 Q40 24 40 38 M62 9 V36" stroke="#c99a1e" stroke-width="2.4" fill="none"/>'
        f'<path d="M22 42 Q62 31 101 37 Q102 44 97 45 Q62 38 25 48 Z" fill="#e0ad22" stroke="{O}" stroke-width="2.2"/>'
        f'<rect x="54" y="16" width="16" height="12" rx="3" fill="#4a4f5a" stroke="{O}" stroke-width="1.8"/><circle cx="62" cy="22" r="4.5" fill="#fffbe0" stroke="{O}" stroke-width="1.4"/>'
        f'<path d="M36 22 Q42 14 50 12" stroke="#fff" stroke-width="2.4" fill="none" opacity=".6"/>')

# 3 큰그림: 지구본을 든 은발 교수
CH["keun"] = dict(propt="translate(-9 -4)", team="c", **sk("pale"), head="long", hairc="#d9dde3", browc="#e8ebef", brows="bushy", broww=5.4,
  glasses="half", nose="long", mouth="grin", eyes={"lr": 7.5, "rr": 6, "lid": True, "look": (1.2, 1.6)},
  outfit={"color": "#8a6a4a", "plaid": "#5e4428", "inner": "#f4ecd6", "collar": "shirt", "collarc": "#f4ecd6", "tie": "bow", "tiec": "#b8352a"},
  beard=f'<path d="M56 84 Q62 92 70 84 Q66 96 62 97 Q57 96 56 84 Z" fill="#e8ebef" stroke="#9aa0a8" stroke-width="1.4"/>',
  hair=f'<path d="M35 48 Q28 22 50 12 Q74 2 92 20 Q102 32 96 52 Q93 40 86 32 Q74 22 58 25 Q44 28 40 46 Z" fill="#d9dde3" stroke="#7a808a" stroke-width="2"/>'
       + strands(["M44 22 Q60 12 80 16", "M48 28 Q66 18 88 26", "M88 30 Q96 38 95 48"], "#9aa0a8", 1.5, .9)
       + strands(["M52 16 Q66 9 82 13"], "#fff", 1.8, .7),
  prop=f'<path d="M84 122 Q96 112 112 118" stroke="#8a6414" stroke-width="3" fill="none"/>'
        f'<circle cx="97" cy="101" r="14" fill="#3b8fd6" stroke="{O}" stroke-width="2.2"/>'
        f'<path d="M88 94 Q93 90 98 94 Q100 99 95 101 Q91 104 89 100 Z M100 104 Q106 102 108 107 Q104 112 100 109 Z" fill="#5cb85c" stroke="#2f6b2f" stroke-width="1"/>'
        f'<path d="M84 98 Q97 92 110 98" stroke="#fff" stroke-width="1.2" opacity=".6" fill="none"/>')

# 4 미래광: 고글 쓴 괴짜 발명가
CH["mirae"] = dict(team="c", **sk("light"), hairc="#3a2f5a", brows="up", broww=5, nose="bulb", mouth="grin",
  eyes={"lr": 10.5, "rr": 8.5, "look": (0, 0), "iris": "#2a6b6b"},
  outfit={"color": "#f4f4f4", "inner": "#2fa58f", "collar": "shirt", "collarc": "#ffffff"},
  over_body=f'<path d="M84 104 L88 124" stroke="{O}" stroke-width="1.2" opacity=".4"/><rect x="78" y="108" width="12" height="8" rx="1" fill="#e6e6e6" stroke="{O}" stroke-width="1.2"/><path d="M81 108 V102 M85 108 V101" stroke="#3b6fb6" stroke-width="2"/>',
  hair=f'<path d="M33 46 L26 30 L38 34 L36 16 L48 26 L52 6 L60 22 L70 4 L72 22 L86 10 L84 26 L98 22 L90 36 L100 42 L90 46 Q86 30 62 28 Q42 30 38 46 Z" fill="#3a2f5a" stroke="{O}" stroke-width="2" stroke-linejoin="round"/>'
       + strands(["M48 26 L54 34", "M70 20 L68 30", "M84 26 L80 32"], "#7a6ab0", 1.6, .9),
  front=CH_GOG if (CH_GOG := '') else '' )
CH["mirae"]["front"] = (f'<path d="M34 34 Q62 22 92 32" stroke="#5a3a22" stroke-width="5" fill="none"/>'
   f'<circle cx="50" cy="31" r="8.5" fill="#7fd6c4" stroke="#8a6414" stroke-width="3.2"/><circle cx="72" cy="29" r="7.5" fill="#7fd6c4" stroke="#8a6414" stroke-width="3"/>'
   f'<path d="M46 27 Q49 25 52 26 M69 26 Q71 25 73 26" stroke="#fff" stroke-width="1.6" fill="none"/>'
   f'<path d="M100 60 L102 64 L106 66 L102 68 L100 72 L98 68 L94 66 L98 64 Z M18 80 L19.5 83 L23 84 L19.5 85 L18 88 L16.5 85 L13 84 L16.5 83 Z" fill="#ffe27a"/>')

# 5 삐딱이: 비스듬한 중절모, 한쪽 눈썹을 치켜든 회의론자
CH["ppittak"] = dict(team="c", **sk("tan"), hairc="#2b1d14", brows="skeptic", broww=4.8, stubble=True, stubn=110, nose="long", mouth="smirk",
  eyes={"lr": 8, "rr": 7.5, "l": "squint", "look": (1.2, .8)},
  outfit={"color": "#33374d", "inner": "#f4f4f4", "collar": "shirt", "collarc": "#454a66", "tie": "long", "tiec": "#b8352a"},
  hair=f'<path d="M33 50 Q31 42 35 38 L40 50 Z M89 46 L91 38 L87 40 Z" fill="#2b1d14"/>',
  front=f'<g transform="rotate(-14 62 30)"><ellipse cx="62" cy="33" rx="40" ry="8" fill="#262838" stroke="{O}" stroke-width="2.2"/>'
        f'<path d="M38 33 Q38 8 62 8 Q86 8 86 33 Z" fill="#30334a" stroke="{O}" stroke-width="2.2"/>'
        f'<path d="M52 10 Q62 17 72 10" stroke="{O}" stroke-width="2" fill="none"/><rect x="38.5" y="25" width="47" height="7" fill="#b8352a"/>'
        f'<path d="M44 14 Q50 10 56 10" stroke="#fff" stroke-width="2" opacity=".35" fill="none"/></g>')

# 6 파도타기: 선글라스 서퍼
CH["pado"] = dict(team="c", **sk("deep"), hairc="#f2c75c", browc="#c99a3a", brows="up", glasses="sun", nose="bulb", nosec="#d9765a", mouth="laugh",
  outfit={"color": "#2fa58f", "dots": "#f2a33a", "collar": "shirt", "collarc": "#2a9480"},
  over_body='<path d="M44 96 Q60 106 76 96" stroke="#f4ecd6" stroke-width="2" fill="none" stroke-dasharray="2 3"/><circle cx="60" cy="104" r="3" fill="#f4ecd6" stroke="#2a1a12"/>',
  hair=f'<path d="M32 50 Q24 30 40 20 Q56 8 76 12 Q96 18 96 40 L90 36 L92 48 Q86 36 80 30 L76 38 L70 28 L64 36 L58 26 L52 36 L46 28 L40 44 Z" fill="#f2c75c" stroke="#8a6414" stroke-width="2" stroke-linejoin="round"/>'
       + strands(["M46 18 Q62 12 80 18", "M50 24 Q66 18 86 26"], "#fff1b8", 1.8, .9))

# 7 계산기: 계산기를 든 숫자광 (네모 안경, 단정한 가르마)
CH["gyesan"] = dict(propt="translate(9 -5)", team="c", **sk("light"), hairc="#16161c", brows="worry", broww=4, glasses="square", nose="button", mouth="gap",
  eyes={"lr": 7.5, "rr": 6.2, "look": (.4, .4)},
  outfit={"color": "#a9c8e8", "collar": "shirt", "collarc": "#ffffff", "tie": "long", "tiec": "#1f3f73"},
  over_body=f'<rect x="72" y="104" width="13" height="12" fill="#fff" stroke="{O}" stroke-width="1.4"/><path d="M75 104 V97 M79 104 V96 M82 104 V98" stroke="#c0392b" stroke-width="2"/>',
  hair=f'<path d="M33 50 Q30 22 54 16 Q80 12 90 28 Q94 36 92 46 Q88 34 76 30 L58 30 Q44 32 38 50 Z" fill="#16161c" stroke="{O}" stroke-width="2"/>'
       f'<path d="M56 18 Q58 24 58 30" stroke="#f3c7a2" stroke-width="1.6" fill="none"/>'
       + strands(["M62 18 Q76 18 86 26", "M40 30 Q46 22 54 20"], "#6a6a80", 1.6, .9),
  prop=f'<rect x="10" y="94" width="24" height="30" rx="3" fill="#2b2f38" stroke="{O}" stroke-width="2"/><rect x="13" y="97" width="18" height="7" rx="1" fill="#b8e0a8"/>'
        + "".join(f'<rect x="{13+(k%3)*6.3:.1f}" y="{107+(k//3)*5.3:.1f}" width="4.4" height="3.6" rx=".8" fill="{"#f2a33a" if k%3==2 else "#d8d8e0"}"/>' for k in range(9)))

# 8 단단이: 투구 쓴 기사, 방패
CH["dandan"] = dict(propt="translate(8 -6)", team="s", **sk("tan"), head="square", hairc="#3a2a20", brows="angry", broww=5.4, stubble=True, nose="bulb", mouth="grin",
  eyes={"lr": 7.8, "rr": 6.6},
  outfit={"color": "#9aa4b2", "collar": "none"},
  over_body=f'<path d="M30 100 Q60 90 90 100" stroke="#6b7482" stroke-width="2" fill="none"/><path d="M26 110 Q60 100 94 110" stroke="#6b7482" stroke-width="2" fill="none"/>',
  front=f'<path d="M29 52 Q28 12 62 10 Q96 12 95 50 L88 48 Q86 26 62 24 Q38 26 36 50 Z" fill="#c9d1db" stroke="{O}" stroke-width="2.4"/>'
        f'<path d="M36 34 Q62 22 90 32 L88 40 Q62 30 38 42 Z" fill="#9aa4b2" stroke="{O}" stroke-width="1.8"/>'
        f'<path d="M62 10 Q66 -4 82 0 Q74 4 72 12 Z" fill="#c0392b" stroke="{O}" stroke-width="1.6"/>'
        f'<path d="M42 18 Q50 13 58 12" stroke="#fff" stroke-width="2.4" opacity=".7" fill="none"/>'
        '', prop=f'<path d="M8 90 H36 V106 Q36 118 22 124 Q8 118 8 106 Z" fill="#2463b5" stroke="{O}" stroke-width="2.2"/><path d="M22 92 V120 M10 102 H34" stroke="#f2c230" stroke-width="3"/>')

# 9 알짜: 확대경을 낀 보석 감정사
CH["alzza"] = dict(propt="translate(-7 -5)", team="s", **sk("pale"), hairc="#5a3422", brows="up", broww=3.6, glasses="loupe", nose="button", nosec="#eaa08a", mouth="grin",
  eyes={"lr": 8, "rr": 10, "lid": False, "iris": "#4a6b2a"},
  outfit={"color": "#6b4fb5", "collar": "shirt", "collarc": "#8a6fd0"},
  hair_back=f'<circle cx="64" cy="14" r="12" fill="#5a3422" stroke="{O}" stroke-width="2"/><path d="M58 8 Q64 4 70 8" stroke="#8a5a3a" stroke-width="1.6" fill="none"/>',
  face_extra=f'<path d="M42 46 L40 43 M45 45 L44 42 M48 45 L48 42" stroke="{O}" stroke-width="1.4"/><path d="M48 77 Q62 84 77 74" stroke="#c0392b" stroke-width="2.4" fill="none" opacity=".6"/>',
  hair=f'<path d="M33 54 Q28 26 52 18 Q78 12 90 30 Q94 40 91 50 Q84 34 70 32 Q58 30 50 36 Q42 42 40 56 Z" fill="#5a3422" stroke="{O}" stroke-width="2"/>'
       + strands(["M48 22 Q64 16 82 24", "M38 40 Q44 28 56 24"], "#8a5a3a", 1.6, .9),
  prop=f'<path d="M30 68 L33 73 L30 78 L27 73 Z" fill="#2fd6c4" stroke="{O}" stroke-width="1.2"/>'
        f'<path d="M86 104 L96 96 L106 104 L96 120 Z" fill="#7fe0ff" stroke="{O}" stroke-width="1.8"/><path d="M86 104 H106 M92 104 L96 120 L100 104 M91 100 L94 104 M101 100 L98 104" stroke="#2a8fb0" stroke-width="1"/>'
        f'<path d="M108 92 L110 96 L114 97 L110 98 L108 102 L106 98 L102 97 L106 96 Z" fill="#fff"/>')

# 10 돋보기: 사냥모자 탐정, 커다란 돋보기
CH["dotbogi"] = dict(team="s", **sk("light"), hairc="#6b4a2a", brows="up", broww=4.6, nose="long", mouth="grin",
  eyes={"lr": 7.5, "rr": 12.5, "look": (1, .5)},
  outfit={"color": "#b08d60", "collar": "shirt", "collarc": "#c4a06e", "tie": "long", "tiec": "#5e4428"},
  over_body=f'<path d="M22 102 Q60 86 98 102 L102 112 Q60 96 18 112 Z" fill="#c4a06e" stroke="{O}" stroke-width="1.8"/>',
  front=f'<path d="M29 46 Q30 16 62 14 Q94 16 94 44 Q62 34 29 46 Z" fill="#b8955f" stroke="{O}" stroke-width="2.2"/>'
        + strands(["M36 30 L88 40", "M34 38 L80 24", "M50 16 L46 42", "M70 15 L72 38"], "#7a5c34", 1.6, .8)
        + f'<path d="M30 44 Q18 50 22 62 L34 52 Z M92 42 Q104 48 100 60 L88 50 Z" fill="#a8865a" stroke="{O}" stroke-width="1.8"/>'
        f'<path d="M58 14 Q62 6 66 14" stroke="{O}" stroke-width="2.2" fill="none"/>'
        f'<path d="M84 66 L104 92" stroke="#5e3c1a" stroke-width="8" stroke-linecap="round"/>'
        f'<circle cx="73" cy="54" r="16" fill="#cfe6ff" fill-opacity=".22" stroke="#d4b25c" stroke-width="5"/>'
        f'<path d="M63 45 Q66 41 71 40" stroke="#fff" stroke-width="2.4" fill="none"/>')

# 11 쑥쑥이: 머리에 새싹 난 아이
CH["ssuk"] = dict(team="s", **sk("light"), head="kid", hairc="#6b4a2a", brows="up", broww=3.6, nose="button", mouth="gap",
  eyes={"lr": 9.5, "rr": 8},
  outfit={"color": "#5cb85c", "collar": "hood", "collarc": "#7fd07f"},
  over_body='<path d="M52 104 V118 M68 104 V118" stroke="#f4f4f4" stroke-width="2"/>',
  face_extra="".join(f'<circle cx="{x}" cy="{y}" r=".9" fill="#b86b45" opacity=".7"/>' for x, y in [(40,64),(43,67),(46,64),(78,62),(81,65),(84,62)]),
  hair=f'<path d="M31 54 Q28 26 56 20 Q84 16 92 40 Q93 46 92 52 Q86 34 74 32 L66 38 L60 30 L52 38 L46 32 Q38 40 36 56 Z" fill="#6b4a2a" stroke="{O}" stroke-width="2"/>'
       + strands(["M44 26 Q60 18 80 24"], "#a67a4a", 1.8, .9),
  front=f'<path d="M62 22 Q60 12 62 4" stroke="#3a8a3a" stroke-width="3" fill="none"/>'
        f'<path d="M62 8 Q48 0 44 10 Q54 14 62 8 Z" fill="#7fd07f" stroke="#2f6b2f" stroke-width="1.6"/><path d="M62 6 Q74 -4 82 4 Q72 12 62 6 Z" fill="#5cb85c" stroke="#2f6b2f" stroke-width="1.6"/>')

# 12 반전이: 흑백 반반 머리 장난꾸러기
CH["banjeon"] = dict(team="s", **sk("tan"), hairc="#1d1d22", browc="#1d1d22", brows="up", broww=4.6, nose="bulb", mouth="tongue",
  eyes={"lr": 8.8, "rr": 7, "r": "wink"},
  outfit={"color": "#1f2a33", "stripes": "#f4ecd6", "collar": "none"},
  hair=f'<path d="M32 50 L28 34 L38 36 L38 20 L50 26 L58 10 L62 28 Z" fill="#1d1d22" stroke="{O}" stroke-width="2" stroke-linejoin="round"/>'
       f'<path d="M62 28 L66 10 L74 24 L86 14 L86 28 L98 28 L90 40 L94 48 Q88 34 76 30 Z" fill="#f4f4f4" stroke="{O}" stroke-width="2" stroke-linejoin="round"/>'
       f'<path d="M38 46 Q44 32 62 28 L62 30 Q46 34 40 48 Z" fill="#1d1d22"/>'
       + strands(["M70 18 L72 28", "M82 22 L80 30"], "#b9b9c4", 1.4, .9))

# 13 나침반: 흰 수염 선장, 나침반 목걸이
CH["nachim"] = dict(team="s", **sk("deep"), hairc="#f2f2f2", browc="#f7f7f7", brows="bushy", broww=5.6, nose="bulb", nosec="#d9765a", mouth="grin", mouth_over=True,
  eyes={"lr": 7.8, "rr": 6.4, "lid": True},
  outfit={"color": "#1f3f73", "collar": "shirt", "collarc": "#28508f"},
  beard=f'<path d="M36 62 Q34 90 52 98 Q62 104 72 98 Q90 90 90 60 Q84 74 74 72 Q62 80 50 72 Q40 72 36 62 Z" fill="#f2f2f2" stroke="#9a9a9a" stroke-width="1.6"/>'
        + strands(["M44 80 Q48 88 54 92", "M80 80 Q76 88 70 92", "M62 86 V96"], "#b9b9b9", 1.4, .9),
  over_body=f'<path d="M60 92 L58 104" stroke="#d4b25c" stroke-width="1.6"/><circle cx="58" cy="110" r="7.5" fill="#f4ecd6" stroke="#8a6414" stroke-width="2.4"/><path d="M58 104 L60 110 L58 116 L56 110 Z" fill="#c0392b"/>'
            f'<circle cx="40" cy="112" r="2.2" fill="#d4b25c"/><circle cx="80" cy="112" r="2.2" fill="#d4b25c"/>',
  front=f'<path d="M28 42 Q30 22 62 20 Q94 22 96 40 Q62 34 28 42 Z" fill="#f7f7f7" stroke="{O}" stroke-width="2.2"/>'
        f'<path d="M30 42 Q62 34 96 40 L96 46 Q62 40 30 48 Z" fill="#1d2433" stroke="{O}" stroke-width="2"/>'
        f'<path d="M26 48 Q62 40 98 46 Q96 52 90 52 Q62 46 32 54 Z" fill="#111" stroke="{O}" stroke-width="1.8"/>'
        f'<circle cx="62" cy="34" r="5" fill="#d4b25c" stroke="{O}" stroke-width="1.4"/><path d="M62 31 V37 M59.5 33.5 H64.5" stroke="#5a4210" stroke-width="1.4"/>')

# 14 순풍: 바람에 머리가 날리는 선원
CH["sunpung"] = dict(team="s", **sk("light"), hairc="#b5502a", brows="up", broww=3.6, nose="button", mouth="laugh",
  eyes={"lr": 8.6, "rr": 7.2, "iris": "#2a5a8a"},
  outfit={"color": "#f4f4f4", "collar": "sailor"},
  hair_back=f'<path d="M86 30 Q104 26 118 34 Q106 36 112 44 Q100 42 104 52 Q94 46 90 50 Z" fill="#b5502a" stroke="{O}" stroke-width="2"/>',
  face_extra=f'<path d="M42 47 L40 44 M45 46 L44 43" stroke="{O}" stroke-width="1.4"/>',
  hair=f'<path d="M33 54 Q28 24 56 18 Q80 14 92 30 L104 32 L92 38 Q92 44 90 48 Q82 34 70 32 Q56 34 50 40 Q42 44 40 56 Z" fill="#b5502a" stroke="{O}" stroke-width="2"/>'
       + strands(["M46 24 Q64 18 86 26", "M90 32 L102 33"], "#e08a5a", 1.8, .9),
  front=f'<g transform="rotate(12 70 18)"><path d="M50 22 Q50 8 70 8 Q90 8 90 22 Z" fill="#fff" stroke="{O}" stroke-width="2"/><rect x="48" y="20" width="44" height="5" rx="2" fill="#1f3f73" stroke="{O}" stroke-width="1.4"/></g>'
        f'<path d="M6 40 Q16 36 24 40 M4 52 Q14 48 22 52 M8 64 Q16 60 22 64" stroke="#fff" stroke-width="2.2" fill="none" stroke-linecap="round" opacity=".85"/>')

ORDER = ["ttukshim", "balgul", "keun", "mirae", "ppittak", "pado", "gyesan", "dandan", "alzza", "dotbogi", "ssuk", "banjeon", "nachim", "sunpung"]
NAMES = {"ttukshim": "뚝심이", "balgul": "발굴왕", "keun": "큰그림", "mirae": "미래광", "ppittak": "삐딱이", "pado": "파도타기", "gyesan": "계산기",
         "dandan": "단단이", "alzza": "알짜", "dotbogi": "돋보기", "ssuk": "쑥쑥이", "banjeon": "반전이", "nachim": "나침반", "sunpung": "순풍"}
# 자동 추가 캐릭터(tools/add_character.py): 정해진 선택지로만 만든 단순 캐릭터. 사람 얼굴을 본뜨지 않는다
HAIR = {"none": "", "short": 'M33 54 Q28 22 62 18 Q96 22 92 52 Q86 34 62 32 Q40 34 33 54 Z',
        "long": 'M30 70 Q24 22 62 16 Q100 22 94 70 Q92 46 86 38 Q62 30 38 38 Q32 46 30 70 Z',
        "curly": 'M32 52 Q26 40 34 32 Q36 20 50 20 Q58 12 70 18 Q84 14 90 26 Q100 34 92 50 Q86 36 62 34 Q42 36 32 52 Z'}
HAT = {"none": "", "cap": '<path d="M34 36 Q36 14 62 14 Q88 14 90 34 Q62 28 34 36 Z" fill="{c}" stroke="#1d1d22" stroke-width="2"/><path d="M84 32 Q102 32 108 38 Q96 40 86 38 Z" fill="{c}" stroke="#1d1d22" stroke-width="2"/>',
       "beanie": '<path d="M32 40 Q32 12 62 12 Q92 12 92 40 Z" fill="{c}" stroke="#1d1d22" stroke-width="2"/><rect x="30" y="36" width="64" height="8" rx="3" fill="{c}" stroke="#1d1d22" stroke-width="1.8"/><circle cx="62" cy="10" r="5" fill="{c}" stroke="#1d1d22" stroke-width="1.6"/>'}
_extra = pathlib.Path(__file__).parent / "extra.json"
for e in (__import__("json").loads(_extra.read_text()) if _extra.exists() else []):
    hp = HAIR[e.get("hair", "short")]
    CH[e["name"]] = dict(team=e["team"], **sk(e["skin"]), hairc=e["hairc"], brows=e.get("brows", "up"), nose=e.get("nose", "button"),
                         mouth=e.get("mouth", "grin"), glasses=e.get("glasses"), glassc="#1d1d22",
                         eyes={"lr": 8.2, "rr": 7, "iris": e.get("iris", "#3a2a20")},
                         outfit={"color": e["outfit"], "collar": e.get("collar", "shirt")},
                         hair=(f'<path d="{hp}" fill="{e["hairc"]}" stroke="{O}" stroke-width="2"/>' if hp else ""),
                         front=HAT[e.get("hat", "none")].replace("{c}", e.get("hatc", "#c0392b")))
    ORDER.append(e["name"]); NAMES[e["name"]] = e["nickname"]
COMMON = ('<radialGradient id="av-bgC" cx="35%" cy="25%" r="80%"><stop offset="0" stop-color="#f4c09a"/><stop offset=".55" stop-color="#d9784c"/><stop offset="1" stop-color="#7e3018"/></radialGradient>'
          '<radialGradient id="av-bgS" cx="35%" cy="25%" r="80%"><stop offset="0" stop-color="#bcd6f4"/><stop offset=".55" stop-color="#5a8fd6"/><stop offset="1" stop-color="#1b3a6e"/></radialGradient>'
          '<clipPath id="av-disc"><circle cx="60" cy="60" r="57"/></clipPath>')
defs = COMMON + "".join(char(k, CH[k]) for k in ORDER)
open('defs.svg', 'w').write(defs)
cells = "".join(f'<div class="c"><svg width="200" height="200" viewBox="0 0 120 120"><use href="#av-{k}"/></svg><b>{NAMES[k]}</b></div>' for k in ORDER)
small = "".join(f'<span class="card"><svg width="40" height="40" viewBox="0 0 120 120"><use href="#av-{k}"/></svg>{NAMES[k]}</span>' for k in ORDER)
open('preview.html', 'w').write(f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>
body{{margin:0;background:#16294a;font-family:system-ui,"Noto Sans KR",sans-serif;color:#f4ecd6}}
.row{{display:grid;grid-template-columns:repeat(7,1fr);gap:14px;padding:20px 24px}} .c{{text-align:center}} .c b{{display:block;font-size:16px;margin-top:4px}}
.small{{display:flex;flex-wrap:wrap;gap:10px;padding:0 24px 20px}} .card{{background:#fff;color:#1f1a14;border-radius:10px;padding:6px 10px;display:flex;align-items:center;gap:6px;font-size:16px}}
</style></head><body><svg width="0" height="0" style="position:absolute"><defs>{defs}</defs></svg><div class="row">{cells}</div><div class="small">{small}</div></body></html>''')
print("ok", len(defs))
