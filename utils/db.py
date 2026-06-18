"""
db.py — 資料存取層
USE_LOCAL=true  → SQLite（本地測試，不需 Supabase）
USE_LOCAL=false → Supabase（生產環境）
在 .streamlit/secrets.toml 設定 USE_LOCAL
"""
from __future__ import annotations
import os, sqlite3, json
from pathlib import Path
from typing import Any
import streamlit as st

TABLES = {
    "purchases": "ims_purchases",
    "sales":     "ims_sales",
    "expenses":  "ims_expenses",
    "scraps":    "ims_scraps",
    "products":  "ims_products",
}

_LOCAL_DB = Path(__file__).parent.parent / "data" / "local.db"

# ── 判斷模式 ─────────────────────────────────────────────────────────────────

def _use_local() -> bool:
    try:
        return str(st.secrets.get("USE_LOCAL", "true")).lower() == "true"
    except Exception:
        return True


# ══════════════════════════════════════════════════════════════════════════════
# SQLite 後端
# ══════════════════════════════════════════════════════════════════════════════

_AUDIT_TABLE = "ims_audit_log"

_SCHEMAS = {
    _AUDIT_TABLE: """
        CREATE TABLE IF NOT EXISTS ims_audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name  TEXT NOT NULL,
            row_id      INTEGER,
            action      TEXT NOT NULL,
            changed_at  TEXT DEFAULT (datetime('now','localtime')),
            old_data    TEXT,
            new_data    TEXT
        )""",
    "ims_products": """
        CREATE TABLE IF NOT EXISTS ims_products (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            code       TEXT UNIQUE,
            name       TEXT NOT NULL,
            ref_price  REAL DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now'))
        )""",
    "ims_purchases": """
        CREATE TABLE IF NOT EXISTS ims_purchases (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            year         INTEGER NOT NULL,
            period       INTEGER NOT NULL,
            date         TEXT,
            invoice_type TEXT,
            invoice_no   TEXT,
            code         TEXT,
            product_name TEXT,
            unit_price   REAL,
            qty          REAL,
            vendor_name  TEXT,
            vendor_tax   TEXT,
            amount       REAL,
            source_sheet TEXT,
            imported_at  TEXT DEFAULT (datetime('now'))
        )""",
    "ims_sales": """
        CREATE TABLE IF NOT EXISTS ims_sales (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            year           INTEGER NOT NULL,
            period         INTEGER NOT NULL,
            machine_no     TEXT,
            date           TEXT,
            invoice_no     TEXT,
            code           TEXT,
            product_name   TEXT,
            qty            REAL,
            untaxed_amount REAL,
            imported_at    TEXT DEFAULT (datetime('now'))
        )""",
    "ims_expenses": """
        CREATE TABLE IF NOT EXISTS ims_expenses (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            year         INTEGER NOT NULL,
            period       INTEGER NOT NULL,
            date         TEXT,
            invoice_type TEXT,
            invoice_no   TEXT,
            content      TEXT,
            vendor_name  TEXT,
            vendor_tax   TEXT,
            amount       REAL,
            imported_at  TEXT DEFAULT (datetime('now'))
        )""",
    "ims_scraps": """
        CREATE TABLE IF NOT EXISTS ims_scraps (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            year         INTEGER NOT NULL,
            period       INTEGER NOT NULL,
            date         TEXT,
            code         TEXT,
            product_name TEXT,
            qty          REAL,
            reason       TEXT,
            loss         REAL,
            note         TEXT,
            imported_at  TEXT DEFAULT (datetime('now'))
        )""",
}


def _get_conn() -> sqlite3.Connection:
    _LOCAL_DB.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(_LOCAL_DB))
    conn.row_factory = sqlite3.Row
    for ddl in _SCHEMAS.values():
        conn.execute(ddl)
    conn.commit()
    return conn


def _sqlite_fetch(table: str, filters: dict | None = None) -> list[dict]:
    conn = _get_conn()
    sql = f"SELECT * FROM {table}"
    params: list = []
    if filters:
        clauses = [f"{k} = ?" for k, v in filters.items() if v is not None]
        params  = [v for v in filters.values() if v is not None]
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _sqlite_insert_batch(table: str, rows: list[dict]) -> None:
    if not rows:
        return
    conn = _get_conn()
    cols = list(rows[0].keys())
    placeholders = ", ".join("?" * len(cols))
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
    conn.executemany(sql, [[r.get(c) for c in cols] for r in rows])
    conn.commit()
    conn.close()


def _sqlite_delete(table: str, filters: dict) -> None:
    conn = _get_conn()
    clauses = [f"{k} = ?" for k in filters]
    params  = list(filters.values())
    conn.execute(f"DELETE FROM {table} WHERE {' AND '.join(clauses)}", params)
    conn.commit()
    conn.close()


def _sqlite_update(table: str, row_id: int, data: dict) -> None:
    conn = _get_conn()
    sets   = ", ".join(f"{k} = ?" for k in data)
    params = list(data.values()) + [row_id]
    conn.execute(f"UPDATE {table} SET {sets} WHERE id = ?", params)
    conn.commit()
    conn.close()


def _sqlite_count(table: str, year: int, period: int) -> int:
    conn = _get_conn()
    row = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE year=? AND period=?", (year, period)
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def _sqlite_years() -> list[int]:
    conn = _get_conn()
    rows = conn.execute("SELECT DISTINCT year FROM ims_sales ORDER BY year DESC").fetchall()
    years = [r[0] for r in rows]
    if not years:
        rows = conn.execute("SELECT DISTINCT year FROM ims_purchases ORDER BY year DESC").fetchall()
        years = [r[0] for r in rows]
    conn.close()
    return years


def _sqlite_upsert_product(code: str, name: str, ref_price: float) -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT INTO ims_products (code, name, ref_price) VALUES (?,?,?) "
        "ON CONFLICT(code) DO UPDATE SET name=excluded.name, ref_price=excluded.ref_price",
        (code, name, ref_price),
    )
    conn.commit()
    conn.close()


def _sqlite_upsert_products_batch(rows: list[dict]) -> None:
    """匯入品項主表：新增時 ref_price=0，已存在只更新 name，保留手動設定的 ref_price。"""
    if not rows:
        return
    conn = _get_conn()
    conn.executemany(
        "INSERT INTO ims_products (code, name, ref_price) VALUES (?,?,0) "
        "ON CONFLICT(code) DO UPDATE SET name=excluded.name",
        [(r["code"], r["name"]) for r in rows],
    )
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Supabase 後端
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def _get_supabase():
    from supabase import create_client
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def _supa_fetch(table: str, filters: dict | None = None) -> list[dict]:
    db = _get_supabase()
    q = db.table(table).select("*")
    if filters:
        for col, val in filters.items():
            if val is not None:
                q = q.eq(col, val)
    return q.order("id").execute().data


def _supa_insert_batch(table: str, rows: list[dict], batch_size: int = 500) -> None:
    db = _get_supabase()
    for i in range(0, len(rows), batch_size):
        db.table(table).insert(rows[i : i + batch_size]).execute()


# ══════════════════════════════════════════════════════════════════════════════
# 公開 API（頁面呼叫這些函式，不在乎底層是哪個資料庫）
# ══════════════════════════════════════════════════════════════════════════════

def fetch_all(table: str, filters: dict | None = None) -> list[dict]:
    if _use_local():
        return _sqlite_fetch(table, filters)
    return _supa_fetch(table, filters)


def fetch_years() -> list[int]:
    if _use_local():
        return _sqlite_years()
    db = _get_supabase()
    rows = db.table(TABLES["sales"]).select("year").execute().data
    years = sorted({r["year"] for r in rows}, reverse=True)
    if not years:
        rows = db.table(TABLES["purchases"]).select("year").execute().data
        years = sorted({r["year"] for r in rows}, reverse=True)
    return years


def upsert_batch(table: str, rows: list[dict], batch_size: int = 500) -> int:
    if _use_local():
        _sqlite_insert_batch(table, rows)
    else:
        _supa_insert_batch(table, rows, batch_size)
    return len(rows)


def delete_period(table: str, year: int, period: int) -> None:
    if _use_local():
        _sqlite_delete(table, {"year": year, "period": period})
    else:
        _get_supabase().table(table).delete().eq("year", year).eq("period", period).execute()


def _write_audit_log(table: str, row_id: int, action: str,
                     old_data: dict, new_data: dict) -> None:
    from datetime import datetime
    entry = {
        "table_name": table,
        "row_id":     row_id,
        "action":     action,
        "changed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "old_data":   json.dumps(old_data, ensure_ascii=False, default=str),
        "new_data":   json.dumps(new_data, ensure_ascii=False, default=str) if new_data else None,
    }
    if _use_local():
        conn = _get_conn()
        conn.execute(
            f"INSERT INTO {_AUDIT_TABLE} (table_name, row_id, action, changed_at, old_data, new_data) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (entry["table_name"], entry["row_id"], entry["action"],
             entry["changed_at"], entry["old_data"], entry["new_data"]),
        )
        conn.commit()
        conn.close()
    else:
        _get_supabase().table(_AUDIT_TABLE).insert(entry).execute()


def delete_row(table: str, row_id: int) -> None:
    old = fetch_all(table, {"id": row_id})
    old_data = old[0] if old else {}
    if _use_local():
        _sqlite_delete(table, {"id": row_id})
    else:
        _get_supabase().table(table).delete().eq("id", row_id).execute()
    _write_audit_log(table, row_id, "DELETE", old_data, {})


def delete_all(table: str) -> None:
    if _use_local():
        conn = _get_conn()
        conn.execute(f"DELETE FROM {table}")
        conn.commit()
    else:
        _get_supabase().table(table).delete().neq("id", 0).execute()


def update_row(table: str, row_id: int, data: dict) -> None:
    old = fetch_all(table, {"id": row_id})
    old_data = {k: old[0].get(k) for k in data} if old else {}
    if _use_local():
        _sqlite_update(table, row_id, data)
    else:
        _get_supabase().table(table).update(data).eq("id", row_id).execute()
    _write_audit_log(table, row_id, "UPDATE", old_data, data)


def upsert_product(code: str, name: str, ref_price: float = 0) -> None:
    if _use_local():
        _sqlite_upsert_product(code, name, ref_price)
    else:
        _get_supabase().table(TABLES["products"]).upsert(
            {"code": code, "name": name, "ref_price": ref_price}, on_conflict="code"
        ).execute()


def import_products(rows: list[dict]) -> int:
    """匯入品項主表：已存在的 code 只更新 name，不動 ref_price。回傳寫入筆數。"""
    if not rows:
        return 0
    if _use_local():
        _sqlite_upsert_products_batch(rows)
    else:
        # Supabase: upsert 只更新 name 欄位
        _get_supabase().table(TABLES["products"]).upsert(
            [{"code": r["code"], "name": r["name"]} for r in rows],
            on_conflict="code", ignore_duplicates=False
        ).execute()
    return len(rows)


def count_period(table: str, year: int, period: int) -> int:
    if _use_local():
        return _sqlite_count(table, year, period)
    db = _get_supabase()
    res = db.table(table).select("id", count="exact").eq("year", year).eq("period", period).execute()
    return res.count or 0


def clear_audit_log() -> None:
    delete_all(_AUDIT_TABLE)


def fetch_audit_log(limit: int = 500) -> list[dict]:
    if _use_local():
        conn = _get_conn()
        rows = conn.execute(
            f"SELECT * FROM {_AUDIT_TABLE} ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    else:
        res = (_get_supabase().table(_AUDIT_TABLE)
               .select("*").order("id", desc=True).limit(limit).execute())
        return res.data or []


def restore_deleted_row(log_id: int) -> bool:
    """從 audit log 還原一筆已刪除的資料，回傳是否成功。"""
    logs = []
    if _use_local():
        conn = _get_conn()
        row = conn.execute(
            f"SELECT * FROM {_AUDIT_TABLE} WHERE id=?", (log_id,)
        ).fetchone()
        conn.close()
        if row:
            logs = [dict(row)]
    else:
        res = _get_supabase().table(_AUDIT_TABLE).select("*").eq("id", log_id).execute()
        logs = res.data or []

    if not logs or logs[0]["action"] != "DELETE":
        return False

    old_data = json.loads(logs[0]["old_data"])
    old_data.pop("id", None)
    table = logs[0]["table_name"]
    upsert_batch(table, [old_data])
    return True
