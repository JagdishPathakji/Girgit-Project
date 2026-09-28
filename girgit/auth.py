import os
import json
import requests
import getpass
from typing import Optional

def print_edu(msg: str) -> None:
    print(f"\033[93m[Internals]\033[0m {msg}")

def print_success(msg: str) -> None:
    print(f"\033[92m{msg}\033[0m")

def print_err(msg: str) -> None:
    print(f"\033[91mError: {msg}\033[0m")

AUTH_FILE = os.path.expanduser('~/.girgit_credentials')
# Connected to live environment
API_BASE = 'https://version-control-system-mebn.onrender.com'

def login() -> None:
    """Prompt user for credentials and log in to the backend to get a JWT."""
    print("Log in to Girgit")
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ")

    if not email or not password:
        print_err("Email and password are required.")
        return

    print_edu("Authenticating with backend server...")
    try:
        response = requests.post(f"{API_BASE}/login", json={
            "email": email,
            "password": password,
            "cli": True
        })
        
        data = response.json()
        if response.status_code == 200 and data.get("status"):
            token = data.get("token")
            username = data.get("username")
            
            with open(AUTH_FILE, 'w') as f:
                json.dump({"token": token, "username": username, "email": email}, f)
                
            print_success(f"Successfully logged in as {username} ({email}).")
        else:
            print_err(data.get("message", "Authentication failed."))
    except requests.exceptions.ConnectionError:
        print_err(f"Could not connect to the server at {API_BASE}")
    except Exception as e:
        print_err(f"An error occurred: {str(e)}")

def logout() -> None:
    """Remove local credentials."""
    if os.path.exists(AUTH_FILE):
        os.remove(AUTH_FILE)
        print_success("Successfully logged out.")
    else:
        print("You are not currently logged in.")

def get_token() -> Optional[str]:
    """Retrieve the stored JWT token."""
    if not os.path.exists(AUTH_FILE):
        return None
    try:
        with open(AUTH_FILE, 'r') as f:
            data = json.load(f)
            return data.get("token")
    except:
        return None
