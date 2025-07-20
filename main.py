

from fastapi import FastAPI, Request, Query, Header
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from google_auth_oauthlib.flow import Flow
import os
from dotenv import load_dotenv
import urllib.parse
from typing import List
import pathlib
import requests
from agent import generate_seo_advice

app = FastAPI()

@app.get("/seo/ai-advice")
def seo_ai_advice(
    site: str,
    request: Request,
    authorization: str = Header(default=None),
):
    # 1. Get user token
    token = request.session.get("token")
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1]
    if not token:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    # 2. Fetch GSC data (summary)
    gsc_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    encoded_site = urllib.parse.quote(site.rstrip("/"), safe="")
    gsc_url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded_site}/searchAnalytics/query"
    gsc_payload = {
        "startDate": "2024-06-01",
        "endDate": "2024-06-30",
        "dimensions": ["query"],
        "rowLimit": 5,
    }
    gsc_response = requests.post(gsc_url, headers=gsc_headers, json=gsc_payload)
    if gsc_response.status_code != 200:
        return JSONResponse({"error": "Failed to fetch GSC data"}, status_code=500)
    gsc_data = gsc_response.json()

    # 3. Fetch GA4 data summary similarly (example with sessions & users)
    ga4_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    ga4_property_id = "properties/123456789"  # Get this from your GA4 account list or param
    ga4_url = f"https://analyticsdata.googleapis.com/v1beta/{ga4_property_id}:runReport"
    ga4_payload = {
        "dateRanges": [{"startDate": "2024-06-01", "endDate": "2024-06-30"}],
        "metrics": [{"name": "sessions"}, {"name": "users"}],
        "dimensions": [{"name": "date"}],
    }
    ga4_response = requests.post(ga4_url, headers=ga4_headers, json=ga4_payload)
    if ga4_response.status_code != 200:
        return JSONResponse({"error": "Failed to fetch GA4 data"}, status_code=500)
    ga4_data = ga4_response.json()

    # 4. Generate SEO advice via OpenAI
    advice = generate_seo_advice(gsc_summary=gsc_data, ga4_summary=ga4_data)

    # 5. Return advice
    return {"seo_advice": advice}
