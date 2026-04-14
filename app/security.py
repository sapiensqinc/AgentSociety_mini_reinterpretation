"""Security utilities: BYOK enforcement, rate limiting, input validation, error sanitization.

This module is critical for public deployment. It ensures:
1. No server-side API key is ever used (BYOK only)
2. Per-session rate limits prevent abuse
3. User input is sanitized to mitigate prompt injection
4. Simulation parameters are capped to prevent DoS
5. Error messages don't leak internals
"""

import re
import time
import streamlit as st


# ── Rate limiting (per-session) ──────────────────────────────────────────────
MAX_REQUESTS_PER_MINUTE = 20
MAX_REQUESTS_PER_HOUR = 100


def check_rate_limit(tag: str = "default") -> tuple[bool, str]:
    """Check if the current session is within rate limits.

    Returns (allowed, message). Each call counts as one request if allowed.
    """
    now = time.time()
    key = f"_rl_{tag}"
    if key not in st.session_state:
        st.session_state[key] = []

    # Clean entries older than 1 hour
    st.session_state[key] = [t for t in st.session_state[key] if now - t < 3600]

    recent_min = sum(1 for t in st.session_state[key] if now - t < 60)
    total_hr = len(st.session_state[key])

    if recent_min >= MAX_REQUESTS_PER_MINUTE:
        return False, f"Rate limit exceeded: {MAX_REQUESTS_PER_MINUTE} requests/minute. Please wait."
    if total_hr >= MAX_REQUESTS_PER_HOUR:
        return False, f"Rate limit exceeded: {MAX_REQUESTS_PER_HOUR} requests/hour. Please try again later."

    st.session_state[key].append(now)
    return True, ""


def enforce_rate_limit(tag: str = "default") -> bool:
    """Show a warning if rate limit is hit. Returns True if ok to proceed."""
    allowed, msg = check_rate_limit(tag)
    if not allowed:
        st.error(msg)
        return False
    return True


# ── Input validation (prompt injection mitigation) ───────────────────────────
MAX_INPUT_LEN = 2000

_INJECTION_PATTERNS = [
    r"<\|system\|>",
    r"<\|assistant\|>",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"\[INST\]",
    r"\[/INST\]",
    r"###\s*System:",
    r"###\s*Instruction:",
]


def sanitize_user_input(text: str, max_len: int = MAX_INPUT_LEN) -> str:
    """Sanitize user-supplied text before sending to LLM.

    - Truncates to max_len
    - Strips control characters (keeps newlines/tabs)
    - Raises ValueError on obvious injection attempts
    """
    if not isinstance(text, str):
        return ""
    text = text[:max_len]
    text = "".join(
        ch for ch in text if ch in ("\n", "\t") or ord(ch) >= 32
    )
    for pat in _INJECTION_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            raise ValueError("Input contains disallowed formatting tokens.")
    return text


# ── Parameter caps (DoS prevention) ──────────────────────────────────────────
# Users can request large simulations which consume many API calls.
# These caps limit the damage of a single page load.

PARAM_CAPS = {
    "agents": 20,       # Max agents in any simulation
    "rounds": 5,        # Max rounds in games
    "steps": 20,        # Max steps in reputation/inflammatory/etc
    "cot_depth": 3,     # Max recursive CoT depth
    "num_routers": 3,   # Max routers in multi-router comparison
}


def cap(name: str, value: int) -> int:
    """Apply the configured cap for a parameter name."""
    limit = PARAM_CAPS.get(name)
    if limit is None:
        return value
    return min(int(value), limit)


# ── Error sanitization ───────────────────────────────────────────────────────

_SECRET_PATTERNS = [
    (re.compile(r"AIza[a-zA-Z0-9_-]{35}"), "<redacted:gemini>"),
    (re.compile(r"sk-[a-zA-Z0-9_-]{20,}"), "<redacted:openai>"),
    (re.compile(r"sk-ant-[a-zA-Z0-9_-]{20,}"), "<redacted:anthropic>"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "<redacted:github>"),
    (re.compile(r"[A-Za-z]:\\[^\s:*?\"<>|]+"), "<path>"),
    (re.compile(r"/[^\s:*?\"<>|]+/"), "<path>/"),
]


def sanitize_error(exc: Exception | str, max_len: int = 500) -> str:
    """Return a safe error message that doesn't expose internals."""
    msg = str(exc) if isinstance(exc, Exception) else str(exc)
    for pattern, replacement in _SECRET_PATTERNS:
        msg = pattern.sub(replacement, msg)
    return msg[:max_len]


def show_safe_error(exc: Exception, context: str = "An error occurred"):
    """Display a user-friendly error message, sanitized."""
    st.error(f"{context}: {sanitize_error(exc)}")


# ── BYOK enforcement ─────────────────────────────────────────────────────────

def require_byok() -> bool:
    """Check that the user has provided their own API key.

    Returns True if key is present in session_state. Shows a clear message if not.
    """
    key = st.session_state.get("api_key", "").strip()
    if not key:
        st.warning(
            "**Gemini API Key가 필요합니다.** 이 앱은 사용자 본인의 API Key로만 동작합니다 (BYOK).\n\n"
            "사이드바에서 Gemini API Key를 입력하세요. "
            "[Google AI Studio](https://aistudio.google.com/apikey)에서 무료로 발급받을 수 있습니다."
        )
        return False
    # Basic format check
    if not re.match(r"^AIza[a-zA-Z0-9_-]{35}$", key):
        st.warning(
            "입력된 API Key의 형식이 올바르지 않습니다. Gemini API Key는 보통 `AIza`로 시작하는 39자 문자열입니다."
        )
        return False
    return True


def ready_to_run(tag: str = "default") -> bool:
    """Single check for a page: BYOK + rate limit.

    Use this before any LLM call. Returns True if all checks pass.
    """
    if not require_byok():
        return False
    if not enforce_rate_limit(tag):
        return False
    return True
