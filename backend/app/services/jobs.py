import json
import time
from uuid import uuid4
from .. import db

def enqueue(owner,asset_id,kind,config):
    now=time.time()
    job_id=str(uuid4())
    with db.connect() as con:
        con.execute('BEGIN IMMEDIATE')
        if not con.execute('SELECT id FROM assets WHERE id=? AND owner=?',(asset_id,owner)).fetchone():
            raise ValueError('This image was deleted before the job could be queued.')
        count=con.execute("SELECT COUNT(*) FROM jobs WHERE owner=? AND state IN ('queued','running')",(owner,)).fetchone()[0]
        if count>=3:
            raise ValueError('At most three active jobs are allowed per session.')
        con.execute('INSERT INTO jobs(id,owner,asset_id,kind,config,state,stage,created,updated) VALUES(?,?,?,?,?,?,?,?,?)',(job_id,owner,asset_id,kind,json.dumps(config),'queued','Waiting for worker',now,now))
    return job_id

def public(row):
    return {k:v for k,v in dict(row,id=row['id'],output=json.loads(row['output']) if row['output'] else None).items() if k not in ('owner','config')}

def claim():
    with db.connect() as con:
        con.execute('BEGIN IMMEDIATE')
        con.execute("UPDATE jobs SET state='cancelled',stage='Cancelled' WHERE state='queued' AND cancel_requested=1")
        row=con.execute("SELECT * FROM jobs WHERE state='queued' AND cancel_requested=0 ORDER BY created LIMIT 1").fetchone()
        if not row:
            return None
        now=time.time()
        con.execute("UPDATE jobs SET state='running',stage='Starting model process',updated=?,heartbeat=? WHERE id=?",(now,now,row['id']))
        return dict(row)
