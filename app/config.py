"""Shared configuration and session state management."""

import os
import sys
import streamlit as st
from pathlib import Path

# Add project root to path so agentsociety2_lite is importable
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def init_session():
    defaults = {
        "chat_history": [],
        "experiment_results": {},
        "current_page": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def get_api_key() -> str:
    return st.session_state.get("api_key", "")


def set_api_key(key: str):
    st.session_state["api_key"] = key
    os.environ["GEMINI_API_KEY"] = key


def require_api_key() -> bool:
    """Check if API key is set. Show warning if not. Returns True if ready."""
    if get_api_key():
        return True
    st.warning("Gemini API Key\uac00 \ud544\uc694\ud569\ub2c8\ub2e4. \uc0ac\uc774\ub4dc\ubc14\uc5d0\uc11c \uc785\ub825\ud574\uc8fc\uc138\uc694.")
    return False


def clear_chat():
    st.session_state["chat_history"] = []
