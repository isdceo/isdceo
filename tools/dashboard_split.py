"""운영 현황판 페이지 사본(docs/dashboard/operator-dashboard-page.html, 한 파일)을 현황판에 올릴 세 파일로 나눈다.
현황판 문서 하나는 256KB까지라 HTML(캐릭터 그림 포함)·스타일·스크립트를 따로 올린다.

  python3 tools/dashboard_split.py --out <폴더>   → <폴더>/index.html, style.css, app.js
"""
from __future__ import annotations

import argparse
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "docs" / "dashboard" / "operator-dashboard-page.html"
LIMIT = 256 * 1024


def split(text: str) -> dict[str, str]:
    head = '<meta name="dash-one-writer">\n'
    assert text.startswith(head), "첫 줄은 <meta name=\"dash-one-writer\">"
    a, b = text.index("<style>\n"), text.index("</style>\n")
    css = text[a + len("<style>\n"):b]
    rest = text[b + len("</style>\n"):]
    i, j = rest.index("\n<script>\n"), rest.rindex("</script>")
    assert not rest[j + len("</script>"):].strip(), "</script> 뒤에 내용이 있음"
    js = rest[i + len("\n<script>\n"):j]
    # 외부 글꼴 <link>는 현황판이 버리므로 옮기지 않는다
    html = head + '<link rel="stylesheet" href="style.css">\n' + rest[:i + 1] + '<script src="app.js"></script>\n'
    return {"index.html": html, "style.css": css, "app.js": js}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=str(SRC))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for name, body in split(Path(a.src).read_text()).items():
        (out / name).write_text(body)
        n = len(body.encode())
        print(f"{name}: {n:,} B ({n / LIMIT:.0%} of 256KB)")
        if n > LIMIT:
            raise SystemExit(f"{name} 가 256KB를 넘음")


if __name__ == "__main__":
    main()
