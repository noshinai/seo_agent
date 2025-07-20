import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")


def generate_seo_advice(gsc_summary: dict, ga4_summary: dict) -> str:
    prompt = f"""
    You are an expert SEO consultant. Analyze the following SEO and traffic data, and provide actionable insights and recommendations:

    Google Search Console data summary:
    {gsc_summary}

    Google Analytics data summary:
    {ga4_summary}

    Please suggest improvements, content ideas, and alert on any SEO issues.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # or "gpt-4" if you have access
        messages=[
            {"role": "system", "content": "You are a helpful SEO assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=500,
        temperature=0.7,
    )

    advice = response.choices[0].message.content.strip()
    return advice
