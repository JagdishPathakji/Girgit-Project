import os
import hashlib
from collections import namedtuple
from typing import Optional, Tuple, Iterator

GIT_DIR = '.girgit'
RefValue = namedtuple('RefValue', ['symbolic', 'value'])

def init() -> None:
    """Initialize the .girgit repository structure."""
    os.makedirs(GIT_DIR, exist_ok=True)
    os.makedirs(f'{GIT_DIR}/objects', exist_ok=True)

def hash_object(data: bytes, type_: str = 'blob') -> str:
    """Hash the data and store it in the object database."""
    obj = type_.encode() + b'\x00' + data
    oid = hashlib.sha1(obj).hexdigest()
    path = f'{GIT_DIR}/objects/{oid}'
    with open(path, 'wb') as inp:
        inp.write(obj)
    return oid

def get_object(oid: str, expected: Optional[str] = 'blob') -> bytes:
    """Retrieve an object from the database by its OID."""
    path = f'{GIT_DIR}/objects/{oid}'
    if not os.path.exists(path):
        raise ValueError(f"Object {oid} not found in database.")
    with open(path, 'rb') as out:
        obj = out.read()
    type_bytes, _, content = obj.partition(b'\x00')
    type_str = type_bytes.decode()
    if expected is not None:
        if type_str != expected:
            raise ValueError(f"Wanted {expected} type, got {type_str}")
    return content

def update_ref(ref: str, value: RefValue, deref: bool = True) -> None:
    """Update a reference (like HEAD or a branch) to point to a new value."""
    ref = get_ref_internal(ref, deref)[0]
    if not value.value:
        raise ValueError("Cannot update reference with empty value.")
    
    val_str = f'ref: {value.value}' if value.symbolic else value.value
    ref_path = f'{GIT_DIR}/{ref}'
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open(ref_path, 'w') as inp:
        inp.write(val_str)

def get_ref(ref: str, deref: bool = True) -> RefValue:
    """Get the value of a reference."""
    return get_ref_internal(ref, deref)[1]

def get_ref_internal(ref: str, deref: bool) -> Tuple[str, RefValue]:
    """Internal function to recursively resolve references."""
    path = f'{GIT_DIR}/{ref}'
    if os.path.isfile(path):
        with open(path, 'r') as out:
            value = out.read().strip()
            symbolic_flag = False
            if value and value.startswith('ref:'):
                value = value.split(":", 1)[1].strip()
                if deref:
                    return get_ref_internal(value, deref=True)
                else:
                    symbolic_flag = True
            return ref, RefValue(symbolic=symbolic_flag, value=value)
    return ref, RefValue(symbolic=False, value=None)

def iter_refs(prefix: str = '', deref: bool = True) -> Iterator[Tuple[str, RefValue]]:
    """Iterate over all references in the repository."""
    refs = ['HEAD']
    for root, _, filenames in os.walk(f'{GIT_DIR}/refs'):
        root = os.path.relpath(root, GIT_DIR).replace('\\', '/')
        refs.extend(f'{root}/{file}' for file in filenames)
    for ref_name in refs:
        if not ref_name.startswith(prefix):
            continue
        yield ref_name, get_ref(ref_name, deref=deref)
