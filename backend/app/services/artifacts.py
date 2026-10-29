from uuid import uuid4
from .. import db
from ..settings import DATA, private_path

def add(owner, asset_id, path, kind):
    artifact_id = str(uuid4())
    relative = path.resolve().relative_to(DATA).as_posix()
    private_path(relative)
    db.execute('INSERT INTO artifacts VALUES(?,?,?,?,?)', (artifact_id,owner,asset_id,relative,kind))
    return artifact_id

def get(artifact_id, owner):
    row = db.one('SELECT * FROM artifacts WHERE id=? AND owner=?',(artifact_id,owner))
    if row is None:
        return None
    row['file'] = private_path(row['path'])
    return row
