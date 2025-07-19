# sitemap_hunter.py
import re, itertools, xml.etree.ElementTree as ET
from urllib.parse import urlparse, unquote
import aiohttp
import asyncio
from typing import List

COMMON_CANDIDATES = [
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap",
    "/sitemap1.xml",
    "/sitemap-index.xml",
]

HEADERS = {"User-Agent": "SEO-Agent/0.1 (+https://github.com/noshinai/seo-agent)"}


async def normalize_root(session: aiohttp.ClientSession, url: str) -> str:
    url = url if "://" in url else f"https://{url}"
    try:
        async with session.get(url, headers=HEADERS, timeout=10, allow_redirects=True) as r:
            parsed = urlparse(str(r.url))
            return f"{parsed.scheme}://{parsed.netloc}"
    except:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"


async def get(session: aiohttp.ClientSession, url: str) -> aiohttp.ClientResponse | None:
    try:
        async with session.get(url, headers=HEADERS, timeout=10, allow_redirects=True) as resp:
            if resp.status == 200:
                return await resp.text()
            else:
                print(f"⚠️ Failed ({resp.status}): {url}")
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
    return None


def is_xml(text: str) -> bool:
    try:
        ET.fromstring(text.strip()[:10_000])
        return True
    except ET.ParseError:
        return False


async def try_common(session: aiohttp.ClientSession, root: str) -> List[str]:
    hits = []
    for path in COMMON_CANDIDATES:
        full = root + path
        print(f"🌐 Trying: {full}")
        text = await get(session, full)
        if text and is_xml(text):
            print(f"✅ Valid sitemap found: {full}")
            hits.append(full)
    return hits


async def parse_robots(session: aiohttp.ClientSession, root: str) -> List[str]:
    robots_url = root + "/robots.txt"
    print(f"📄 Fetching robots.txt: {robots_url}")
    text = await get(session, robots_url)
    if not text:
        print("⚠️ No robots.txt found.")
        return []

    sitemaps = []
    for line in text.splitlines():
        if line.lower().startswith("sitemap:"):
            sm_url = line.split(":", 1)[1].strip()
            print(f"🔗 Found in robots.txt: {sm_url}")
            sm_text = await get(session, sm_url)
            if sm_text and is_xml(sm_text):
                print(f"✅ Valid sitemap from robots.txt: {sm_url}")
                sitemaps.append(sm_url)
            else:
                print(f"❌ Invalid or unreachable sitemap: {sm_url}")
    return sitemaps


async def google_search(session: aiohttp.ClientSession, domain: str, max_hits: int = 10) -> List[str]:
    import bs4

    query = f"site:{domain} inurl:sitemap"
    params = {"q": query, "num": max_hits}
    try:
        async with session.get("https://www.google.com/search", params=params, headers=HEADERS, timeout=10) as resp:
            html = await resp.text()
    except Exception as e:
        print(f"❌ Google search failed: {e}")
        return []

    soup = bs4.BeautifulSoup(html, "html.parser")
    urls = []
    for a in soup.select("a"):
        href = a.get("href", "")
        m = re.match(r"/url\?q=(https?[^&]+)", href)
        if m:
            actual = unquote(m.group(1))
            if domain in actual and "sitemap" in actual:
                urls.append(actual)

    clean = []
    for u in itertools.islice(urls, max_hits):
        print(f"🔍 Checking search hit: {u}")
        sm_text = await get(session, u)
        if sm_text and is_xml(sm_text):
            print(f"✅ Valid sitemap from search: {u}")
            clean.append(u)
    return clean


async def hunt(domain_or_url: str) -> List[str]:
    async with aiohttp.ClientSession() as session:
        root = await normalize_root(session, domain_or_url)
        print(f"🔍 Hunting sitemaps for: {domain_or_url}")
        print(f"🔗 Canonical domain resolved: {root}")

        robots_hits = await parse_robots(session, root)
        common_hits = await try_common(session, root)
        search_hits = await google_search(session, urlparse(root).netloc)

        # Deduplicate results
        seen = set()
        for lst in (robots_hits, common_hits, search_hits):
            for url in lst:
                seen.add(url)

        return list(seen)
