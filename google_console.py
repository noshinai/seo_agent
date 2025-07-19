from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from google_auth_oauthlib.flow import Flow
import os
from dotenv import load_dotenv

import pathlib
import requests

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
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
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


from fastapi import Header
from datetime import datetime, timedelta
import logging
import urllib.parse

@app.get("/gsc/performance")
def get_gsc_performance(site: str, request: Request, authorization: str = Header(default=None)):
    token = request.session.get("token")
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1]

    if not token:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=30)

    payload = {
        "startDate": str(start_date),
        "endDate": str(end_date),
        "dimensions": ["query"],
        "rowLimit": 20
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

# from datetime import datetime, timedelta

# @app.get("/gsc/performance")
# def get_gsc_performance(site: str, request: Request):
#     token = request.session.get("token")
#     if not token:
#         return JSONResponse({"error": "Not authenticated"}, status_code=401)

#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json",
#     }

#     end_date = datetime.utcnow().date()
#     start_date = end_date - timedelta(days=30)

#     payload = {
#         "startDate": str(start_date),
#         "endDate": str(end_date),
#         "dimensions": ["query"],
#         "rowLimit": 20
#     }

#     url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"
#     response = requests.post(url, headers=headers, json=payload)

#     if response.status_code == 200:
#         return response.json()
#     else:
#         return JSONResponse({"error": "Failed to fetch performance data", "details": response.json()}, status_code=500)


# @app.get("/oauth2callback")
# def callback(request: Request):
#     state = request.session.get("state")
#     flow = Flow.from_client_config(
#         {
#             "web": {
#                 "client_id": CLIENT_ID,
#                 "client_secret": CLIENT_SECRET,
#                 "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#                 "token_uri": "https://oauth2.googleapis.com/token",
#             }
#         },
#         scopes=SCOPES,
#         state=state,
#         redirect_uri=REDIRECT_URI
#     )

#     flow.fetch_token(authorization_response=str(request.url))
#     credentials = flow.credentials

#     access_token = credentials.token
#     # request.session["token"] = access_token
#     return {"message": "Authentication successful. Token stored.", "token": access_token}

# @app.get("/gsc/sites")
# def list_sites(request: Request):
#     token = request.session.get("token")
#     if not token:
#         return {"error": "Not authenticated"}

#     headers = {"Authorization": f"Bearer {token}"}
#     res = requests.get("https://searchconsole.googleapis.com/webmasters/v3/sites", headers=headers)
#     return res.json()
