import operator
import string
import os
import itertools
import collections
from typing import Iterator, Dict, Tuple, Optional, Set
from . import data

Commit = collections.namedtuple('Commit', ['tree', 'parent', 'message'])

def write_tree(directory: str = ".") -> str:
    """Recursively hash files in a directory and return the root tree OID."""
    entries = []
    with os.scandir(directory) as it:
        for entry in it:
            full = f'{directory}/{entry.name}'
            if is_ignored(full):
                continue

            if entry.is_file(follow_symlinks=False):
                type_ = 'blob'
                with open(full, 'rb') as out:
                    oid = data.hash_object(out.read())
            elif entry.is_dir(follow_symlinks=False):
                type_ = 'tree'
                oid = write_tree(full)
            else:
                continue

            entries.append((entry.name, oid, type_))

    tree = ''.join(f'{type_} {oid} {name}\n' for name, oid, type_ in sorted(entries))
    return data.hash_object(tree.encode(), 'tree')

def iter_tree_entries(oid: str) -> Iterator[Tuple[str, str, str]]:
    """Iterate over the entries of a tree object."""
    if not oid:
        return
    tree = data.get_object(oid, 'tree')
    for entry in tree.decode().splitlines():
        type_, entry_oid, name = entry.split(' ', 2)
        yield type_, entry_oid, name

def get_tree(oid: str, base_path: str = '') -> Dict[str, str]:
    """Recursively parse a tree and return a dict mapping file paths to their blob OIDs."""
    result = {}
    for type_, entry_oid, name in iter_tree_entries(oid):
        if '/' in name or name in ('.', '..'):
            raise ValueError(f"Invalid tree entry name: {name}")
        path = base_path + name
        if type_ == 'blob':
            result[path] = entry_oid
        elif type_ == 'tree':
            result.update(get_tree(entry_oid, f'{path}/'))
        else:
            raise ValueError(f'Unknown tree entry type: {type_}')
    return result

def read_tree(tree_oid: str) -> None:
    """Extract a tree object to the working directory."""
    empty_current_dir()
    for path, oid in get_tree(oid=tree_oid, base_path='./').items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as inp:
            inp.write(data.get_object(oid))

def empty_current_dir() -> None:
    """Delete all tracked files in the current directory."""
    for root, dirnames, filenames in os.walk('.', topdown=False):
        for filename in filenames:
            path = os.path.relpath(f'{root}/{filename}')
            if is_ignored(path) or not os.path.isfile(path):
                continue
            os.remove(path)
        for dirname in dirnames:
            path = os.path.relpath(f'{root}/{dirname}')
            if is_ignored(path):
                continue
            try:
                os.rmdir(path)
            except (OSError, FileNotFoundError):
                pass

def commit(message: str) -> str:
    """Create a commit object linking to a tree and the parent commit."""
    commit_data = f'tree {write_tree()}\n'

    HEAD = data.get_ref('HEAD').value
    if HEAD:
        commit_data += f'parent {HEAD}\n'

    commit_data += '\n'
    commit_data += f'{message}\n'

    oid = data.hash_object(commit_data.encode(), 'commit')
    data.update_ref('HEAD', data.RefValue(symbolic=False, value=oid))
    return oid

def get_commit(oid: str) -> Commit:
    """Retrieve and parse a commit object."""
    parent = None
    tree = None
    commit_data = data.get_object(oid, 'commit').decode()
    lines = iter(commit_data.splitlines())

    for line in itertools.takewhile(operator.truth, lines):
        key, value = line.split(' ', 1)
        if key == 'tree':
            tree = value
        elif key == 'parent':
            parent = value
        else:
            raise ValueError(f'Unknown Field {key} in commit {oid}')
    
    if not tree:
        raise ValueError(f'Commit {oid} is missing a tree reference')

    message = '\n'.join(lines)
    return Commit(tree=tree, parent=parent, message=message)

def checkout(name: str, force: bool = False) -> None:
    """Checkout a commit or branch to the working directory."""
    if not force:
        HEAD = data.get_ref('HEAD').value
        if HEAD:
            head_commit = get_commit(HEAD)
            current_tree = write_tree()
            if current_tree != head_commit.tree:
                raise RuntimeError("You have uncommitted changes. Please commit them before checking out.")

    oid = get_oid(name)
    commit_obj = get_commit(oid)
    read_tree(commit_obj.tree)

    if is_branch(name):
        HEAD_ref = data.RefValue(symbolic=True, value=f'refs/heads/{name}')
    else:
        HEAD_ref = data.RefValue(symbolic=False, value=oid)
        
    data.update_ref('HEAD', HEAD_ref, deref=False)

def is_branch(name: str) -> bool:
    """Check if a reference name represents a branch."""
    return data.get_ref(f'refs/heads/{name}').value is not None

def create_tag(name: str, oid: str) -> None:
    """Create a tag reference pointing to an OID."""
    data.update_ref(f'refs/tags/{name}', data.RefValue(symbolic=False, value=oid))

def is_ignored(path: str) -> bool:
    """Check if a path should be ignored by girgit."""
    path = path.replace('\\', '/')
    parts = path.split('/')
    return any(p in {'.girgit', '.git', '.venv', '__pycache__'} for p in parts)

def get_oid(name: str) -> str:
    """Resolve a name (branch, tag, HEAD, or SHA1) to its corresponding OID."""
    if name == "@":
        name = "HEAD"

    refs_to_try = [
        f'{name}',
        f'refs/{name}',
        f'refs/tags/{name}',
        f'refs/heads/{name}',
    ]
    for ref in refs_to_try:
        ref_obj = data.get_ref(ref, deref=False)
        if ref_obj.value:
            return data.get_ref(ref, deref=True).value

    is_hex = all(c in string.hexdigits for c in name)
    if len(name) == 40 and is_hex:
        return name

    raise ValueError(f'Unknown name or reference: {name}')

def iter_commits_and_parents(oids: Set[str]) -> Iterator[str]:
    """Iterate through the commit history graph starting from the given OIDs."""
    oids_queue = collections.deque(oids)
    visited = set()
    while oids_queue:
        oid = oids_queue.popleft()
        if not oid or oid in visited:
            continue
        visited.add(oid)
        yield oid
        commit_obj = get_commit(oid)
        oids_queue.appendleft(commit_obj.parent)

def create_branch(name: str, oid: str) -> None:
    """Create a new branch reference."""
    data.update_ref(f'refs/heads/{name}', data.RefValue(symbolic=False, value=oid))

def delete_branch(name: str) -> None:
    """Delete a branch reference."""
    current_branch = get_branch_name()
    if name == current_branch:
        raise ValueError(f"Cannot delete the currently checked-out branch '{name}'.")
    
    path = f'{data.GIT_DIR}/refs/heads/{name}'
    if not os.path.exists(path):
        raise ValueError(f"Branch '{name}' does not exist.")
    
    os.remove(path)

def init() -> None:
    """Initialize repository and set default HEAD."""
    data.init()
    data.update_ref('HEAD', data.RefValue(symbolic=True, value='refs/heads/master'))

def get_branch_name() -> Optional[str]:
    """Get the name of the current branch, or None if detached."""
    HEAD = data.get_ref('HEAD', deref=False)
    if HEAD.symbolic:
        head_val = HEAD.value
        if not head_val.startswith('refs/heads/'):
            raise ValueError(f"HEAD points to invalid reference: {head_val}")
        return os.path.relpath(head_val, 'refs/heads/').replace('\\', '/')
    return None

def iter_branch_name() -> Iterator[str]:
    """Iterate over all branch names."""
    for ref_name, _ in data.iter_refs('refs/heads/'):
        yield os.path.relpath(ref_name, 'refs/heads/').replace('\\', '/')

def reset(oid: str) -> None:
    """Reset HEAD to a specific commit."""
    data.update_ref('HEAD', data.RefValue(symbolic=False, value=oid))
