#!/usr/bin/env python3
import sys, re, itertools, xml.etree.ElementTree as ET
from urllib.parse import urlparse
import requests

COMMON_CANDIDATES = [
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap",
    "/sitemap1.xml",
    "/sitemap-index.xml",
]

HEADERS = {"User-Agent": "SEO-Agent/0.1 (+https://github.com/noshinai/seo-agent)"}


def normalize_root(url: str) -> str:
    """
    Follow redirects to normalize root domain.
    """
    url = url if "://" in url else f"https://{url}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        parsed = urlparse(r.url)
        return f"{parsed.scheme}://{parsed.netloc}"
    except requests.RequestException:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"


def get(url: str) -> requests.Response | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if resp.ok:
            return resp
        else:
            print(f"⚠️ Failed ({resp.status_code}): {url}")
    except requests.RequestException as e:
        print(f"❌ Error fetching {url}: {e}")
    return None


def is_xml(text: str) -> bool:
    try:
        ET.fromstring(text.strip()[:10_000])
        return True
    except ET.ParseError:
        return False


def try_common(root: str) -> list[str]:
    hits = []
    for path in COMMON_CANDIDATES:
        full = root + path
        print(f"🌐 Trying: {full}")
        if (r := get(full)) and is_xml(r.text):
            print(f"✅ Valid sitemap found: {full}")
            hits.append(full)
    return hits


def parse_robots(root: str) -> list[str]:
    robots_url = root + "/robots.txt"
    print(f"📄 Fetching robots.txt: {robots_url}")
    resp = get(robots_url)
    if not resp:
        print("⚠️ No robots.txt found.")
        return []

    sitemaps = []
    for line in resp.text.splitlines():
        if line.lower().startswith("sitemap:"):
            sm_url = line.split(":", 1)[1].strip()
            print(f"🔗 Found in robots.txt: {sm_url}")
            if sm_url and (r := get(sm_url)) and is_xml(r.text):
                print(f"✅ Valid sitemap from robots.txt: {sm_url}")
                sitemaps.append(sm_url)
            else:
                print(f"❌ Invalid or unreachable sitemap: {sm_url}")
    return sitemaps


def google_search(domain: str, max_hits: int = 10) -> list[str]:
    """
    Uses Google's public web interface with simple scraping.
    Replace with SerpAPI or Google CSE for production use.
    """
    import urllib.parse, bs4

    query = f"site:{domain} inurl:sitemap"
    params = {"q": query, "num": max_hits}
    try:
        html = requests.get("https://www.google.com/search", params=params, headers=HEADERS, timeout=10).text
    except requests.RequestException as e:
        print(f"❌ Google search failed: {e}")
        return []

    soup = bs4.BeautifulSoup(html, "html.parser")
    urls = []

    for a in soup.select("a"):
        href = a.get("href", "")
        m = re.match(r"/url\?q=(https?[^&]+)", href)
        if m:
            actual = urllib.parse.unquote(m.group(1))
            if domain in actual and "sitemap" in actual:
                urls.append(actual)

    clean = []
    for u in itertools.islice(urls, max_hits):
        print(f"🔍 Checking search hit: {u}")
        if (r := get(u)) and is_xml(r.text):
            print(f"✅ Valid sitemap from search: {u}")
            clean.append(u)
    return clean


def hunt(domain_or_url: str) -> list[str]:
    root = normalize_root(domain_or_url)
    print(f"🔍 Hunting sitemaps for: {domain_or_url}")
    print(f"🔗 Canonical domain resolved: {root}")

    results: list[str] = []

    robots_hits = parse_robots(root)
    common_hits = try_common(root)
    search_hits = google_search(urlparse(root).netloc)

    for lst in (robots_hits, common_hits, search_hits):
        for url in lst:
            if url not in results:
                results.append(url)
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: sitemap_hunter.py <domain_or_url>")
        sys.exit(1)

    domain = sys.argv[1]
    results = hunt(domain)

    if results:
        print("\n🎯 Discovered sitemap URLs:")
        for url in results:
            print("  ✓", url)
    else:
        print("\n❌ No sitemaps found.")
