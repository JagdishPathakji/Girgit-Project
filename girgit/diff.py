import collections
from typing import Iterator, Tuple
from . import data
from . import base
from . import Myers
from .Edit_Wrapper import Edit

def compare_tree(*trees: dict) -> Iterator[Tuple]:
    """Take multiple trees and return OIDs grouped by filename."""
    entries = collections.defaultdict(lambda: [None] * len(trees))

    for i, tree in enumerate(trees):
        for path, oid in tree.items():
            entries[path][i] = oid

    for path, oids in entries.items():
        yield path, *oids

def is_binary(data_bytes: bytes) -> bool:
    """Check if file contents are binary by searching for NUL byte."""
    return b'\x00' in data_bytes

def diff_blob(o_from: str, o_to: str, path: str = "blob") -> str:
    """Compute and format the Myers diff between two blob objects."""
    a_file = data.get_object(o_from) if o_from else b""
    b_file = data.get_object(o_to) if o_to else b""

    if is_binary(a_file) or is_binary(b_file):
        return f'Binary files a/{path} and b/{path} differ\n'

    a_lines = a_file.decode('utf-8', errors='replace').splitlines(keepends=True)
    b_lines = b_file.decode('utf-8', errors='replace').splitlines(keepends=True)

    output = f'--- a/{path}\n+++ b/{path}\n'
    edits = Myers.Myers(a_lines, b_lines).diff_operations()

    old_start = next((edit.old_line.number for edit in edits if edit.old_line), 0)
    old_chunk = sum(1 for edit in edits if edit.type != "ins")
    new_start = next((edit.new_line.number for edit in edits if edit.new_line), 0)
    new_chunk = sum(1 for edit in edits if edit.type != "del")

    output += f'@@ -{old_start},{old_chunk} +{new_start},{new_chunk} @@\n'

    for edit in edits:
        if edit.type == 'ins':
            output += f'\033[92m+ {edit.text}\033[0m'
        elif edit.type == 'del':
            output += f'\033[91m- {edit.text}\033[0m'
        else:
            output += f'  {edit.text}'

    return output

def diff_tree(t_from: dict, t_to: dict) -> str:
    """Compare two trees and generate diff outputs for changed blobs."""
    output = ''
    for path, o_from, o_to in compare_tree(t_from, t_to):
        if o_from != o_to:
            output += diff_blob(o_from, o_to, path)
    return output
