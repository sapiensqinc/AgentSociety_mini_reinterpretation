"""Security utilities: BYOK enforcement, rate limiting, input validation, error sanitization.

Hardening pillars (aligned with OWASP Top 10 for LLM Applications 2025):
1. LLM01 Prompt Injection — spotlighting (delimiter + datamarking), extended patterns,
   invisible-character stripping (Unicode Tags, ZWJ, bidi).
2. LLM02 Sensitive Information Disclosure — output filtering before Streamlit render.
3. LLM05 Improper Output Handling — HTML tag / external image / non-HTTPS link removal.
4. LLM10 Unbounded Consumption — session token + cost ceiling on top of request rate limit.
5. BYOK — key kept only in `st.session_state`; never persisted, logged, or echoed.
6. Path traversal — profile JSON loading gated behind allowlist + is_relative_to check.

References:
- OWASP Top 10 for LLM 2025          https://genai.owasp.org/llm-top-10/
- Spotlighting (Hines et al. 2024)   https://arxiv.org/abs/2403.14720
- Streamlit security guidance        https://docs.streamlit.io/develop/concepts/security
"""

import hashlib
import json
import re
import time
from pathlib import Path

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


# ── Token / cost ceiling (LLM10 Unbounded Consumption) ───────────────────────
# Stops malicious users from burning the BYOK key with a few large-payload calls.

TOKEN_BUDGET_PER_SESSION = 500_000   # input+output combined
COST_ABORT_USD = 2.00                # approximate, user can override per-provider

# Per-1K-token pricing (USD). Very rough — update when pricing changes.
_DEFAULT_RATES_USD_PER_1K = {
    "gemini-2.5-flash": 0.00030,
    "gemini-2.5-pro": 0.00500,
    "gpt-4.1": 0.00200,
    "claude-sonnet-4-7": 0.00300,
    "mistral-small": 0.00020,
    "default": 0.00100,
}


def _rate_for(model: str) -> float:
    model = (model or "default").lower()
    for key, rate in _DEFAULT_RATES_USD_PER_1K.items():
        if key in model:
            return rate
    return _DEFAULT_RATES_USD_PER_1K["default"]


def account_tokens(input_tokens: int, output_tokens: int, model: str = "default") -> None:
    """Accumulate token usage + cost on the session. Raises if budget exceeded.

    Call this from the LLM wrapper AFTER every successful completion (or estimate
    when exact counts are unavailable).
    """
    rate = _rate_for(model)
    used = st.session_state.get("_tok_used", 0) + input_tokens + output_tokens
    cost = st.session_state.get("_cost_usd", 0.0) + (input_tokens + output_tokens) / 1000 * rate
    st.session_state["_tok_used"] = used
    st.session_state["_cost_usd"] = cost
    if used > TOKEN_BUDGET_PER_SESSION:
        raise RuntimeError(
            f"Session token budget exceeded ({used:,} > {TOKEN_BUDGET_PER_SESSION:,}). "
            "Refresh to reset."
        )
    if cost > COST_ABORT_USD:
        raise RuntimeError(
            f"Session cost ceiling exceeded (~${cost:.2f} > ${COST_ABORT_USD:.2f}). "
            "Refresh to reset."
        )


def token_usage_summary() -> dict[str, float]:
    return {
        "tokens": st.session_state.get("_tok_used", 0),
        "cost_usd": st.session_state.get("_cost_usd", 0.0),
    }


# ── Input validation (LLM01 Prompt Injection) ────────────────────────────────
MAX_INPUT_LEN = 2000

# Invisible / control ranges used in indirect prompt injection.
_INVISIBLE_RANGES = [
    (0x00E0000, 0x00E007F),  # Unicode Tags (Willison invisible prompt)
    (0x0200B, 0x0200F),      # Zero-width space/joiner/LTR-RTL mark
    (0x0202A, 0x0202E),      # Bidi override
    (0x02066, 0x02069),      # Bidi isolate
    (0x0FFF9, 0x0FFFB),      # Interlinear annotation anchors
]


def strip_invisible(text: str) -> str:
    """Remove invisible Unicode characters that carry hidden prompt payloads."""
    def ok(ch: str) -> bool:
        cp = ord(ch)
        return not any(lo <= cp <= hi for lo, hi in _INVISIBLE_RANGES)
    return "".join(ch for ch in text if ok(ch))


_INJECTION_PATTERNS = [
    # ChatML / Llama / structured role tokens
    r"<\|(system|assistant|user|im_start|im_end)\|>",
    r"\[/?INST\]",
    r"###\s*(System|Instruction|Human|Assistant):",
    # Role-takeover attempts
    r"(?i)\b(ignore|disregard|forget)\b.{0,40}\b(previous|prior|above|system)\b.{0,40}\b(instruction|prompt|rule)s?\b",
    r"(?i)you\s+are\s+now\s+(a\s+)?(dan|developer\s+mode|jailbr[eo]ken|unrestricted)",
    r"(?i)\b(reveal|print|output|echo|show)\b.{0,40}\b(system|initial|hidden)\b.{0,20}prompt",
    # Encoding bypass
    r"(?i)base64[:\s]+[A-Za-z0-9+/=]{40,}",
    # Tool-call spoofing
    r"(?i)<tool_call>|<function_call>|\bfunction\.call\(",
]

# Spotlighting delimiters — see Hines et al. 2024
USER_DELIM_OPEN = "<<<USER_CONTENT_BEGIN>>>"
USER_DELIM_CLOSE = "<<<USER_CONTENT_END>>>"


def sanitize_user_input(text: str, max_len: int = MAX_INPUT_LEN) -> str:
    """Sanitize user-supplied text before sending to LLM.

    - Truncates to max_len
    - Strips control and invisible characters (Unicode Tags, bidi, ZWJ, …)
    - Raises ValueError on role-takeover / structured-prompt injection patterns
    """
    if not isinstance(text, str):
        return ""
    text = text[:max_len]
    text = strip_invisible(text)
    text = "".join(ch for ch in text if ch in ("\n", "\t") or ord(ch) >= 32)
    for pat in _INJECTION_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            raise ValueError("Input contains disallowed formatting tokens.")
    return text


def spotlight(user_text: str) -> str:
    """Wrap untrusted user text with delimiters; strip caller's own delimiter tokens.

    The system prompt should instruct the model to treat content between the
    delimiters as DATA — never as instructions. See app README § security.
    """
    cleaned = user_text.replace(USER_DELIM_OPEN, "").replace(USER_DELIM_CLOSE, "")
    cleaned = strip_invisible(cleaned)
    return f"{USER_DELIM_OPEN}\n{cleaned}\n{USER_DELIM_CLOSE}"


# ── Output filtering (LLM02 / LLM05) ─────────────────────────────────────────
_MD_IMG_ANY = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_MD_LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)]+)\)")
_HTML_TAG = re.compile(r"<[^>]+>")


def sanitize_llm_output(text: str) -> str:
    """Filter LLM output before rendering to Streamlit.

    - Removes HTML tags (double-defense on top of unsafe_allow_html=False).
    - Removes inline images entirely (blocks SSRF / tracking pixels).
    - Drops non-HTTPS markdown links.
    - Scrubs anything that looks like an echoed system prompt delimiter.
    """
    if not isinstance(text, str):
        return ""
    for needle in ("SYSTEM:", USER_DELIM_OPEN, USER_DELIM_CLOSE):
        text = text.replace(needle, "")
    text = _HTML_TAG.sub("", text)
    text = _MD_IMG_ANY.sub("", text)

    def _link(m: re.Match[str]) -> str:
        url = m.group(1)
        if not url.startswith("https://"):
            # Keep the visible label, drop the unsafe target
            return re.sub(r"\]\([^)]+\)$", "]", m.group(0))
        return m.group(0)

    text = _MD_LINK.sub(_link, text)
    return text


# ── Parameter caps (DoS prevention) ──────────────────────────────────────────
PARAM_CAPS = {
    "agents": 20,
    "rounds": 5,
    "steps": 20,
    "cot_depth": 3,
    "num_routers": 3,
}


def cap(name: str, value: int) -> int:
    limit = PARAM_CAPS.get(name)
    if limit is None:
        return value
    return min(int(value), limit)


# ── Error sanitization ───────────────────────────────────────────────────────
_SECRET_PATTERNS = [
    (re.compile(r"AIza[a-zA-Z0-9_-]{35}"), "<redacted:gemini>"),
    (re.compile(r"sk-ant-[a-zA-Z0-9_-]{20,}"), "<redacted:anthropic>"),
    (re.compile(r"sk-[a-zA-Z0-9_-]{20,}"), "<redacted:openai>"),
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
    st.error(f"{context}: {sanitize_error(exc)}")


# ── BYOK enforcement ─────────────────────────────────────────────────────────
def require_byok() -> bool:
    """Check that the user has provided their own API key."""
    key = st.session_state.get("api_key", "").strip()
    if not key:
        st.warning(
            "**Gemini API Key가 필요합니다.** 이 앱은 사용자 본인의 API Key로만 동작합니다 (BYOK).\n\n"
            "사이드바에서 Gemini API Key를 입력하세요. "
            "[Google AI Studio](https://aistudio.google.com/apikey)에서 무료로 발급받을 수 있습니다."
        )
        return False
    if not re.match(r"^AIza[a-zA-Z0-9_-]{35}$", key):
        st.warning(
            "입력된 API Key의 형식이 올바르지 않습니다. Gemini API Key는 보통 `AIza`로 시작하는 39자 문자열입니다."
        )
        return False
    return True


def ready_to_run(tag: str = "default") -> bool:
    """Single gate for a page: BYOK + rate limit. Token budget is checked per call."""
    if not require_byok():
        return False
    if not enforce_rate_limit(tag):
        return False
    return True


# ── Idle-purge: drop the BYOK key after N minutes of inactivity ──────────────
IDLE_PURGE_SEC = 1800


def touch_activity() -> None:
    """Record activity; purge the BYOK key if idle threshold crossed."""
    now = time.time()
    last = st.session_state.get("_last_activity", now)
    if now - last > IDLE_PURGE_SEC:
        st.session_state.pop("api_key", None)
    st.session_state["_last_activity"] = now


# ── Path traversal prevention for profile JSON loads ─────────────────────────
_PROFILE_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


def safe_profile_path(name: str, base_dir: Path) -> Path:
    """Resolve a profile JSON path safely.

    - Name must match allowlist regex.
    - Resolved path must stay inside the trusted base directory.
    Raises ValueError on any failure.
    """
    if not _PROFILE_NAME_RE.match(name or ""):
        raise ValueError("Invalid profile name")
    base_dir = base_dir.resolve()
    candidate = (base_dir / f"{name}.json").resolve()
    if not candidate.is_relative_to(base_dir):
        raise ValueError("Path traversal detected")
    return candidate


def load_profile_json(name: str, base_dir: Path) -> dict:
    """Safely load a profile JSON, enforcing path + shape constraints."""
    path = safe_profile_path(name, base_dir)
    if not path.is_file():
        raise FileNotFoundError(f"Profile not found: {name}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Profile must be a JSON object")
    return data


# ── Key-bucket for rate limiting across tabs using the same key ──────────────
def key_bucket(api_key: str) -> str:
    """Stable, non-reversible identifier for a key — used in rate-limit buckets."""
    return hashlib.sha256((api_key or "").encode()).hexdigest()[:16]
