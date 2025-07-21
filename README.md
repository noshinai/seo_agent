# seo_agent

This AGENT has a timeout of 10 seconds between each request. If the URL does not return a response within 10 seconds, it will error out and show that the operation was timed out.

*Head requests*
To save on bytes, walker performs HEAD requests instead of GET requests. However, some websites might deny responding to this method, which could lead to false negatives. For each failed HEAD request(status >= 400), it fallbacks to GET request.


project/
├── server.py              # Entry point
├── sitemap_hunter.py      # Finds sitemap.xml
├── sitemap_parser.py      # Extracts URLs from sitemap
├── broken_link.py         # Checks for broken links
├── seo_audit.py           # SEO audit logic
├── openai_agent.py        # OpenAI-powered insights
