import asyncio
import aiohttp
import certifi
import ssl
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

ssl_context = ssl.create_default_context(cafile=certifi.where())

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

TIMEOUT = aiohttp.ClientTimeout(total=20)
MAX_CONCURRENT_CONNECTIONS = 10
RETRY_COUNT = 2


async def get_links_from_scrapping(session, url):
    try:
        async with session.get(url, ssl=ssl_context, headers=HEADERS) as resp:
            if resp.status != 200:
                print(f"Failed to load {url} [{resp.status}]")
                return set()
            html = await resp.text()
            soup = BeautifulSoup(html, 'html.parser')
            links = set()
            for a_tag in soup.find_all('a', href=True):
                full_url = urljoin(url, a_tag['href'])
                parsed = urlparse(full_url)
                if parsed.scheme in ['http', 'https']:
                    links.add(full_url)
            return links
    except Exception as e:
        print(f"Error retrieving links from {url}: {e}")
        return set()


async def check_link(session, url):
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


# async def broken_link_checker(start_url):
#     connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_CONNECTIONS)
#     async with aiohttp.ClientSession(timeout=TIMEOUT, connector=connector) as session:
#         links = await get_links_from_scrapping(session, start_url)
#         if not links:
#             print("No links found.")
#             return

#         tasks = [check_link(session, link) for link in links]
#         await asyncio.gather(*tasks)


# # Example usage
# if __name__ == "__main__":
#     start_url = "https://www.ewubd.edu/"
#     asyncio.run(broken_link_checker(start_url))
