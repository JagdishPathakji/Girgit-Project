import os
import boto3
from typing import Dict, Any, List
from . import data, base

def add_remote(name: str, url: str) -> None:
    """Save a remote URL. Expected format: s3://bucket-name/project-prefix"""
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

def parse_s3_url(url: str):
    if not url.startswith("s3://"):
        raise ValueError("URL must start with s3:// (e.g. s3://bucket-name/username/repo)")
    parts = url.replace("s3://", "").split("/")
    bucket = parts[0]
    prefix = "/".join(parts[1:])
    return bucket, prefix

def push(remote_name: str, branch: str) -> None:
    url = get_remote(remote_name)
    bucket_name, prefix = parse_s3_url(url)
    s3 = boto3.client('s3')
    
    local_ref_path = f'refs/heads/{branch}'
    local_oid = data.get_ref(local_ref_path).value
    if not local_oid:
        raise ValueError(f"Local branch '{branch}' does not exist.")
        
    print(f"\033[93m[Internals]\033[0m Connected to S3 Bucket: {bucket_name}")
    
    objects_dir = f'{data.GIT_DIR}/objects'
    if os.path.exists(objects_dir):
        all_objects = []
        for root, _, files in os.walk(objects_dir):
            for oid in files:
                all_objects.append((root, oid))
                
        print(f"\033[93m[Internals]\033[0m Found {len(all_objects)} objects. Uploading to S3...")
        for i, (root, oid) in enumerate(all_objects, 1):
            print(f"  -> Uploading object {i}/{len(all_objects)} ({oid[:8]})...")
            obj_path = os.path.join(root, oid)
            s3_key = f"{prefix}/objects/{oid}" if prefix else f"objects/{oid}"
            with open(obj_path, 'rb') as f:
                content = f.read()
            try:
                s3.put_object(Bucket=bucket_name, Key=s3_key, Body=content)
            except Exception as e:
                print(f"\n\033[91mError uploading to S3: {e}\033[0m")
                return
                
    print(f"\033[93m[Internals]\033[0m Updating remote branch '{branch}' to {local_oid[:10]}...")
    ref_s3_key = f"{prefix}/{local_ref_path}" if prefix else local_ref_path
    s3.put_object(Bucket=bucket_name, Key=ref_s3_key, Body=local_oid.encode('utf-8'))
    
    # Set HEAD to the pushed branch if it doesn't exist yet
    head_s3_key = f"{prefix}/HEAD" if prefix else "HEAD"
    try:
        s3.head_object(Bucket=bucket_name, Key=head_s3_key)
    except:
        s3.put_object(Bucket=bucket_name, Key=head_s3_key, Body=f"ref: {local_ref_path}".encode('utf-8'))

    print(f"\033[92mSuccessfully pushed to {remote_name}/{branch} on AWS S3\033[0m")

def clone(url: str, directory: str) -> None:
    bucket_name, prefix = parse_s3_url(url)
    s3 = boto3.client('s3')
    
    if os.path.exists(directory):
        raise ValueError(f"Directory '{directory}' already exists.")
        
    os.makedirs(directory)
    os.chdir(directory)
    base.init()
    
    print(f"\033[93m[Internals]\033[0m Fetching repository data from S3 Bucket: {bucket_name}...")
    
    # 1. Fetch all refs
    refs_prefix = f"{prefix}/refs/" if prefix else "refs/"
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=refs_prefix)
    
    refs = {}
    if 'Contents' in response:
        for obj in response['Contents']:
            key = obj['Key']
            resp = s3.get_object(Bucket=bucket_name, Key=key)
            content = resp['Body'].read().decode('utf-8').strip()
            # Remove the s3 prefix from the local path
            local_ref_path = key[len(prefix)+1:] if prefix else key
            refs[local_ref_path] = content
            
    # Get HEAD
    head_s3_key = f"{prefix}/HEAD" if prefix else "HEAD"
    try:
        resp = s3.get_object(Bucket=bucket_name, Key=head_s3_key)
        refs['HEAD'] = resp['Body'].read().decode('utf-8').strip()
    except:
        pass
        
    if not refs:
        print("\033[91mRemote S3 repository is empty or does not exist.\033[0m")
        return
        
    def download_object(oid: str):
        obj_path = f'{data.GIT_DIR}/objects/{oid}'
        if os.path.exists(obj_path):
            return
        s3_key = f"{prefix}/objects/{oid}" if prefix else f"objects/{oid}"
        try:
            resp = s3.get_object(Bucket=bucket_name, Key=s3_key)
            with open(obj_path, 'wb') as f:
                f.write(resp['Body'].read())
        except Exception as e:
            pass # Ignore missing objects

    def fetch_commit_tree(commit_oid: str):
        download_object(commit_oid)
        try:
            commit_obj = base.get_commit(commit_oid)
        except:
            return # Object download failed
            
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

    print(f"\033[93m[Internals]\033[0m Recursively downloading objects from AWS S3...")
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
        
    print(f"\033[92mSuccessfully cloned into '{directory}' from AWS S3\033[0m")
