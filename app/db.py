import os
import logging
from pathlib import Path
import mysql.connector
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("db_layer")

def _load_env():
    env_vars = {
        "DB_HOST": "localhost",
        "DB_PORT": "3306",
        "DB_USER": "root",
        "DB_PASSWORD": "",
        "DB_NAME": "research_collaboration_db"
    }
    # Look for .env in current directory or parent directory
    env_paths = [Path(".env"), Path("../.env"), Path(__file__).resolve().parent.parent / ".env"]
    for p in env_paths:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env_vars[k.strip()] = v.strip()
            break
    # Allow os.environ overrides
    for k in env_vars:
        if k in os.environ:
            env_vars[k] = os.environ[k]
    return env_vars

def get_connection():
    cfg = _load_env()
    return mysql.connector.connect(
        host=cfg["DB_HOST"],
        port=int(cfg["DB_PORT"]),
        user=cfg["DB_USER"],
        password=cfg["DB_PASSWORD"],
        database=cfg["DB_NAME"],
        autocommit=True
    )

def query(sql: str, params=None) -> pd.DataFrame:
    """Execute a parameterized SELECT query and return results as a pandas DataFrame."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        return pd.DataFrame(rows)
    finally:
        conn.close()

def execute(sql: str, params=None):
    """Execute a parameterized INSERT/UPDATE/DELETE statement."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def call_proc(name: str, args=None) -> pd.DataFrame:
    """Execute a stored procedure and return first result set as a pandas DataFrame."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.callproc(name, args or ())
        rows = []
        for result in cur.stored_results():
            rows = result.fetchall()
            break
        return pd.DataFrame(rows)
    finally:
        conn.close()

def friendly_error(exc: Exception) -> str:
    """Map database errors to user-friendly messages without leaking tracebacks."""
    logger.error("Database operation failed: %s", exc)
    if isinstance(exc, mysql.connector.Error):
        errno = exc.errno
        msg = str(exc.msg) if hasattr(exc, "msg") else str(exc)
        if errno == 1062:
            return "This record already exists."
        elif errno in (1451, 1452):
            return "Referenced record missing or still in use."
        elif "A paper cannot cite itself" in msg or (hasattr(exc, "sqlstate") and exc.sqlstate == "45000"):
            return "A paper cannot cite itself."
        else:
            return f"Database error occurred (Code {errno}). Please check your input."
    return "An unexpected error occurred. Please try again."
