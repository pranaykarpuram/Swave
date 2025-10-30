"""
Firebase Admin SDK configuration (env-based, no secrets in repo)
"""
import os
import json
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth


def _init_firebase_admin_if_available() -> bool:
    """Initialize Firebase Admin if env provides credentials. Returns True if initialized."""
    try:
        firebase_admin.get_app()
        return True
    except ValueError:
        pass

    # Preferred: GOOGLE_APPLICATION_CREDENTIALS points to a JSON file
    gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    # Alternative: FIREBASE_CREDENTIALS_JSON contains the JSON string
    creds_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")

    try:
        if gac and os.path.exists(gac):
            cred = credentials.Certificate(gac)
            firebase_admin.initialize_app(cred)
            return True
        if creds_json:
            data = json.loads(creds_json)
            cred = credentials.Certificate(data)
            firebase_admin.initialize_app(cred)
            return True
    except Exception:
        # Fail closed: if credentials are malformed, don't initialize
        return False

    # Not configured
    return False


FIREBASE_ADMIN_READY = _init_firebase_admin_if_available()


def verify_firebase_token(id_token: str):
    """Verify a Firebase ID token. Returns decoded dict if valid, else None."""
    if not FIREBASE_ADMIN_READY:
        return None
    try:
        return firebase_auth.verify_id_token(id_token)
    except Exception:
        return None

