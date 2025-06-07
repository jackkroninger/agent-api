from supabase import create_client
import yaml
from gotrue.errors import AuthApiError
from utils.errors import UserAuthenticationFaliure
from utils.schemas import Token

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