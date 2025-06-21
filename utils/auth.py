from supabase import create_client
import yaml
from gotrue.errors import AuthApiError
from utils.errors import UserAuthenticationFaliure
from utils.schemas import Token
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os.path
import pickle

with open("config.yml", "r") as f: config = yaml.safe_load(f)

supabase = create_client(config["supabase"]["url"], config["supabase"]["key"])

def check_token(token):
    try:
        response = supabase.auth.get_user(token)
        return response
    except AuthApiError as e:
        raise UserAuthenticationFaliure("Invalid token")
    
def login(username: str, password: str) -> str:
    try:
        response = supabase.auth.sign_in_with_password({"email": username,"password": password})
        return response.session.access_token
    except AuthApiError as e:
        raise e
    
def google_auth(user_id: str):
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    token_fn = f"google_oath/{user_id}-token.pickle"
    if os.path.exists('token.pickle'):
        with open(token_fn, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                token_fn, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_fn, 'wb') as token:
            pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)