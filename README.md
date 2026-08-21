# 🦎 Girgit

**Girgit** is a custom Command Line Interface (CLI) version control system built entirely in Python. It is a fully functional replica of Git, designed as an educational college project to study and demonstrate how **Git internals** (objects, cryptographic hashing, trees, and directed acyclic graphs) work under the hood.

---

## 🎯 Project Goals
The primary aim of this project is to demystify version control systems. Instead of relying on black-box external libraries, Girgit implements core Git concepts completely from scratch:
- Cryptographic hashing (SHA-1) for tracking Blob, Tree, and Commit objects.
- Graph traversal for commit history and branch management.
- The **Myers Diff Algorithm** (built from scratch) to calculate line-by-line file differences.

---

## 🏗️ Architecture & Project Structure
The codebase is cleanly modularized, mimicking professional software architecture:

```text
girgit/
├── cli.py      # The UI layer. Parses terminal commands and provides educational outputs.
├── base.py     # The core logic layer. Handles high-level operations (commits, trees, checkouts).
├── data.py     # The database layer. Reads/writes blobs and manages references (branches/HEAD).
├── diff.py     # The comparison layer. Groups trees and finds changed files.
└── Myers.py    # The algorithmic layer. Computes the Shortest Edit Script (diff) between texts.
```

---

## 🚀 Installation & Setup
To install Girgit locally on your machine for testing:

1. Open your terminal (Command Prompt, PowerShell, or Bash) in the root directory of this project.
2. Install the package in developer mode:
   ```bash
   python setup.py develop
   ```
This will register the `girgit` command globally on your system, allowing you to use it in any directory.

---

## 💻 Usage & Commands

To test Girgit, create a brand new, empty folder anywhere on your computer and run `girgit init`. 

Here is the complete cheat sheet of supported commands:

### Basics & Commits
* `girgit init` : Initializes a new repository (creates the hidden `.girgit` database).
* `girgit commit -m "<message>"` : Takes a snapshot of your directory, creates Blob/Tree objects, and saves a Commit. *(Girgit commits directly without a staging area).*
* `girgit log` : Displays the chronological history of commits, branching paths, and tags.
* `girgit status` : Shows the current active branch or if HEAD is detached.

### Branching & Navigation
* `girgit branch` : Lists all available branches.
* `girgit branch <name>` : Creates a new branch pointing to the current commit.
* `girgit checkout <branch_or_commit>` : Safely extracts the code from that branch into your working directory. *(Includes safety checks to prevent deleting uncommitted work!)*
* `girgit reset <commit_hash>` : Moves the current branch pointer backward in time.
* `girgit tag <name>` : Assigns a human-readable tag (like `v1.0`) to the current commit.

### Diffs & Visualization
* `girgit show` : Uses the custom Myers Diff algorithm to show exactly what lines of code were added (in green) or deleted (in red) in the latest commit.
* `girgit k` : Uses Graphviz to generate and open a PDF visualization of your entire commit history graph!

### Low-level Internal Commands
* `girgit hash-object <file>` : Compresses and hashes a file into the object database.
* `girgit cat-file <hash>` : Reads the raw contents of any internal object.
* `girgit write-tree` / `girgit read-tree` : Manually store or extract directory structures.

---

## 🎨 Educational UI
Girgit is specifically designed for students learning version control. Whenever you run a command, it prints bright yellow `[Internals]` logs explaining exactly what is happening in the background (e.g., *"Hashing files into Blob objects"*, *"Traversing commit graph"*). This turns every command into an interactive lesson on how version control systems manage data!
