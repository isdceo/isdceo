"""종목 카드용 회사 로고 (운영자 전용 현황판에만 쓴다).

- 한국: 토스증권 종목 아이콘  https://static.toss.im/png-icons/securities/icn-sec-fill-<6자리>.png
- 미국: Financial Modeling Prep 종목 이미지  https://financialmodelingprep.com/image-stock/<티커>.png  (BRK.B → BRK-B)

로고는 각 회사의 상표다. 두 주소 모두 이용 조건을 따로 밝히지 않은 공개 이미지라, 운영자 본인 확인용
화면에서 종목 표시 목적으로만 쓴다. 지인 공개 전에는 다시 확인한다(docs/data-provider-research.md 9장).
받은 그림은 64px로 줄여 data: URL로 넘긴다(현황판은 외부 주소 그림을 직접 불러올 수 없다).
받지 못하면 None — 화면은 종목명 첫 글자 배지로 대신한다.
"""
import base64, io, os, urllib.request
from pathlib import Path

UA = "isdceo-league-dashboard/1.0"
CACHE = Path(os.environ.get("LOGO_CACHE", Path.home() / ".cache" / "isdceo-logos"))


def logo_url(market: str, ticker: str) -> str | None:
    if market == "KR" and ticker:
        return f"https://static.toss.im/png-icons/securities/icn-sec-fill-{ticker}.png"
    if market == "US" and ticker:
        return f"https://financialmodelingprep.com/image-stock/{ticker.replace('.', '-').upper()}.png"
    return None


def _shrink(raw: bytes, size: int = 64) -> bytes:
    try:
        from PIL import Image
    except ImportError:
        return raw
    try:
        im = Image.open(io.BytesIO(raw)).convert("RGBA")
        im.thumbnail((size, size))
        px = [p for p in im.getdata() if p[3] > 40]
        if px and sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b, _ in px) / len(px) > 225:
            # 흰색·밝은 로고는 흰 카드에서 안 보이므로 어두운 바탕에 얹는다
            bg = Image.new("RGBA", im.size, (38, 34, 30, 255))
            bg.alpha_composite(im)
            im = bg
        out = io.BytesIO()
        im.save(out, "PNG", optimize=True)
        return out.getvalue()
    except Exception:
        return raw


def fetch_logo(market: str, ticker: str, timeout: float = 10) -> str | None:
    """data:image/png;base64,... 또는 None. 같은 컨테이너 안에서는 캐시를 쓴다."""
    url = logo_url(market, ticker)
    if not url:
        return None
    cache = CACHE / f"{market}-{ticker.replace('/', '_')}.png"
    try:
        if cache.exists():
            raw = cache.read_bytes()
        else:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                if r.status != 200 or "image" not in (r.headers.get("Content-Type") or ""):
                    return None
                raw = _shrink(r.read())
            if len(raw) < 200 or len(raw) > 60_000:
                return None
            CACHE.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(raw)
        return "data:image/png;base64," + base64.b64encode(raw).decode()
    except Exception:
        return None
