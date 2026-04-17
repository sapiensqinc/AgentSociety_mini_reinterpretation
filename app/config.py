"""Shared configuration and session state management.

Security model:
- No server-side API key is ever loaded or used in deployed environments.
- Users MUST provide their own Gemini API key (BYOK - Bring Your Own Key).
- The key is stored only in Streamlit session_state (per-user, in-memory).
"""

import os
import pickle
import sys
import streamlit as st
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _drop_unpicklable_values() -> list[str]:
    """Remove any session_state entries that can't survive Streamlit's
    `maybe_check_serializable()` so a stale local-class instance left by a
    previous deploy can't break every subsequent page navigation.
    Returns the list of keys that were dropped (for optional surfacing).
    """
    dropped = []
    for key in list(st.session_state.keys()):
        # Skip Streamlit internal keys (prefixed by underscore or magic)
        if key.startswith("_") or key.startswith("FormSubmitter:"):
            continue
        try:
            pickle.dumps(st.session_state[key])
        except Exception:
            try:
                del st.session_state[key]
            except Exception:
                pass
            dropped.append(key)
    return dropped


def init_session():
    # Clean up stale un-picklable values BEFORE Streamlit's end-of-run
    # serialization check would trigger UnserializableSessionStateError.
    # Safe to run on every rerun: primitives pickle in microseconds.
    _drop_unpicklable_values()

    defaults = {
        "api_key": "",
        "chat_history": [],
        "experiment_results": {},
        "current_page": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def get_api_key() -> str:
    """Return the user's Gemini API key from session state only."""
    return st.session_state.get("api_key", "")


def set_api_key(key: str):
    """Set the user's Gemini API key.

    Stored only in session_state (not persisted to disk, never logged).
    Also sets GEMINI_API_KEY env var for the agentsociety2_lite client,
    scoped to this Python process only.
    """
    key = (key or "").strip()
    st.session_state["api_key"] = key
    if key:
        os.environ["GEMINI_API_KEY"] = key
    else:
        os.environ.pop("GEMINI_API_KEY", None)


def require_api_key() -> bool:
    """Legacy wrapper for backward compatibility. Use security.require_byok()."""
    from app.security import require_byok
    return require_byok()


def clear_chat():
    st.session_state["chat_history"] = []
