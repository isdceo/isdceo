"""로로 팀 3D 느낌 게임 화면 시안을 만든다.

  python3 league/play-candidates/roro/build.py <출력 폴더>

- src.html 에 2D 캐릭터 정의(운영자 현황판의 SVG defs)를 넣어 index.html 을 만들고,
  3D 캐릭터 그림(av/)과 공유 결과 묶음(data/table.js, 마감 지난 종목·점수만)을 함께 둔다.
"""
import json, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import dashboard_data as D  # noqa: E402

def main(out: str):
    out = Path(out); (out / "data").mkdir(parents=True, exist_ok=True)
    page = (ROOT / "docs/dashboard/operator-dashboard-page.html").read_text()
    a = page.index('<svg width="0" height="0"'); b = page.index("</defs></svg>", a) + len("</defs></svg>")
    (out / "index.html").write_text((HERE / "src.html").read_text().replace("{{DEFS}}", page[a:b]))
    shutil.copytree(HERE / "av", out / "av", dirs_exist_ok=True)
    js = "window.TABLE = " + json.dumps(D.bundle(), ensure_ascii=False) + ";\n"
    (out / "data/table.js").write_text(js)
    print("시안:", out / "index.html")

if __name__ == "__main__":
    main(sys.argv[1])
