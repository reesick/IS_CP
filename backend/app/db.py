import sqlite3
import time
from contextlib import contextmanager
from .settings import DATA

@contextmanager
def connect():
    db = sqlite3.connect(DATA / 'imageshield.sqlite', timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA busy_timeout=15000')
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()

def init():
    with connect() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY, owner TEXT NOT NULL, geometry TEXT NOT NULL, original TEXT, clean TEXT, mask_id TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY, owner TEXT NOT NULL, asset_id TEXT NOT NULL, path TEXT NOT NULL, kind TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, owner TEXT NOT NULL, asset_id TEXT NOT NULL, kind TEXT NOT NULL, config TEXT NOT NULL, state TEXT NOT NULL, stage TEXT NOT NULL, completed_steps INTEGER, total_steps INTEGER, created REAL, updated REAL, heartbeat REAL, cancel_requested INTEGER DEFAULT 0, output TEXT, error_code TEXT, error_message TEXT);
        CREATE TABLE IF NOT EXISTS experiments(id TEXT PRIMARY KEY, owner TEXT NOT NULL, asset_id TEXT NOT NULL, config TEXT NOT NULL, pairs TEXT NOT NULL, review TEXT, effectiveness TEXT DEFAULT 'not_tested');
        CREATE TABLE IF NOT EXISTS worker_status(id INTEGER PRIMARY KEY CHECK(id=1), heartbeat REAL, pid INTEGER);
        ''')

def one(sql, params=()):
    with connect() as db:
        row = db.execute(sql, params).fetchone()
        return dict(row) if row else None

def all_rows(sql, params=()):
    with connect() as db:
        return [dict(r) for r in db.execute(sql, params).fetchall()]

def execute(sql, params=()):
    with connect() as db:
        db.execute(sql, params)
