import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def get_links_from_url(url):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = set()
        for a_tag in soup.find_all('a', href=True):
            full_url = urljoin(url, a_tag['href'])
            parsed = urlparse(full_url)
            if parsed.scheme in ['http', 'https']:
                links.add(full_url)
        return links
    except Exception as e:
        print(f"Failed to retrieve links from {url}: {e}")
        return set()

def check_link(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }

    try:
        # 1. Try HEAD request first (fast)
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=5, verify=False)
        status = response.status_code

        if status >= 400:
            # 2. Fallback to GET request if HEAD failed
            response = requests.get(url, headers=headers, allow_redirects=True, timeout=5, verify=False)
            status = response.status_code

        # 3. Analyze final status code
        if status == 999:
            print(f"🚫 Blocked by site (LinkedIn): {url} [{status}]")
            return None
        elif status in [403, 401]:
            print(f"🚫 Blocked or requires auth: {url} [{status}]")
            return None
        elif status >= 400:
            print(f"❌ Broken: {url} [{status}]")
            return False
        else:
            print(f"✅ OK: {url} [{status}]")
            return True

    except requests.RequestException as e:
        print(f"❌ Error: {url} [Exception: {e}]")
        return False

# Example usage:
start_url = 'https://www.ewubd.edu/'
links = get_links_from_url(start_url)
for link in links:
    check_link(link)
