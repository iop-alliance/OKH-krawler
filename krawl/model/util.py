from __future__ import annotations

from datetime import datetime
from urllib.parse import urlunparse


def parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError("cannot parse date")


def create_url(domain: str = None, scheme: str = "https", path: str = None, params=None, query=None, fragment=None):
    return str(urlunparse((
        scheme,
        domain,
        path,
        params,
        query,
        fragment,
    )))
