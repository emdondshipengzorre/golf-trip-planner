"""基础设施：HTTP session、缓存、API 密钥管理"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from pathlib import Path

import requests
import streamlit as st

CACHE_DB = Path(__file__).parent.parent / "data" / "cache.db"

logger = logging.getLogger("scraper")

# ─── HTTP Session（连接池复用） ───

_session = None


def get_session() -> requests.Session:
    """获取复用的 HTTP Session"""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
        })
    return _session


def fetch_json(url: str, headers: dict = None, method: str = "GET",
               params: dict = None, json_data: dict = None,
               timeout: int = 15) -> dict | None:
    """统一的 JSON API 请求方法"""
    session = get_session()
    try:
        if method.upper() == "POST":
            resp = session.post(url, headers=headers, json=json_data, timeout=timeout)
        else:
            resp = session.get(url, headers=headers, params=params, timeout=timeout)

        if resp.status_code == 200:
            return resp.json()

        logger.warning(f"HTTP {resp.status_code} for {url}")
        return None

    except (requests.RequestException, ValueError) as e:
        logger.warning(f"Request error for {url}: {e}")
        return None


# ─── 缓存 ───

def _init_cache():
    CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CACHE_DB)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT,
            expires_at REAL
        )"""
    )
    conn.commit()
    return conn


def cache_get(key: str) -> dict | None:
    conn = _init_cache()
    row = conn.execute(
        "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
    ).fetchone()
    conn.close()
    if row and row[1] > time.time():
        return json.loads(row[0])
    return None


def cache_set(key: str, value, ttl_seconds: int = 14400):
    conn = _init_cache()
    conn.execute(
        "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
        (key, json.dumps(value, ensure_ascii=False), time.time() + ttl_seconds),
    )
    conn.commit()
    conn.close()


def cache_clear():
    """清除所有缓存"""
    conn = _init_cache()
    conn.execute("DELETE FROM cache")
    conn.commit()
    conn.close()


def make_cache_key(prefix: str, **kwargs) -> str:
    raw = f"{prefix}:" + json.dumps(kwargs, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


# ─── API 密钥管理 ───

def get_api_key(name: str) -> str | None:
    """从 Streamlit secrets 或环境变量获取 API 密钥"""
    try:
        return st.secrets.get(name)
    except Exception:
        import os
        return os.environ.get(name)
