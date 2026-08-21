import os
import requests
from typing import Dict, Any, List
from . import data, base

def add_remote(name: str, url: str) -> None:
    """Save a remote URL."""
    path = f'{data.GIT_DIR}/remotes/{name}'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(url)

def get_remote(name: str) -> str:
    """Get a remote URL."""
    path = f'{data.GIT_DIR}/remotes/{name}'
    if not os.path.exists(path):
        raise ValueError(f"Remote '{name}' does not exist.")
    with open(path, 'r') as f:
        return f.read().strip()

def push(remote_name: str, branch: str) -> None:
    """Push local objects and branch ref to remote server."""
    base_url = get_remote(remote_name)
    
    local_ref_path = f'refs/heads/{branch}'
    local_oid = data.get_ref(local_ref_path).value
    if not local_oid:
        raise ValueError(f"Local branch '{branch}' does not exist.")
        
    # Attempt to initialize repo on server if it doesn't exist
    try:
        requests.post(f"{base_url}/init")
    except Exception:
        pass
        
    print(f"\033[93m[Internals]\033[0m Scanning local database for objects to sync...")
    
    objects_dir = f'{data.GIT_DIR}/objects'
    if os.path.exists(objects_dir):
        for root, _, files in os.walk(objects_dir):
            for oid in files:
                obj_path = os.path.join(root, oid)
                with open(obj_path, 'rb') as f:
                    content = f.read()
                # Upload object
                requests.post(f"{base_url}/objects/{oid}", data=content)
                
    print(f"\033[93m[Internals]\033[0m Updating remote branch '{branch}' to {local_oid[:10]}...")
    payload = {"oid": local_oid}
    resp = requests.post(f"{base_url}/{local_ref_path}", json=payload)
    resp.raise_for_status()
    print(f"\033[92mSuccessfully pushed to {remote_name}/{branch}\033[0m")

def clone(url: str, directory: str) -> None:
    """Clone a repository from a remote URL."""
    if os.path.exists(directory):
        raise ValueError(f"Directory '{directory}' already exists.")
        
    os.makedirs(directory)
    os.chdir(directory)
    base.init()
    
    print(f"\033[93m[Internals]\033[0m Fetching repository references from {url}...")
    
    resp = requests.get(f"{url}/refs")
    resp.raise_for_status()
    refs = resp.json().get('refs', {})
    
    if not refs:
        print("\033[91mRemote repository is empty or does not exist.\033[0m")
        return
        
    def download_object(oid: str):
        obj_path = f'{data.GIT_DIR}/objects/{oid}'
        if os.path.exists(obj_path):
            return
        r = requests.get(f"{url}/objects/{oid}")
        if r.status_code == 200:
            with open(obj_path, 'wb') as f:
                f.write(r.content)
            
    def fetch_commit_tree(commit_oid: str):
        download_object(commit_oid)
        commit_obj = base.get_commit(commit_oid)
        
        def fetch_tree(tree_oid: str):
            download_object(tree_oid)
            for type_, entry_oid, _ in base.iter_tree_entries(tree_oid):
                if type_ == 'blob':
                    download_object(entry_oid)
                elif type_ == 'tree':
                    fetch_tree(entry_oid)
                    
        fetch_tree(commit_obj.tree)
        if commit_obj.parent:
            fetch_commit_tree(commit_obj.parent)

    print(f"\033[93m[Internals]\033[0m Recursively downloading objects and history graph...")
    for ref_path, ref_value in refs.items():
        if ref_path == 'HEAD':
            continue
        if not ref_value.startswith('ref:'):
            fetch_commit_tree(ref_value)
            data.update_ref(ref_path, data.RefValue(symbolic=False, value=ref_value))
            
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
        
    print(f"\033[92mSuccessfully cloned into '{directory}'\033[0m")
