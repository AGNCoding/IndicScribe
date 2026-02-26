import os
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

# Initialize OAuth registry
oauth = OAuth()

# Setup Google OAuth
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile https://www.googleapis.com/auth/drive',
    },
    authorize_params={
        'access_type': 'offline',  # Request offline access for refresh tokens
        'prompt': 'consent',  # Always show consent screen to get refresh token
    }
)

