import argparse
import os
import sys
import textwrap
import subprocess
from typing import Any

from . import data
from . import base
from . import diff
from . import remote

def print_edu(msg: str) -> None:
    """Print educational internals information in yellow."""
    print(f"\033[93m[Internals]\033[0m {msg}")

def print_success(msg: str) -> None:
    """Print success messages in green."""
    print(f"\033[92m{msg}\033[0m")

def print_err(msg: str) -> None:
    """Print error messages in red."""
    print(f"\033[91mError: {msg}\033[0m", file=sys.stderr)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="girgit: An educational version control system")
    subparser = parser.add_subparsers(dest="command")
    subparser.required = True

    oid_type = base.get_oid

    init_parser = subparser.add_parser("init", help="Initialize a new repository")
    init_parser.set_defaults(func=init)

    # Cloud Networking Commands
    remote_parser = subparser.add_parser("remote", help="Manage set of tracked repositories")
    remote_parser.add_argument("action", choices=["add"])
    remote_parser.add_argument("name")
    remote_parser.add_argument("url")
    remote_parser.set_defaults(func=remote_cmd)

    push_parser = subparser.add_parser("push", help="Update remote refs along with associated objects")
    push_parser.add_argument("remote")
    push_parser.add_argument("branch")
    push_parser.set_defaults(func=push_cmd)

    clone_parser = subparser.add_parser("clone", help="Clone a repository into a new directory")
    clone_parser.add_argument("url")
    clone_parser.add_argument("directory")
    clone_parser.set_defaults(func=clone_cmd)

    hash_parser = subparser.add_parser("hash-object", help="Hash a file and store it")
    hash_parser.add_argument("file")
    hash_parser.set_defaults(func=hash_object)

    cat_file_parser = subparser.add_parser("cat-file", help="View stored object content")
    cat_file_parser.add_argument("oid", type=oid_type)
    cat_file_parser.set_defaults(func=cat_file)

    write_tree_parser = subparser.add_parser("write-tree", help="Store working directory as a tree")
    write_tree_parser.set_defaults(func=write_tree)

    read_tree_parser = subparser.add_parser("read-tree", help="Extract a tree to working directory")
    read_tree_parser.add_argument("tree", type=oid_type)
    read_tree_parser.set_defaults(func=read_tree)

    commit_parser = subparser.add_parser("commit", help="Save changes to repository")
    commit_parser.set_defaults(func=commit)
    commit_parser.add_argument('--message', '-m', required=True)

    log_parser = subparser.add_parser("log", help="View commit history")
    log_parser.set_defaults(func=log)
    log_parser.add_argument('oid', nargs='?', type=oid_type, default='@')

    checkout_parser = subparser.add_parser("checkout", help="Switch branches or restore files")
    checkout_parser.add_argument('commit')
    checkout_parser.set_defaults(func=checkout)

    tag_parser = subparser.add_parser("tag", help="Tag a commit")
    tag_parser.add_argument('name')
    tag_parser.add_argument('oid', nargs='?', type=oid_type, default='@')
    tag_parser.set_defaults(func=tag)

    k_parser = subparser.add_parser("k", help="Visualize the graph")
    k_parser.set_defaults(func=k)

    branch_parser = subparser.add_parser("branch", help="List, create, or delete branches")
    branch_parser.set_defaults(func=branch)
    branch_parser.add_argument('-d', '--delete', action='store_true', help="Delete a branch")
    branch_parser.add_argument('name', nargs='?')
    branch_parser.add_argument('start_point', default='@', type=oid_type, nargs='?')

    status_parser = subparser.add_parser("status", help="Show working tree status")
    status_parser.set_defaults(func=status)

    reset_parser = subparser.add_parser("reset", help="Reset current branch to specific commit")
    reset_parser.set_defaults(func=reset)
    reset_parser.add_argument('oid', type=oid_type)

    show_parser = subparser.add_parser("show", help="Show changes made in a commit")
    show_parser.set_defaults(func=show)
    show_parser.add_argument('oid', nargs='?', type=oid_type, default='@')
    
    return parser.parse_args()


def init(args: argparse.Namespace) -> None:
    base.init()
    print_edu("Created .girgit directory and objects/ database.")
    print_edu("Set HEAD to point to refs/heads/master.")
    print_success(f'Initialized empty girgit repo at {os.path.join(os.getcwd(), data.GIT_DIR)}')

def hash_object(args: argparse.Namespace) -> None:
    with open(args.file, 'rb') as out:
        oid = data.hash_object(out.read())
        print_edu(f"Read file content, compressed it, and stored at .girgit/objects/{oid}")
        print_success(oid)

def cat_file(args: argparse.Namespace) -> None:
    sys.stdout.flush()
    print_edu(f"Retrieving object {args.oid} from database...")
    content = data.get_object(args.oid, expected=None)
    sys.stdout.buffer.write(content)
    print()

def write_tree(args: argparse.Namespace) -> None:
    print_edu("Recursively writing blob and tree objects for working directory...")
    oid = base.write_tree()
    print_success(oid)

def read_tree(args: argparse.Namespace) -> None:
    print_edu(f"Extracting tree {args.tree} and overwriting working directory...")
    base.read_tree(args.tree)

def commit(args: argparse.Namespace) -> None:
    print_edu("Hashing all files in working directory into Blob objects...")
    print_edu("Creating Tree objects for directory structures...")
    oid = base.commit(args.message)
    print_edu(f"Created Commit object {oid[:10]} pointing to root Tree.")
    print_success(f'Successfully committed changes: {oid}')

def log(args: argparse.Namespace) -> None:
    refs = {} 
    for ref_name, ref in data.iter_refs():
        refs.setdefault(ref.value, []).append(ref_name)

    print_edu("Traversing commit graph using parent references...")
    for oid in base.iter_commits_and_parents({args.oid}):
        _print_commit(oid, base.get_commit(oid), refs.get(oid, []))

def checkout(args: argparse.Namespace) -> None:
    print_edu(f"Checking working directory for uncommitted changes...")
    base.checkout(args.commit)
    print_edu(f"Updated HEAD and extracted commit tree to working directory.")
    print_success(f"Successfully checked out {args.commit}")

def tag(args: argparse.Namespace) -> None:
    base.create_tag(args.name, args.oid)
    print_edu(f"Created reference .girgit/refs/tags/{args.name} pointing to {args.oid[:10]}")
    print_success(f"Tagged commit {args.oid[:10]} as {args.name}")

def k(args: argparse.Namespace) -> None: 
    print_edu("Generating graphviz dot string from commit DAG...")
    dot = "digraph commits{\n"
    oids = set()
    for ref_name, ref in data.iter_refs(deref=False): 
        dot += f'"{ref_name}" [shape=note]\n'
        dot += f'"{ref_name}" -> "{ref.value}"\n'
        if not ref.symbolic:
            oids.add(ref.value)
    for oid in base.iter_commits_and_parents(oids): 
        commit_obj = base.get_commit(oid)
        dot += f'"{oid}" [shape=box label="{oid[:10]}..." style=filled]\n'
        if commit_obj.parent:
            dot += f'"{oid}" -> "{commit_obj.parent}"\n'

    dot += "}"
    print_edu("Executing dot command to render PDF...")
    try:
        subprocess.run(
            'dot -Tpdf | open -f -a Preview',
            shell=True,
            input=dot,
            text=True
        )
    except FileNotFoundError:
        print_err("Graphviz 'dot' command not found. Please install it to use 'girgit k'.")

def branch(args: argparse.Namespace) -> None:
    if args.delete:
        if not args.name:
            raise ValueError("Must provide a branch name to delete.")
        print_edu(f"Validating branch '{args.name}' exists and is not checked out...")
        base.delete_branch(args.name)
        print_edu(f"Removed reference file .girgit/refs/heads/{args.name}.")
        print_success(f"Deleted branch {args.name}")
        return

    if not args.name:
        current = base.get_branch_name()
        for branch_name in base.iter_branch_name():
            prefix = '*' if branch_name == current else ' '
            if branch_name == current:
                print(f'\033[92m{prefix} {branch_name}\033[0m')
            else:
                print(f'{prefix} {branch_name}')
    else:
        base.create_branch(args.name, args.start_point)
        print_edu(f"Created reference .girgit/refs/heads/{args.name} pointing to {args.start_point[:10]}")
        print_success(f'Branch {args.name} created at {args.start_point[:10]}...')

def status(args: argparse.Namespace) -> None:
    print_edu("Reading HEAD reference to determine current state...")
    branch_name = base.get_branch_name()
    if branch_name:
        print_success(f'On branch {branch_name}')
    else:
        HEAD = base.get_oid('@')
        print(f'\033[93mHEAD detached at {HEAD[0:10]}...\033[0m')

def reset(args: argparse.Namespace) -> None:
    print_edu(f"Moving HEAD reference directly to {args.oid[:10]}...")
    base.reset(args.oid)
    print_success(f"Reset complete.")

def _print_commit(oid: str, commit_obj: base.Commit, refs: list = None) -> None: 
    refs_str = f" \033[93m({','.join(refs)})\033[0m" if refs else ""
    print(f'\033[94mcommit : {oid}\033[0m{refs_str}') 
    print(textwrap.indent(commit_obj.message, '      '))
    print('')

def show(args: argparse.Namespace) -> None:
    if not args.oid:
        return
    print_edu(f"Retrieving commit {args.oid[:10]} and its parent...")
    commit_obj = base.get_commit(args.oid)
    parent_tree = None

    if commit_obj.parent:
        parent_tree = base.get_commit(commit_obj.parent).tree

    _print_commit(args.oid, commit_obj)

    print_edu(f"Running Myers diff algorithm on tree differences...")
    result = diff.diff_tree(base.get_tree(parent_tree), base.get_tree(commit_obj.tree))
    print(result)

def remote_cmd(args: argparse.Namespace) -> None:
    if args.action == "add":
        remote.add_remote(args.name, args.url)
        print_success(f"Added remote '{args.name}' pointing to {args.url}")

def push_cmd(args: argparse.Namespace) -> None:
    remote.push(args.remote, args.branch)

def clone_cmd(args: argparse.Namespace) -> None:
    remote.clone(args.url, args.directory)

def main() -> None:
    os.system('') # Enables ANSI color parsing on Windows terminals
    try:
        args = parse_args()
        args.func(args)
    except Exception as e:
        print_err(str(e))
        sys.exit(1)
