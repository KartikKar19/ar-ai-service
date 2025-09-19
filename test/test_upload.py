import os
import requests
from dotenv import load_dotenv

# Load config from .env
load_dotenv()

AUTH0_URL = os.getenv("AUTH_SERVICE_URL")
CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUDIENCE = os.getenv("AUTH0_AUDIENCE")
UPLOAD_URL = "http://127.0.0.1:8002/v1/documents/upload"  # your local API endpoint

def get_token():
    """Get JWT token from Auth0"""
    token_url = f"{AUTH0_URL}/oauth/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "audience": AUDIENCE,
        "grant_type": "client_credentials"
    }
    response = requests.post(token_url, json=payload)
    print("Token request status:", response.status_code)
    print("Token request response:", response.text)
    response.raise_for_status()
    return response.json()["access_token"]

def upload_pdf(file_path):
    """Upload PDF to local API"""
    token = get_token()
    print("\n=== JWT Token ===")
    print(token, "\n")
    
    headers = {"Authorization": f"Bearer {token}"}
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "application/pdf")}
        response = requests.post(UPLOAD_URL, headers=headers, files=files)

    data = {
        "title": "Test PDF",
        "description": "Testing upload endpoint",
        "subject": "test",
        "tags": "test,debug"
    }
    response = requests.post(UPLOAD_URL, headers=headers, files=files, data=data)
    print("Upload Status Code:", response.status_code)
    try:
        print("Upload Response:", response.json())
    except Exception:
        print("Upload Response (raw):", response.text)

if __name__ == "__main__":
    upload_pdf("test/rayoptics.pdf")
