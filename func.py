# sitemap_hunter.py
import re, itertools, xml.etree.ElementTree as ET
from urllib.parse import urlparse, unquote
import aiohttp
import asyncio
from typing import List
import certifi
import ssl
from bs4 import BeautifulSoup

ssl_context = ssl.create_default_context(cafile=certifi.where())
RETRY_COUNT = 2
HEADERS = {"User-Agent": "SEO-Agent/0.1 (+https://github.com/noshinai/seo-agent)"}

COMMON_CANDIDATES = [
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap",
    "/sitemap1.xml",
    "/sitemap-index.xml",
]

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

async def expand_sitemaps(session: aiohttp.ClientSession, sitemap_urls: List[str]) -> List[str]:
    """Recursively expand sitemap index files into concrete sitemap URLs."""
    final_sitemaps = []

    for sm_url in sitemap_urls:
        xml = await get(session, sm_url)
        if not xml:
            continue

        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            continue

        # Handle sitemap index (nested sitemaps)
        if root.tag.endswith("sitemapindex"):
            for sm in root.findall(".//{*}sitemap/{*}loc"):
                loc = sm.text.strip()
                print(f"🔁 Found nested sitemap: {loc}")
                nested = await expand_sitemaps(session, [loc])
                final_sitemaps.extend(nested)
        elif root.tag.endswith("urlset"):
            # Direct sitemap
            final_sitemaps.append(sm_url)

    return final_sitemaps



async def hunt(domain_or_url: str) -> List[str]:
    async with aiohttp.ClientSession() as session:
        root = await normalize_root(session, domain_or_url)
        print(f"🔍 Hunting sitemaps for: {domain_or_url}")
        print(f"🔗 Canonical domain resolved: {root}")

        robots_hits = await parse_robots(session, root)
        common_hits = await try_common(session, root)
        search_hits = await google_search(session, urlparse(root).netloc)

        # Deduplicate all discovered sitemaps
        initial_sitemaps = list(set(robots_hits + common_hits + search_hits))

        # 🧠 Recursively expand sitemap indexes into real sitemaps
        expanded_sitemaps = await expand_sitemaps(session, initial_sitemaps)

        # Deduplicate final list
        return list(set(expanded_sitemaps))



async def extract_links_from_sitemap(sitemap_url: str):
    """
    Downloads and parses a sitemap to extract <loc> URLs asynchronously.
    """
    print(f"\n Downloading sitemap: {sitemap_url}")
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(sitemap_url, timeout=10) as response:
                response_text = await response.text()
                response.raise_for_status()

        tree = ET.fromstring(response_text)

        # Handle sitemap namespaces
        namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        loc_elements = tree.findall(".//ns:loc", namespaces=namespace)

        urls = [el.text.strip() for el in loc_elements if el.text]
        print(f" Found {len(urls)} URLs in sitemap.")
        return urls
    except Exception as e:
        print(f" Failed to parse sitemap: {e}")
        return []



async def check_link(session, url):
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }

    for attempt in range(RETRY_COUNT):
        try:
            async with session.head(url, headers=HEADERS, allow_redirects=True, ssl=ssl_context) as resp:
                if resp.status == 999:
                    print(f"❌ Blocked by site (LinkedIn): {url} [{resp.status}]")
                    return None
                elif resp.status in [403, 401]:
                    print(f"❌ Blocked or requires auth: {url} [{resp.status}]")
                    return None
                elif resp.status == 400 and ("facebook.com" in url or "twitter.com" in url):
                    print(f"⚠️ Possibly OK but blocked or rate-limited: {url} [{resp.status}]")
                    return None
                elif resp.status >= 400:
                    print(f"❌ Broken: {url} [{resp.status}]")
                    return False
                else:
                    print(f"✅ OK: {url} [{resp.status}]")
                    return True
        except aiohttp.ClientResponseError as e:
            print(f"❌ Client error: {url} [{e.status}]")
            return False
        except asyncio.TimeoutError:
            print(f"⏳ Timeout: {url} [Attempt {attempt + 1}]")
        except Exception as e:
            print(f"❌ Error: {url} [Exception: {e}]")
            return False
    return False



async def fetch_html(session, url):
    try:
        async with session.get(url, timeout=50) as resp:
            if resp.status != 200:
                print(f"⚠️ Failed to fetch {url} (status: {resp.status})")
                return None

            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                print(f"⚠️ Skipping {url} (non-HTML content: {content_type})")
                return None

            return await resp.text()
    except asyncio.TimeoutError:
        print(f"⏱️ Timeout while fetching: {url}")
    except aiohttp.ClientError as e:
        print(f"❌ Client error while fetching {url}: {e}")
    except Exception as e:
        print(f"❗ Unexpected error fetching {url}: {e}")

    return None

async def analyze_seo(session, url):
    seo_data = {}
    html = await fetch_html(session, url)
    if not html:
        return {"url": url, "error": "Failed to fetch"}

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title else "No title"
    meta_desc = soup.find("meta", attrs={"name": "description"})
    description = meta_desc["content"].strip() if meta_desc and "content" in meta_desc.attrs else "Missing"
    h1 = soup.find("h1").text.strip() if soup.find("h1") else "Missing"

    seo_data[url] = {
            "title": title,
            "description": description,
            "h1": h1
        }
    return seo_data