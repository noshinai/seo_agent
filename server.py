# server.py
import sys
import asyncio
import aiohttp
from func import hunt, extract_links_from_sitemap, check_link, analyze_seo
# from broken_link import check_link
# from sitemap_parser import extract_links_from_sitemap
# from seo_audit import analyze_seo
from agent import ask_ai_for_seo_feedback


async def main(domain_or_url):
    sitemap_urls = await hunt(domain_or_url)
    if not sitemap_urls:
        print("\n❌ No sitemaps found.")
        return

    print("\n Checking all links from sitemaps...")
    all_links = []
    for sitemap_url in sitemap_urls:
        urls = await extract_links_from_sitemap(sitemap_url)
        all_links.extend(urls)

    if not all_links:
        print("❌ No links found in sitemaps.")
        return

    async with aiohttp.ClientSession() as session:
        broken_tasks = [check_link(session, url) for url in all_links]
        broken_results = await asyncio.gather(*broken_tasks)

    # Filter broken links based on False result
    broken_links = [url for url, result in zip(all_links, broken_results) if result is False]

    async with aiohttp.ClientSession() as session:
        print("\n📊 Analyzing SEO for pages...")
        seo_tasks = [analyze_seo(session, url) for url in all_links[:5]]
        seo_results = await asyncio.gather(*seo_tasks)

    print("\n🧾 Summary:")
    print(f"✅ Total links checked: {len(all_links)}")
    print(f"❌ Broken links found: {len(broken_links)}")
    for b in broken_links:
        print("  -", b)

    # # Combine all seo_results into a single dictionary
    # seo_data = {}
    # for result in seo_results:
    #     seo_data.update(result)

    # feedback = ask_ai_for_seo_feedback(seo_data)
    # print(f"Review:\n{feedback}")

    seo_data = {}
    for result in seo_results:
        # Ensure result is a dictionary before updating
        if isinstance(result, dict):
            for url, data in result.items():
                if isinstance(data, dict):
                    seo_data[url] = data  # Accept only valid dicts
                else:
                    print(f"[Skipping invalid entry] {url}: {data}")
        else:
            print(f"[Skipping invalid result] {result}")

    # Call only if we have valid data
    if seo_data:
        feedback = ask_ai_for_seo_feedback(seo_data)
        print(f"Review:\n{feedback}")
    else:
        print("No valid SEO data to analyze.")



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python server.py <domain_or_url>")
        sys.exit(1)

    domain = sys.argv[1]
    asyncio.run(main(domain))

# python server.py https://www.nytimes.com

# python server.py factiiv.io