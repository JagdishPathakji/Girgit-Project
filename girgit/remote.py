import os
import requests
import base64
from typing import Dict, Any, List
from . import data, base
from .auth import get_token, API_BASE

def add_remote(name: str, url: str) -> None:
    """Save a remote URL. Expected format: username/repo-name"""
    path = f'{data.GIT_DIR}/remotes/{name}'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(url)

def get_remote(name: str) -> str:
    path = f'{data.GIT_DIR}/remotes/{name}'
    if not os.path.exists(path):
        raise ValueError(f"Remote '{name}' does not exist.")
    with open(path, 'r') as f:
        return f.read().strip()

def push(remote_name: str, branch: str) -> None:
    repo = get_remote(remote_name)
    
    local_ref_path = f'refs/heads/{branch}'
    local_oid = data.get_ref(local_ref_path).value
    if not local_oid:
        raise ValueError(f"Local branch '{branch}' does not exist.")
        
    print(f"\033[93m[Internals]\033[0m Preparing to push to {repo} on branch {branch}...")
    
    objects_payload = {}
    objects_dir = f'{data.GIT_DIR}/objects'
    if os.path.exists(objects_dir):
        all_objects = []
        for root, _, files in os.walk(objects_dir):
            for oid in files:
                all_objects.append((root, oid))
                
        print(f"\033[93m[Internals]\033[0m Found {len(all_objects)} objects. Packaging...")
        for i, (root, oid) in enumerate(all_objects, 1):
            obj_path = os.path.join(root, oid)
            with open(obj_path, 'rb') as f:
                content = f.read()
                objects_payload[oid] = base64.b64encode(content).decode('utf-8')
                
    refs_payload = {
        local_ref_path: local_oid,
        "HEAD": f"ref: {local_ref_path}"
    }

    token = get_token()
    if not token:
        print("\033[91mError: You are not logged in. Please run 'girgit login' first.\033[0m")
        return

    print(f"\033[93m[Internals]\033[0m Uploading to backend server...")
    
    try:
        response = requests.post(f"{API_BASE}/cli/push", json={
            "repo": repo,
            "objects": objects_payload,
            "refs": refs_payload
        }, headers={
            "Authorization": f"Bearer {token}"
        })
        
        resp_data = response.json()
        if response.status_code == 200 and resp_data.get("status"):
            print(f"\033[92mSuccessfully pushed to {remote_name}/{branch}!\033[0m")
        else:
            print(f"\033[91mError pushing: {resp_data.get('message', 'Unknown error')}\033[0m")
    except requests.exceptions.ConnectionError:
        print(f"\033[91mError: Could not connect to the server at {API_BASE}\033[0m")
    except Exception as e:
        print(f"\033[91mError during push: {str(e)}\033[0m")


def clone(repo_name: str, directory: str) -> None:
    if os.path.exists(directory):
        raise ValueError(f"Directory '{directory}' already exists.")
        
    print(f"\033[93m[Internals]\033[0m Fetching repository data from server for {repo_name}...")
    
    headers = {}
    token = get_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.get(f"{API_BASE}/cli/clone", params={"repo": repo_name}, headers=headers)
        if response.status_code != 200:
            resp_data = response.json()
            print(f"\033[91mError cloning: {resp_data.get('message', 'Unknown error')}\033[0m")
            return
            
        data_payload = response.json()
        if not data_payload.get("status"):
            print(f"\033[91mError cloning: {data_payload.get('message', 'Unknown error')}\033[0m")
            return
            
        objects = data_payload.get("objects", {})
        refs = data_payload.get("refs", {})
        
        if not refs:
            print("\033[91mRemote repository is empty or does not exist.\033[0m")
            return

        os.makedirs(directory)
        os.chdir(directory)
        base.init()

        print(f"\033[93m[Internals]\033[0m Writing objects and references...")

        for oid, b64content in objects.items():
            obj_path = f'{data.GIT_DIR}/objects/{oid}'
            os.makedirs(os.path.dirname(obj_path), exist_ok=True)
            with open(obj_path, 'wb') as f:
                f.write(base64.b64decode(b64content))

        for ref_path, ref_value in refs.items():
            if ref_path == 'HEAD':
                continue
            data.update_ref(ref_path, data.RefValue(symbolic=False, value=ref_value))
            
        # Add remote automatically
        add_remote('origin', repo_name)
        
        # Checkout branch
        head_ref = refs.get('HEAD', '')
        if head_ref.startswith('ref: '):
            branch = head_ref.split('refs/heads/')[1]
            try:
                base.get_oid(branch)
                print(f"\033[93m[Internals]\033[0m Rebuilding working directory from {branch}...")
                base.checkout(branch, force=True)
            except ValueError:
                available_branches = [b for b in refs.keys() if b.startswith('refs/heads/')]
                if available_branches:
                    fallback_branch = available_branches[0].split('refs/heads/')[1]
                    print(f"\033[93m[Internals]\033[0m Default branch '{branch}' missing. Rebuilding from {fallback_branch} instead...")
                    base.checkout(fallback_branch, force=True)
                else:
                    print("\033[93m[Internals]\033[0m No branches found to checkout.")
            
        print(f"\033[92mSuccessfully cloned '{repo_name}' into '{directory}'\033[0m")
        
    except requests.exceptions.ConnectionError:
        print(f"\033[91mError: Could not connect to the server at {API_BASE}\033[0m")
    except Exception as e:
        print(f"\033[91mError during clone: {str(e)}\033[0m")
