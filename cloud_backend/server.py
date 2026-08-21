import os
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Girgit Cloud Server", description="A bare-repository server for Girgit")

# Base directory to store bare repositories
STORAGE_DIR = os.path.join(os.path.dirname(__file__), 'storage')
os.makedirs(STORAGE_DIR, exist_ok=True)

def get_repo_path(username: str, repo_name: str) -> str:
    """Return the absolute path to the bare repository."""
    return os.path.join(STORAGE_DIR, username, repo_name)

@app.get("/api/v1/users")
async def list_users():
    """List all users (folders inside STORAGE_DIR). Useful for frontend."""
    if not os.path.exists(STORAGE_DIR):
        return {"users": []}
    users = [d for d in os.listdir(STORAGE_DIR) if os.path.isdir(os.path.join(STORAGE_DIR, d))]
    return {"users": users}

@app.get("/api/v1/repos/{username}")
async def list_user_repos(username: str):
    """List all repositories for a specific user. Useful for frontend."""
    user_path = os.path.join(STORAGE_DIR, username)
    if not os.path.exists(user_path):
        raise HTTPException(status_code=404, detail="User not found")
    repos = [d for d in os.listdir(user_path) if os.path.isdir(os.path.join(user_path, d))]
    return {"repositories": repos}

@app.post("/api/v1/repos/{username}/{repo_name}/init")
async def init_repo(username: str, repo_name: str):
    """Initialize a bare girgit repository on the server."""
    repo_path = get_repo_path(username, repo_name)
    if os.path.exists(repo_path):
        raise HTTPException(status_code=400, detail="Repository already exists")
    
    os.makedirs(os.path.join(repo_path, 'objects'), exist_ok=True)
    os.makedirs(os.path.join(repo_path, 'refs', 'heads'), exist_ok=True)
    
    with open(os.path.join(repo_path, 'HEAD'), 'w') as f:
        f.write('ref: refs/heads/main')
        
    return {"message": f"Repository {username}/{repo_name} initialized."}

@app.post("/api/v1/repos/{username}/{repo_name}/objects/{oid}")
async def upload_object(username: str, repo_name: str, oid: str, request: Request):
    """Receive an object (blob, tree, commit) from the client and save it."""
    repo_path = get_repo_path(username, repo_name)
    if not os.path.exists(repo_path):
        raise HTTPException(status_code=404, detail="Repository not found")
    
    obj_path = os.path.join(repo_path, 'objects', oid)
    body = await request.body()
    
    if not os.path.exists(obj_path):
        with open(obj_path, 'wb') as f:
            f.write(body)
            
    return {"message": "Object saved"}

@app.get("/api/v1/repos/{username}/{repo_name}/objects/{oid}")
async def download_object(username: str, repo_name: str, oid: str):
    """Send an object to the client."""
    repo_path = get_repo_path(username, repo_name)
    obj_path = os.path.join(repo_path, 'objects', oid)
    
    if not os.path.exists(obj_path):
        raise HTTPException(status_code=404, detail="Object not found")
        
    return FileResponse(obj_path, media_type='application/octet-stream')

@app.get("/api/v1/repos/{username}/{repo_name}/refs")
async def list_refs(username: str, repo_name: str):
    """List all references (branches/tags) in the repository."""
    repo_path = get_repo_path(username, repo_name)
    if not os.path.exists(repo_path):
        raise HTTPException(status_code=404, detail="Repository not found")
        
    refs = {}
    refs_dir = os.path.join(repo_path, 'refs')
    if os.path.exists(refs_dir):
        for root, _, filenames in os.walk(refs_dir):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, repo_path).replace('\\', '/')
                with open(full_path, 'r') as f:
                    refs[rel_path] = f.read().strip()
                    
    head_path = os.path.join(repo_path, 'HEAD')
    if os.path.exists(head_path):
        with open(head_path, 'r') as f:
            refs['HEAD'] = f.read().strip()
            
    return {"refs": refs}

class RefUpdate(BaseModel):
    oid: str

@app.post("/api/v1/repos/{username}/{repo_name}/{ref_path:path}")
async def update_ref(username: str, repo_name: str, ref_path: str, data: RefUpdate):
    """Update a reference to point to a new commit OID."""
    repo_path = get_repo_path(username, repo_name)
    if not os.path.exists(repo_path):
        raise HTTPException(status_code=404, detail="Repository not found")
        
    full_ref_path = os.path.join(repo_path, ref_path)
    os.makedirs(os.path.dirname(full_ref_path), exist_ok=True)
    
    with open(full_ref_path, 'w') as f:
        f.write(data.oid)
        
    return {"message": f"Reference {ref_path} updated"}

if __name__ == '__main__':
    import uvicorn
    print("🚀 Girgit FastAPI Server starting on http://localhost:8000")
    print(f"📂 Bare repositories will be stored in: {STORAGE_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
