"""
Firebase Admin SDK configuration
"""
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
import os

# Initialize Firebase Admin SDK
# We'll use environment variables for production, but for now use service account
# or default credentials
try:
    # Try to get existing app
    app = firebase_admin.get_app()
except ValueError:
    # App doesn't exist, initialize it
    try:
        # Option 1: If you have a service account key file
        cred_path = os.path.join(os.path.dirname(__file__), '..', 'firebase-service-account-key.json')
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Firebase Admin initialized with service account key")
        else:
            # Option 2: Use default credentials (for cloud deployment or local emulator)
            # For development, we'll skip Firebase Admin verification
            # and just use Django's authentication
            print("Firebase Admin not configured - using Django authentication")
            pass
    except Exception as e:
        print(f"Firebase Admin initialization failed: {e}")
        print("Continuing without Firebase Admin - Django auth will be used")

def verify_firebase_token(id_token):
    """
    Verify a Firebase ID token
    
    Returns:
        dict: Decoded token if valid, None if invalid
    """
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        print(f"Firebase token verification failed: {e}")
        return None

