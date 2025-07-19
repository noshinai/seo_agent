import xml.etree.ElementTree as ET
import aiohttp
import asyncio

HEADERS = {"User-Agent": "SEO-Agent/0.1 (+https://github.com/noshinai/seo-agent)"}


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




# import xml.etree.ElementTree as ET
# import requests

# HEADERS = {"User-Agent": "SEO-Agent/0.1 (+https://github.com/noshinai/seo-agent)"}


# def extract_links_from_sitemap(sitemap_url):
#     """
#     Downloads and parses a sitemap to extract <loc> URLs.
#     """
#     print(f"\n Downloading sitemap: {sitemap_url}")
#     try:
#         response = requests.get(sitemap_url, headers=HEADERS, timeout=10)
#         response.raise_for_status()
#         tree = ET.fromstring(response.text)

#         # Handle sitemap namespaces
#         namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
#         loc_elements = tree.findall(".//ns:loc", namespaces=namespace)

#         urls = [el.text.strip() for el in loc_elements if el.text]
#         print(f" Found {len(urls)} URLs in sitemap.")
#         return urls
#     except Exception as e:
#         print(f" Failed to parse sitemap: {e}")
#         return []
