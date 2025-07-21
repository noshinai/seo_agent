
from openai import OpenAI

client = OpenAI()  # Uses env variable OPENAI_API_KEY

def ask_ai_for_seo_feedback(seo_data: dict) -> str:
    prompt = (
        "You are an expert SEO analyst. Please review the SEO metadata of the following webpages.\n"
        "For each URL, provide:\n"
        "- A brief SEO analysis\n"
        "- Suggested improvements for the title, meta description, or H1 if only missing or suboptimal.\n"
        "- Recommended keywords to target\n"
        "- Alternative H1 tags if relevant\n"
        "- Any missing SEO elements (e.g., title too long, missing H1, weak keywords)\n\n"
    )

    for url, data in seo_data.items():
        if not isinstance(data, dict):
            continue  # Skip if it's not a dictionary (e.g., an error string or None)

    for url, data in seo_data.items():
        prompt += f"URL: {url}\n"
        prompt += f"Title: {data['title']}\n"
        prompt += f"Description: {data['description']}\n"
        prompt += f"H1: {data['h1']}\n"
        prompt += "-" * 40 + "\n"

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert SEO analyst."},
            {"role": "user", "content": prompt}
        ]
    )

    feedback = response.choices[0].message.content
    return feedback



# def generate_seo_advice(gsc_summary: dict, ga4_summary: dict) -> str:
#     prompt = f"""
#     You are an expert SEO consultant. Analyze the following SEO and traffic data, and provide actionable insights and recommendations:

#     Google Search Console data summary:
#     {gsc_summary}

#     Google Analytics data summary:
#     {ga4_summary}

#     Please suggest improvements, content ideas, and alert on any SEO issues.
#     """

#     response = openai.ChatCompletion.create(
#         model="gpt-4o-mini",  # or "gpt-4" if you have access
#         messages=[
#             {"role": "system", "content": "You are a helpful SEO assistant."},
#             {"role": "user", "content": prompt},
#         ],
#         max_tokens=500,
#         temperature=0.7,
#     )

#     advice = response.choices[0].message.content.strip()
#     return advice
