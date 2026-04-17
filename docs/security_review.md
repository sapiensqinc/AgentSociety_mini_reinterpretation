# Security Review

Two-part review:
1. Dependency supply-chain audit (original doc)
2. Application-level audit of the agent framework, Streamlit UI, and GIF recorder/viewer (2026-04-17)

---

## 1. Dependencies

### Summary

Removed the original `agentsociety2`'s `litellm` dependency and replaced it with
`google-genai`. Python 3.14 compatible + security-hardened.

### Package-by-Package Assessment

| Package | Status | Notes |
|---------|:------:|-------|
| **google-genai** | SAFE | Maintained by Google. Thin API client. No known CVE |
| **pydantic** | SAFE | Widely adopted, Rust core (v2). No known CVE |
| **json-repair** | CAUTION | Single maintainer. No CVE but limited community review. Pin versions |
| **python-dotenv** | SAFE | Simple, mature, widely used. Ensure `.env*` is gitignored |
| **sqlalchemy** | SAFE | Industry-standard ORM. Safe when parameterized queries are used |
| **aiohttp** | CAUTION | HTTP complexity has produced CVEs before. Keep updated |
| **streamlit** | CAUTION | Past XSS / path-traversal CVEs. Deploy with care. Pin + update |
| **plotly** | SAFE | Client-side chart generation. Minimal attack surface |
| **pyvis** | CAUTION | Small community, infrequent updates. Maintenance risk |
| **playwright** | SAFE | Browser automation, used only by scripts/record_gifs.py; never in the deployed app |
| **pillow / imageio** | CAUTION | Image parsers have had CVEs historically. Keep updated |

### LLM SDK Comparison

| Criterion | google-genai | openai | litellm |
|-----------|:---:|:---:|:---:|
| Maintainer | Google | OpenAI | BerriAI (small) |
| Known CVE | none | none | **Supply-chain compromise (2026-03)** |
| Attack surface | thin API client | thin API client | Wraps 100+ providers, wide surface |
| Verdict | **SAFE** | **SAFE** | **RISKY** |

#### litellm incident

- **Date**: 2026-03-24
- **Actor**: TeamPCP
- **Path**: Tampered Trivy GitHub Action tag → stolen PyPI token from CI → malicious `litellm` builds
- **Infected versions**: 1.82.7, 1.82.8
- **Payload**: `.pth` file auto-executed on Python startup, exfiltrated env vars (API keys, cloud credentials)
- **Impact**: 40-minute window, 40 000+ downloads

#### Decision: remove litellm entirely

`agentsociety2` uses `litellm` as a core dependency, so the lightweight
reinterpretation (`agentsociety2_lite`) **drops litellm completely** and calls
`google-genai` directly.

---

## 2. Application-level audit (2026-04-17)

Covers the Python core (`agentsociety2_lite/`), the Streamlit app (`app/`, `run.py`),
the recorder (`scripts/record_gifs.py`), and the timeline viewer (`gifs/viewer.html`).

### 2.1 Code execution / dangerous sinks

| Sink | Present? | Notes |
|------|:--------:|-------|
| `exec`, `eval`, `compile` | no | grep-verified across all `.py` |
| `os.system`, `subprocess(shell=True)` | no | grep-verified |
| `pickle.loads`, `yaml.load` (unsafe) | no | grep-verified |
| `__import__` with user input | no | only stdlib imports |

**CodeGenRouter note**: despite its name, `router_codegen.py` uses Gemini's
structured function-calling API, **not** `exec()` on LLM output. Tool dispatch
is gated by two checks (`getattr(method, "_is_tool", False)` and a method
name-resolution that returns `None` for anything that isn't a decorated
method), so the LLM cannot invoke arbitrary Python methods.

### 2.2 Secret handling

- `.env.local` is gitignored via `.env.*` + `!.env.example`. Verified that no
  `AIza[A-Za-z0-9_-]{35}` substring exists anywhere in the tracked tree or git
  history.
- In deployed (Streamlit Cloud) mode no `.env*` files are present; the key
  comes from the user's browser session only. `app/config.set_api_key()`
  stores the key in `st.session_state` and scopes `GEMINI_API_KEY` to the
  current process's `os.environ` — never persisted to disk.
- `app/security.sanitize_error()` redacts Gemini / OpenAI / Anthropic / GitHub
  key patterns, as well as Windows and POSIX absolute paths, from error
  messages shown to the user.
- Recorded GIF frames: the API key input is a `type="password"` field, so the
  rendered characters are bullets and never visible in screenshots.

### 2.3 User input → LLM (prompt injection mitigation)

`app/security.sanitize_user_input()`:
- Caps input length to `MAX_INPUT_LEN = 2000`.
- Strips ASCII control characters (keeps `\n`, `\t`).
- Rejects inputs that contain obvious prompt-scaffold tokens
  (`<|system|>`, `[INST]`, `### System:` etc.) — a *shallow* filter, paired
  with Gemini's own `BLOCK_MEDIUM_AND_ABOVE` safety categories.

Defense in depth, not a guarantee. Prompt injection cannot be prevented
absolutely; the blast radius is limited by the fact that tools are typed,
read-only-by-default, and the LLM cannot execute arbitrary Python.

### 2.4 Resource exhaustion / DoS

- Per-session rate limits (`security.check_rate_limit`): 20 req/min, 100 req/h,
  tagged per scenario so abusing one page doesn't quietly starve another.
- Simulation parameter caps (`security.cap`):
  `agents ≤ 20`, `rounds ≤ 5`, `steps ≤ 20`, `cot_depth ≤ 3`,
  `num_routers ≤ 3`. These bound the number of LLM calls per run.
- `MAX_OUTPUT_TOKENS = 2048` in `llm/client.py` bounds each individual call.

Limitation: session-state counters reset if a user opens a new browser
session. For a public deployment, a server-side counter keyed by IP or API
key would be required.

### 2.5 LLM output safety

- `_safety_settings()` in `llm/client.py` sets `BLOCK_MEDIUM_AND_ABOVE` for
  harassment, hate speech, sexually explicit, and dangerous content.
- `MAX_OUTPUT_TOKENS = 2048` limits cost and stops runaway generation.

### 2.6 SQL (replay writer)

`agentsociety2_lite/storage/replay_writer.py` uses parameterized queries
(`?` placeholders) — no SQL injection. `db_path` is hardcoded to
`example_replay.db` in the replay page, never user-controlled.

### 2.7 HTML timeline viewer (`gifs/viewer.html`)

Hardening applied 2026-04-17:
- No `innerHTML` — sidebar items built via `createElement` / `textContent`,
  so a malicious `manifest.json` cannot inject markup or script.
- Meta `Content-Security-Policy` header: `default-src 'self'`, `img-src 'self' data:`,
  `connect-src 'self'`, `base-uri 'self'`, `form-action 'none'`. (`frame-ancestors`
  cannot be set via `<meta>` — deploy behind a reverse proxy that sets the
  response header if embedding protection is needed.)
- `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`.
- Frame filenames and slugs are validated against strict allowlists
  (`[A-Za-z0-9_\-.]+` and `category/name`) before being used in URLs — path
  traversal (`../`), absolute paths, and `javascript:` / `data:` URLs in
  manifest entries are rejected.
- `meta_path` from the manifest is ignored; the actual URL is always
  rebuilt from the validated `slug`.
- Numeric fields (`fps`, `total_seconds`, `timestamps`) are bounded and
  checked with `Number.isFinite` before being formatted.

### 2.8 Streamlit deployment

- BYOK enforced (`security.require_byok`): regex-validated key,
  session-scoped only.
- `st.session_state` may contain non-picklable values (e.g. the custom_env
  `WeatherEnvironment` class). Streamlit's serializable-session-state check
  surfaces this as a user-visible error. For CI/recorder runs we open a
  fresh browser context per scenario to isolate state — see
  `scripts/record_gifs.py`.
- `.streamlit/config.toml` should set `enableCORS=false`, `enableXsrfProtection=true`
  (the defaults in recent Streamlit versions) — verify on each deploy.

### 2.9 Recorder (`scripts/record_gifs.py`)

- Loads the API key from `.env.local` — never from user-controllable sources.
- Runs `playwright install chromium` out-of-band; the browser process has no
  access to the local environment other than what Playwright exposes.
- Each scenario runs in a fresh browser context so session_state does not
  leak across recordings (fix for the `UnserializableSessionStateError`
  observed when `custom_env`'s `WeatherEnvironment` polluted later
  scenarios).

---

## 3. Recommendations

| # | Recommendation | Owner |
|---|----------------|-------|
| 1 | Keep secrets in `.env.local` only. Never commit `.env`. Verified via `git check-ignore` | dev |
| 2 | Pin all deps with `>=` + a major-version upper bound (done in `requirements.txt`) | dev |
| 3 | Run `pip audit` / `safety check` before each release | dev |
| 4 | For a public Streamlit deployment: add auth middleware + server-side rate limit (session counters alone are bypassable) | deploy |
| 5 | For a public viewer deployment: set `frame-ancestors 'none'` as a real HTTP header | deploy |
| 6 | Review `.env.example` before each commit to ensure no live key has been pasted | dev |
| 7 | Treat LLM output as untrusted user data when rendering it (Streamlit's Markdown rendering is safe by default; avoid `unsafe_allow_html`) | dev |
