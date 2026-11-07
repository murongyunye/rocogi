from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .config import DB_PATH, DEFAULT_SETTINGS, deep_merge, load_settings


def load_cli_settings(path: Optional[str] = None) -> Dict[str, Any]:
    """Load settings from a JSON file, or from the local Rocogi database."""
    if path:
        with open(path, "r", encoding="utf-8") as handle:
            return deep_merge(DEFAULT_SETTINGS, json.load(handle))
    try:
        from .storage import Database

        db = Database(DB_PATH)
        return load_settings(db)
    except Exception:
        return deep_merge(DEFAULT_SETTINGS, {})
