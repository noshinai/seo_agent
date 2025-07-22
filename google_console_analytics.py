from fastapi import FastAPI, Request, Query, Header
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from google_auth_oauthlib.flow import Flow
import os
from dotenv import load_dotenv

from typing import List
import pathlib
from datetime import datetime, timedelta
import logging
import requests
import urllib.parse
from typing import List, Optional

app = FastAPI()
load_dotenv()
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")

# remove in production
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# OAuth2 credentials from Google Cloud Console
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("CLIENT_ID and CLIENT_SECRET must be set in environment variables.")
SCOPES = [
    "https://www.googleapis.com/auth/webmasters",
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly"
]
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/oauth2callback")

@app.get("/oauth/login")
def login(request: Request):
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    request.session["state"] = state
    return RedirectResponse(url=authorization_url)


# --- Step 2: Handle callback, fetch token, then fetch GSC site list ---
@app.get("/oauth2callback")
def oauth_callback(request: Request):
    state = request.session.get("state")
    if not state:
        return JSONResponse({"error": "Missing session state"}, status_code=400)

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI,
    )

    # Fetch token from Google's redirect response
    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials

    # Store token in session
    request.session["token"] = credentials.token

    # Fetch list of GSC sites immediately
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Accept": "application/json",
    }
    response = requests.get("https://searchconsole.googleapis.com/webmasters/v3/sites", headers=headers)

    if response.status_code == 200:
        data = response.json()
        data["token"] = credentials.token
        return JSONResponse(data)
    else:
        return JSONResponse({"error": "Failed to fetch GSC data", "details": response.json()}, status_code=500)




@app.get("/gsc/performance")
def get_gsc_performance(
    site: str, 
    request: Request,
    authorization: str = Header(default=None),
    start_date: str = Query(default=None),
    end_date: str = Query(default=None),
    dimensions: Optional[List[str]] = Query(default=["query"]),
    row_limit: Optional[int] = Query(default=20)):

    if not site:
        return JSONResponse({"error": "Site parameter is required"}, status_code=400)

    token = request.session.get("token")
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1]

    if not token:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Parse and validate dates
    try:
        if not end_date:
            end_date = datetime.utcnow().date()
        else:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        if not start_date:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        return JSONResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status_code=400)

    if start_date > end_date:
        return JSONResponse({"error": "Start date cannot be after end date."}, status_code=400)
    
    # Validate dimensions
    allowed_dimensions = {"query", "page", "device", "country", "date"}
    invalid_dimensions = [d for d in dimensions if d not in allowed_dimensions]
    if invalid_dimensions:
        return JSONResponse({"error": f"Invalid dimensions: {invalid_dimensions}"}, status_code=400)

    payload = {
        "startDate": str(start_date),
        "endDate": str(end_date),
        "dimensions": dimensions,
        "rowLimit": row_limit
    }

    site = site.rstrip("/")
    encoded_site = urllib.parse.quote(site, safe='')

    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded_site}/searchAnalytics/query"

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # raises an exception for 4xx/5xx
        return response.json()

    except requests.exceptions.HTTPError as http_err:
        try:
            error_data = response.json()
        except Exception:
            error_data = response.text
        logging.error(f"HTTP error: {http_err} | Response: {error_data}")
        return JSONResponse({
            "error": "Failed to fetch performance data",
            "status_code_from_google": response.status_code,
            "details": error_data
        }, status_code=500)

    except Exception as e:
        logging.exception("Unexpected error occurred.")
        return JSONResponse({
            "error": "Unexpected server error",
            "message": str(e)
        }, status_code=500)


@app.get("/ga4/properties")
def list_ga4_properties(request: Request, authorization: str = Header(default=None)):
    token = request.session.get("token")
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1]

    if not token:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get("https://analyticsadmin.googleapis.com/v1beta/accountSummaries", headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return JSONResponse({"error": "Failed to fetch GA accounts", "details": response.json()}, status_code=500)



def parse_date_param(date_str: str):
    try:
        if date_str.lower() == "today":
            return datetime.utcnow().strftime("%Y-%m-%d")
        elif date_str.lower().endswith("daysago"):
            days = int(date_str.lower().replace("daysago", ""))
            return (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        else:
            datetime.strptime(date_str, "%Y-%m-%d")  # validate format
            return date_str
    except Exception:
        raise ValueError("Date must be 'YYYY-MM-DD', 'today' or '<n>daysAgo'")
    

@app.get("/ga4/report")
def get_ga4_report(
    request: Request,
    property_id: str = Query(...),  # GA4 property ID
    start_date: str = Query(default="30daysAgo"),
    end_date: str = Query(default="today"),
    metrics: List[str] = Query(default=["sessions"]),
    dimensions: List[str] = Query(default=["date"]),
    authorization: str = Header(default=None)
):
    try:
        start_date = parse_date_param(start_date)
        end_date = parse_date_param(end_date)
    except ValueError as ve:
        return JSONResponse({"error": str(ve)}, status_code=400)
    

    token = request.session.get("token")
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1]

    if not token:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"

    payload = {
        "dateRanges": [{"startDate": start_date, "endDate": end_date}],
        "metrics": [{"name": m} for m in metrics],
        "dimensions": [{"name": d} for d in dimensions]
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()
    else:
        return JSONResponse({
            "error": "Failed to fetch GA4 report",
            "status_code_from_google": response.status_code,
            "details": response.json()
        }, status_code=500)
