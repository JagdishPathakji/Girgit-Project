# 🦎 Girgit

**Girgit** is a custom Command Line Interface (CLI) version control system built entirely in Python. It is a fully functional replica of Git, designed as an educational college project to study and demonstrate how **Git internals** (objects, cryptographic hashing, trees, and directed acyclic graphs) work under the hood.

This project also features a **Custom Cloud Backend** built with FastAPI, allowing you to push, clone, and sync your repositories over a network—just like real GitHub!

---

## 🎯 Project Goals
The primary aim of this project is to demystify version control systems. Instead of relying on black-box external libraries, Girgit implements core Git concepts completely from scratch:
- Cryptographic hashing (SHA-1) for tracking Blob, Tree, and Commit objects.
- Graph traversal for commit history and branch management.
- The **Myers Diff Algorithm** (built from scratch) to calculate line-by-line file differences.
- Client-Server Architecture to sync binary objects via HTTP.

---

## 🏗️ Architecture & Project Structure
The codebase is cleanly modularized into two parts: the CLI Client and the Cloud Server.

### 1. The Client (CLI)
```text
girgit/
├── cli.py      # The UI layer. Parses terminal commands and provides educational outputs.
├── base.py     # The core logic layer. Handles high-level operations (commits, trees, checkouts).
├── data.py     # The database layer. Reads/writes blobs and manages local references.
├── diff.py     # The comparison layer. Custom Myers Diff Algorithm to find changed files.
└── remote.py   # The networking layer. Handles HTTP communication for pushing and cloning.
```

### 2. The Cloud Backend (FastAPI)
```text
cloud_backend/
└── server.py   # A lightweight FastAPI server that acts as a remote Bare Repository.
```

---

## 🚀 Installation & Setup

### 1. Install Dependencies
You will need Python 3 installed. Run the following command to install the required networking and server libraries:
```bash
pip install fastapi uvicorn requests
```

### 2. Install the Girgit CLI
Install the package in developer mode to register the `girgit` command globally on your system:
```bash
python setup.py develop
```

---

## ☁️ How to run the Cloud Server
To test remote syncing, start the FastAPI server on your machine:
```bash
python cloud_backend/server.py
```
The server will start on `http://localhost:8000` and is structured to support a future web frontend by organizing bare repositories using dynamic endpoints: `/api/v1/repos/<username>/<repo_name>`.

---

## 💻 Usage & Commands

To test Girgit locally, create an empty folder and run `girgit init`. Here is the complete cheat sheet of supported commands:

### Basics & Commits
* `girgit init` : Initializes a new repository (creates the hidden `.girgit` database).
* `girgit commit -m "<message>"` : Takes a snapshot of your directory and saves a Commit.
* `girgit log` : Displays the chronological history of commits and branches.
* `girgit status` : Shows the current active branch.

### Branching & Navigation
* `girgit branch` : Lists all available branches.
* `girgit branch <name>` : Creates a new branch pointing to the current commit.
* `girgit branch -d <name>` : Safely deletes a branch.
* `girgit checkout <branch_or_commit>` : Safely extracts the code from that branch into your working directory (blocks data loss if you have uncommitted changes!).
* `girgit reset <commit_hash>` : Moves the current branch pointer backward in time.
* `girgit tag <name>` : Assigns a human-readable tag (like `v1.0`) to the current commit.

### Cloud Networking 🌐
* `girgit remote add <name> <url>` : Bookmarks a remote server URL (e.g., `girgit remote add origin http://localhost:8000/api/v1/repos/Jagdish/Project`).
* `girgit push <remote_name> <branch>` : Uploads your local binary objects and branch references to the remote server.
* `girgit clone <url> <directory_name>` : Downloads a repository from the server and reconstructs the working directory on your machine.

### Diffs & Visualization
* `girgit show` : Uses the custom Myers Diff algorithm to show exactly what lines of code were added (in green) or deleted (in red) in the latest commit.
* `girgit k` : Uses Graphviz to generate and open a PDF visualization of your entire commit history graph!

---

## 🎨 Educational UI
Girgit is specifically designed for students learning version control. Whenever you run a command, it prints bright yellow `[Internals]` logs explaining exactly what is happening in the background (e.g., *"Hashing files into Blob objects"*, *"Recursively downloading objects and history graph"*). This turns every command into an interactive lesson on how version control systems manage data!
