import os, urllib.parse, httpx

WIKI_LANG = os.getenv("WIKI_LANG", "ru")

async def google_search(query: str) -> str:
    key = os.getenv("GOOGLE_CSE_KEY")
    cx = os.getenv("GOOGLE_CSE_CX")
    if not key or not cx:
        return "Google CSE не настроен."
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": key, "cx": cx, "q": query, "num": 3}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        items = r.json().get("items", [])
        if not items:
            return "Ничего не найдено (Google)."
        lines = ["🔎 *Google* результаты:"]
        for it in items[:3]:
            lines.append(f"- {it.get('title')}\n{it.get('link')}")
        return "\n".join(lines)

async def bing_search(query: str) -> str:
    key = os.getenv("BING_KEY")
    if not key:
        return "Bing не настроен."
    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": key}
    params = {"q": query, "count": 3, "textDecorations": False}
    async with httpx.AsyncClient(timeout=20, headers=headers) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        web_pages = (r.json() or {}).get("webPages", {}).get("value", [])
        if not web_pages:
            return "Ничего не найдено (Bing)."
        lines = ["🔎 *Bing* результаты:"]
        for it in web_pages[:3]:
            lines.append(f"- {it.get('name')}\n{it.get('url')}")
        return "\n".join(lines)

async def ddg_instant(query: str) -> str:
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json", "no_redirect": 1, "no_html": 1}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        answer = data.get("AbstractText") or data.get("Answer")
        source = data.get("AbstractURL")
        if answer:
            s = f"🕸️ *DDG*: {answer}"
            if source:
                s += f"\nИсточник: {source}"
            return s
        return ""

async def wiki_summary(query: str) -> str:
    title = urllib.parse.quote(query)
    url = f"https://{WIKI_LANG}.wikipedia.org/api/rest_v1/page/summary/{title}"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return "Не нашёл страницу в Википедии."
        jd = r.json()
        extract = jd.get("extract")
        page = jd.get("content_urls", {}).get("desktop", {}).get("page")
        if extract:
            base = f"📚 *Wikipedia*: {extract}"
            if page:
                base += f"\nСтраница: {page}"
            return base
        return "Нет краткого описания на Википедии."

async def web_search(query: str) -> str:
    # Try Google, then Bing, then DDG + Wiki
    g = await google_search(query)
    if not g.startswith("Google CSE не настроен.") and not g.startswith("Ничего не найдено (Google)."):
        return g
    b = await bing_search(query)
    if not b.startswith("Bing не настроен.") and not b.startswith("Ничего не найдено (Bing)."):
        return b
    d = await ddg_instant(query)
    if d:
        return d
    w = await wiki_summary(query)
    return w
