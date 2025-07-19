# server.py
import sys
import asyncio
import aiohttp
from sitemap_hunter import hunt
from broken_link import check_link
from sitemap_parser import extract_links_from_sitemap


async def main(domain_or_url):
    sitemap_urls = await hunt(domain_or_url)
    if not sitemap_urls:
        print("\n❌ No sitemaps found.")
        return

    print("\n🎯 Checking all links from sitemaps...")
    all_links = []
    for sitemap_url in sitemap_urls:
        urls = await extract_links_from_sitemap(sitemap_url)
        all_links.extend(urls)

    if not all_links:
        print("❌ No links found in sitemaps.")
        return

    async with aiohttp.ClientSession() as session:
        tasks = [check_link(session, url) for url in all_links]
        results = await asyncio.gather(*tasks)

    # Filter broken links based on False result
    broken_links = [url for url, result in zip(all_links, results) if result is False]

    print("\n🧾 Summary:")
    print(f"✅ Total links checked: {len(all_links)}")
    print(f"❌ Broken links found: {len(broken_links)}")
    for b in broken_links:
        print("  -", b)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python server.py <domain_or_url>")
        sys.exit(1)

    domain = sys.argv[1]
    asyncio.run(main(domain))

# python server.py https://www.nytimes.com

# python server.py factiiv.io