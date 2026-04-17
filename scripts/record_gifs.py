"""Record Streamlit scenario runs as GIFs via Playwright.

Usage:
    python scripts/record_gifs.py             # run all
    python scripts/record_gifs.py --only hello_agent
    python scripts/record_gifs.py --list
"""
import argparse
import io
import json
import os
import sys
import time
from pathlib import Path

import imageio.v3 as iio
import numpy as np
from dotenv import load_dotenv
from PIL import Image
from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env.local")
API_KEY = os.environ["GEMINI_API_KEY"]
URL = "http://localhost:8599"
OUT_DIR = ROOT / "gifs"
OUT_DIR.mkdir(exist_ok=True)


# ──────────────── helpers ────────────────

def wait_widgets(page: Page, extra_ms: int = 500, timeout_s: int = 25) -> None:
    """Wait for Streamlit skeletons and 'Running' status to clear."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if page.locator('[data-testid="stSkeleton"]').count() == 0:
            break
        page.wait_for_timeout(300)
    deadline2 = time.time() + 6
    while time.time() < deadline2:
        if page.locator('[data-testid="stStatusWidget"]').count() == 0:
            break
        page.wait_for_timeout(300)
    page.wait_for_timeout(extra_ms)


def spinner_gone(page: Page) -> bool:
    return page.locator('[data-testid="stSpinner"]').count() == 0


def page_idle(page: Page) -> bool:
    """True when Streamlit has no active rerun, spinner, skeleton, or stale block."""
    if page.locator('[data-testid="stSkeleton"]').count() > 0:
        return False
    if page.locator('[data-testid="stSpinner"]').count() > 0:
        return False
    if page.locator('[data-testid="stStatusWidget"]').count() > 0:
        return False
    if page.locator('[data-stale="true"]').count() > 0:
        return False
    # Any element containing "thinking" text (generic LLM working indicator)
    try:
        body = page.locator('[data-testid="stMain"]').first.inner_text(timeout=500).lower()
        if "thinking..." in body:
            return False
    except Exception:
        pass
    return True


def setup_page(page: Page) -> None:
    page.goto(URL, wait_until="networkidle")
    page.wait_for_selector('[data-testid="stSidebar"]', timeout=30000)
    wait_widgets(page, 500)
    key_input = page.locator('[data-testid="stSidebar"] input[type="password"]').first
    key_input.fill(API_KEY)
    key_input.press("Tab")
    wait_widgets(page, 800)


def select_category(page: Page, category: str) -> None:
    cat = page.locator('[data-testid="stSidebar"] [data-baseweb="select"]').first
    cat.click()
    page.wait_for_timeout(500)
    page.get_by_role("option", name=category).first.click()
    wait_widgets(page, 1200)


def select_example(page: Page, example_label: str) -> None:
    page.locator('[data-testid="stSidebar"]').get_by_text(example_label, exact=False).first.click()
    wait_widgets(page, 1200)


# ──────────────── recorder ────────────────

class Recorder:
    def __init__(self, page: Page, output: Path, width: int = 900, fps: float = 1.25):
        self.page = page
        self.output = output
        self.width = width
        self.fps = fps
        self.frames: list[bytes] = []
        self.timestamps: list[float] = []  # seconds since recorder start
        self.interval = 1.0 / fps
        self._last = 0.0
        self._t0 = time.time()

    def snap(self, force: bool = False) -> None:
        now = time.time()
        if force or now - self._last >= self.interval:
            self.frames.append(self.page.screenshot(type="jpeg", quality=70))
            self.timestamps.append(now - self._t0)
            self._last = now

    def scroll_reveal(self, step_px: int = 360, max_frames: int = 22, settle_ms: int = 450) -> None:
        """After a scenario completes, scroll the Streamlit main container to
        reveal results below the fold."""
        # Wait for main to exist (a recent st.rerun may have torn it down briefly)
        try:
            self.page.wait_for_selector('[data-testid="stMain"]', state="attached", timeout=5000)
        except Exception:
            return
        js_to_top = "(() => { const m = document.querySelector('[data-testid=\"stMain\"]'); if (m) m.scrollTo(0, 0); })()"
        js_step = f"(() => {{ const m = document.querySelector('[data-testid=\"stMain\"]'); if (m) m.scrollBy(0, {step_px}); }})()"
        js_y = "(() => { const m = document.querySelector('[data-testid=\"stMain\"]'); return m ? m.scrollTop : -1; })()"
        self.page.evaluate(js_to_top)
        self.page.wait_for_timeout(settle_ms)
        self.snap(force=True)
        for _ in range(max_frames):
            y_before = self.page.evaluate(js_y)
            self.page.evaluate(js_step)
            self.page.wait_for_timeout(settle_ms)
            y_after = self.page.evaluate(js_y)
            self.snap(force=True)
            if y_after == y_before:
                break

    def run_until(self, is_done, max_seconds: float = 120, tail_frames: int = 4,
                  post_tail_delay: float = 0.9, min_seconds: float = 3.0,
                  stable_polls: int = 2) -> None:
        """Take screenshots until is_done() returns True for `stable_polls` consecutive
        checks AND at least `min_seconds` has elapsed."""
        start = time.time()
        hits = 0
        while time.time() - start < max_seconds:
            self.snap()
            elapsed = time.time() - start
            if elapsed >= min_seconds and is_done():
                hits += 1
                if hits >= stable_polls:
                    break
            else:
                hits = 0
            self.page.wait_for_timeout(400)
        for _ in range(tail_frames):
            self.page.wait_for_timeout(int(post_tail_delay * 1000))
            self.snap(force=True)

    def save(self) -> None:
        if not self.frames:
            return
        # Resize in one pass so both GIF and per-frame outputs match
        resized_imgs = []
        for b in self.frames:
            im = Image.open(io.BytesIO(b)).convert("RGB")
            if self.width and im.width != self.width:
                ratio = self.width / im.width
                h = int(im.height * ratio)
                im = im.resize((self.width, h), Image.LANCZOS)
            resized_imgs.append(im)

        self.output.parent.mkdir(parents=True, exist_ok=True)

        # 1. GIF (animated)
        iio.imwrite(
            self.output,
            [np.asarray(im) for im in resized_imgs],
            plugin="pillow",
            extension=".gif",
            duration=int(1000 / self.fps),
            loop=0,
        )
        n = Image.open(self.output).n_frames

        # 2. Per-frame JPEGs for the HTML timeline viewer
        slug = self.output.stem  # e.g. "hello_agent"
        frames_dir = self.output.parent / f"{slug}_frames"
        frames_dir.mkdir(exist_ok=True)
        # Clear stale frames from a previous run of the same scenario
        for old in frames_dir.glob("*.jpg"):
            old.unlink()
        frame_files = []
        for i, im in enumerate(resized_imgs):
            fname = f"f{i:03d}.jpg"
            im.save(frames_dir / fname, format="JPEG", quality=78, optimize=True)
            frame_files.append(fname)

        # 3. Metadata json (frame list + timestamps)
        meta = {
            "slug": slug,
            "width": resized_imgs[0].width,
            "height": resized_imgs[0].height,
            "fps": self.fps,
            "frames": frame_files,
            "timestamps": [round(t, 3) for t in self.timestamps],
            "total_seconds": round(self.timestamps[-1] if self.timestamps else 0.0, 3),
        }
        (self.output.parent / f"{slug}.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        print(f"  [gif] captured {len(self.frames)}, wrote {n} frames; {len(frame_files)} raw jpg + json")


# ──────────────── scenarios ────────────────

def _click_button(page: Page, name: str, exact: bool = False):
    page.get_by_role("button", name=name, exact=exact).first.click()


def _fill_number(page: Page, label: str, value):
    """Streamlit number_input: find label then sibling input."""
    locator = page.locator(f'[data-testid="stNumberInput"]:has-text("{label}") input').first
    locator.fill(str(value))
    locator.press("Tab")


def _fill_text(page: Page, label: str, value: str):
    locator = page.locator(f'[data-testid="stTextInput"]:has-text("{label}") input').first
    locator.fill(value)
    locator.press("Tab")


def _fill_textarea(page: Page, label: str, value: str):
    locator = page.locator(f'[data-testid="stTextArea"]:has-text("{label}") textarea').first
    locator.fill(value)
    locator.press("Tab")


def _set_slider(page: Page, label: str, value):
    container = page.locator(f'[data-testid="stSlider"]:has-text("{label}")').first
    thumb = container.locator('[role="slider"]').first
    thumb.click()
    thumb.press("Home")
    page.wait_for_timeout(150)
    try:
        lo = int(container.locator('[role="slider"]').first.get_attribute("aria-valuemin") or "0")
    except Exception:
        lo = 0
    delta = int(value) - lo
    for _ in range(max(0, delta)):
        thumb.press("ArrowRight")
    page.wait_for_timeout(200)


def _set_number(page: Page, label: str, value):
    """Set a Streamlit number_input by label match (partial allowed). Scoped to main."""
    main = page.locator('[data-testid="stMain"]')
    loc = main.locator(f'[data-testid="stNumberInput"]:has-text("{label}") input').first
    loc.click()
    loc.press("Control+A")
    loc.type(str(value))
    loc.press("Enter")
    page.wait_for_timeout(400)


def _multiselect_clear_extras(page: Page, label: str, keep: int = 1):
    """Leave only `keep` tags in the multiselect widget identified by label."""
    main = page.locator('[data-testid="stMain"]')
    container = main.locator(f'[data-testid="stMultiSelect"]:has-text("{label}")').first
    # Close icons inside existing tags (BaseWeb tag has a span that acts as close)
    tags = container.locator('span[role="button"][aria-label*="Remove"], span[title*="Clear"], span[data-baseweb="tag"] span[role="button"]')
    n = tags.count()
    # Try also generic tag-close pattern
    if n == 0:
        tags = container.locator('[data-baseweb="tag"] [role="presentation"]')
        n = tags.count()
    to_remove = max(0, n - keep)
    for _ in range(to_remove):
        tags.first.click()
        page.wait_for_timeout(200)


# ---- Basics ----

def scn_hello_agent(page: Page, rec: Recorder):
    _click_button(page, "Tell me about Alice's personal...")
    rec.snap(force=True)
    rec.run_until(page_idle_factory(page), max_seconds=90, min_seconds=6, tail_frames=3)


def page_idle_factory(page: Page):
    def f():
        return page_idle(page)
    return f


def scn_custom_env(page: Page, rec: Recorder):
    rec.snap(force=True)
    main = page.locator('[data-testid="stMain"]')
    inp = main.locator('[data-testid="stTextInput"] input').first
    inp.click()
    inp.fill("What's the weather?")
    inp.press("Enter")
    page.wait_for_timeout(500)
    page.get_by_role("button", name="Execute").first.click()
    rec.run_until(page_idle_factory(page), max_seconds=120, min_seconds=6, tail_frames=5)


def scn_replay_system(page: Page, rec: Recorder):
    rec.snap(force=True)
    page.get_by_role("button", name="Run Simulation").first.click()
    rec.run_until(page_idle_factory(page), max_seconds=150, min_seconds=8, tail_frames=5)


# ---- Advanced ----

def scn_custom_agent(page: Page, rec: Recorder):
    rec.snap(force=True)
    page.get_by_role("button", name="Ask Specialist").first.click()
    rec.run_until(page_idle_factory(page), max_seconds=120, min_seconds=6, tail_frames=4)


def scn_multi_router(page: Page, rec: Recorder):
    rec.snap(force=True)
    page.get_by_role("button", name="Run All Routers").first.click()
    rec.run_until(page_idle_factory(page), max_seconds=180, min_seconds=8, tail_frames=5)


# ---- Games ----

def scn_prisoners_dilemma(page: Page, rec: Recorder):
    rec.snap(force=True)
    page.get_by_role("button", name="Run Game").first.click()
    rec.run_until(page_idle_factory(page), max_seconds=150, min_seconds=8, tail_frames=5)


def scn_public_goods(page: Page, rec: Recorder):
    try:
        _set_number(page, "Rounds", 1)
    except Exception as e:
        print("  number set skip:", e)
    rec.snap(force=True)
    page.get_by_role("button", name="Start Game").first.click()
    rec.run_until(page_idle_factory(page), max_seconds=180, min_seconds=8, tail_frames=5)


def scn_reputation_game(page: Page, rec: Recorder):
    try:
        _set_number(page, "Population (Z)", 4)
    except Exception:
        pass
    try:
        _set_slider(page, "Simulation Steps", 5)
    except Exception:
        pass
    rec.snap(force=True)
    page.get_by_role("button", name="Run Simulation").first.click()
    rec.run_until(page_idle_factory(page), max_seconds=240, min_seconds=10, tail_frames=5)


# ---- Papers ----

def scn_polarization(page: Page, rec: Recorder):
    try:
        _set_number(page, "Agents", 4)
    except Exception:
        pass
    try:
        _set_number(page, "Rounds", 1)
    except Exception:
        pass
    try:
        _multiselect_clear_extras(page, "Conditions", keep=1)
    except Exception:
        pass
    rec.snap(force=True)
    page.get_by_role("button", name="Run Experiment").first.click()
    rec.run_until(page_idle_factory(page), max_seconds=300, min_seconds=10, tail_frames=5)


def scn_inflammatory(page: Page, rec: Recorder):
    try:
        _set_number(page, "Network Size", 6)
    except Exception:
        pass
    try:
        _set_number(page, "Steps", 2)
    except Exception:
        pass
    try:
        _multiselect_clear_extras(page, "Conditions", keep=1)
    except Exception:
        pass
    rec.snap(force=True)
    page.get_by_role("button", name="Run Experiment").first.click()
    rec.run_until(page_idle_factory(page), max_seconds=300, min_seconds=10, tail_frames=5)


def scn_ubi(page: Page, rec: Recorder):
    try:
        _set_number(page, "Agents", 4)
    except Exception:
        pass
    try:
        _set_number(page, "Months", 1)
    except Exception:
        pass
    rec.snap(force=True)
    page.get_by_role("button", name="Run Experiment").first.click()
    rec.run_until(page_idle_factory(page), max_seconds=300, min_seconds=10, tail_frames=5)


def scn_hurricane(page: Page, rec: Recorder):
    try:
        _set_number(page, "Agents", 6)
    except Exception:
        pass
    rec.snap(force=True)
    page.get_by_role("button", name="Run Simulation").first.click()
    rec.run_until(page_idle_factory(page), max_seconds=360, min_seconds=10, tail_frames=5)


# ──────────────── scenario registry ────────────────

SCENARIOS = [
    ("basics/hello_agent",       "Basics",            "01. Hello Agent",             scn_hello_agent),
    ("basics/custom_env",        "Basics",            "02. Custom Environment",      scn_custom_env),
    ("basics/replay_system",     "Basics",            "03. Replay System",           scn_replay_system),
    ("advanced/custom_agent",    "Advanced",          "01. Custom Agent",            scn_custom_agent),
    ("advanced/multi_router",    "Advanced",          "02. Multi-Router",            scn_multi_router),
    ("games/prisoners_dilemma",  "Games",             "01. Prisoner's Dilemma",      scn_prisoners_dilemma),
    ("games/public_goods",       "Games",             "02. Public Goods",            scn_public_goods),
    ("games/reputation_game",    "Games",             "03. Reputation Game",         scn_reputation_game),
    ("papers/polarization",      "Paper Experiments", "Polarization",                scn_polarization),
    ("papers/inflammatory",      "Paper Experiments", "Inflammatory",                scn_inflammatory),
    ("papers/ubi",               "Paper Experiments", "UBI",                         scn_ubi),
    ("papers/hurricane",         "Paper Experiments", "Hurricane",                   scn_hurricane),
]


def _write_manifest_and_viewer() -> None:
    """Scan OUT_DIR for `<slug>.json` metadata files, write manifest.json
    and a self-contained viewer.html with a timeline player."""
    entries = []
    for slug, category, example, _ in SCENARIOS:
        meta_path = OUT_DIR / f"{slug}.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        entries.append({
            "slug": slug,
            "category": category,
            "example": example,
            "meta_path": f"{slug}.json",
            "gif_path": f"{slug}.gif",
            "frames_dir": f"{Path(slug).parent.as_posix()}/{Path(slug).name}_frames",
            "frame_count": len(meta.get("frames", [])),
            "total_seconds": meta.get("total_seconds", 0),
        })
    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps({"scenarios": entries}, indent=2), encoding="utf-8")
    print(f"\nmanifest: {len(entries)} scenarios written to {manifest_path.relative_to(ROOT)}")

    viewer_path = OUT_DIR / "viewer.html"
    viewer_path.write_text(_VIEWER_HTML, encoding="utf-8")
    print(f"viewer:   {viewer_path.relative_to(ROOT)}")


_VIEWER_HTML = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<!-- CSP: frame-ancestors cannot be set via <meta>; set that header server-side. -->
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'self'; form-action 'none';">
<meta http-equiv="X-Content-Type-Options" content="nosniff">
<meta http-equiv="Referrer-Policy" content="no-referrer">
<title>AgentSociety mini-reinterpretation — Scenario Timeline Viewer</title>
<style>
  :root { color-scheme: light dark; }
  body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", sans-serif; background: #0f1115; color: #e7e7ea; }
  header { padding: 14px 20px; border-bottom: 1px solid #23262d; display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
  header h1 { font-size: 16px; margin: 0; font-weight: 600; }
  header .sub { font-size: 12px; color: #8a8f98; }
  main { display: grid; grid-template-columns: 260px 1fr; gap: 0; min-height: calc(100vh - 55px); }
  aside { border-right: 1px solid #23262d; overflow-y: auto; background: #12151b; }
  aside h2 { font-size: 11px; letter-spacing: 1px; text-transform: uppercase; color: #8a8f98; margin: 16px 20px 6px; }
  aside .item { padding: 8px 20px; cursor: pointer; font-size: 13px; border-left: 3px solid transparent; }
  aside .item:hover { background: #1a1e26; }
  aside .item.active { background: #1e2430; border-left-color: #4f8bff; color: #fff; }
  aside .item .count { color: #8a8f98; font-size: 11px; margin-left: 6px; }
  section.player { padding: 16px 24px; overflow-y: auto; }
  .stage { max-width: 900px; }
  .frame-wrap { background: #1a1e26; border: 1px solid #23262d; border-radius: 8px; overflow: hidden; }
  .frame-wrap img { display: block; width: 100%; height: auto; }
  .controls { display: flex; gap: 10px; align-items: center; margin-top: 12px; flex-wrap: wrap; }
  button { background: #2a3142; border: 1px solid #384055; color: #e7e7ea; padding: 6px 12px; border-radius: 5px; cursor: pointer; font-size: 13px; }
  button:hover { background: #333b4e; }
  button.primary { background: #3b6fe0; border-color: #3b6fe0; }
  button.primary:hover { background: #4a7cec; }
  input[type=range] { flex: 1; accent-color: #4f8bff; }
  .meta { font-size: 12px; color: #8a8f98; margin-left: auto; }
  .scenario-title { font-size: 15px; font-weight: 600; margin: 0 0 2px; }
  .scenario-sub { font-size: 12px; color: #8a8f98; margin: 0 0 10px; }
  .speed { display: inline-flex; gap: 4px; }
  .speed button.on { background: #3b6fe0; border-color: #3b6fe0; }
  kbd { background: #2a3142; border: 1px solid #384055; border-radius: 3px; padding: 1px 5px; font-size: 11px; }
  .hint { font-size: 11px; color: #6b7380; margin-top: 10px; }
</style>
</head>
<body>
<header>
  <h1>AgentSociety Mini Reinterpretation — Scenario Timeline Viewer</h1>
  <span class="sub">좌측에서 시나리오 선택 · 재생/일시정지 · 스크러버로 자유 이동</span>
</header>
<main>
  <aside id="sidebar"></aside>
  <section class="player">
    <div class="stage">
    <div id="title-area">
      <h2 class="scenario-title" id="scn-title">시나리오를 선택하세요</h2>
      <p class="scenario-sub" id="scn-sub"></p>
    </div>
    <div class="frame-wrap"><img id="frame" alt="" /></div>
    <div class="controls">
      <button id="btn-prev" title="Prev (←)">◀</button>
      <button id="btn-play" class="primary" title="Play/Pause (Space)">▶ Play</button>
      <button id="btn-next" title="Next (→)">▶</button>
      <input type="range" id="scrub" min="0" max="0" value="0" />
      <span class="speed">
        <button data-speed="0.5">0.5×</button>
        <button data-speed="1" class="on">1×</button>
        <button data-speed="2">2×</button>
        <button data-speed="4">4×</button>
      </span>
      <span class="meta" id="meta">— / —</span>
    </div>
    <div class="hint">
      <kbd>Space</kbd> 재생/일시정지 · <kbd>←</kbd> <kbd>→</kbd> 프레임 이동 · <kbd>Home</kbd>/<kbd>End</kbd> 처음/끝 · <kbd>1</kbd>–<kbd>4</kbd> 속도
    </div>
    </div>
  </section>
</main>

<script>
(async () => {
  // --- safety helpers ----------------------------------------------------
  // Only accept category/slug/frame strings that match a strict allowlist.
  // Prevents path traversal (../), absolute paths, javascript:/data: URLs,
  // or stray characters that could escape the gifs/ directory.
  const SAFE_SEG = /^[A-Za-z0-9_\-.]+$/;        // single path segment
  const SAFE_SLUG = /^[A-Za-z0-9_\-]+\/[A-Za-z0-9_\-]+$/;  // "category/name"
  const isSafeSeg = s => typeof s === "string" && SAFE_SEG.test(s) && !s.includes("..");
  const isSafeSlug = s => typeof s === "string" && SAFE_SLUG.test(s);
  const isFiniteNum = n => typeof n === "number" && Number.isFinite(n);

  let manifest;
  try {
    manifest = await fetch("manifest.json").then(r => r.json());
  } catch (e) { console.error("manifest load failed", e); return; }

  const scenarios = (manifest.scenarios || []).filter(s =>
    s && isSafeSlug(s.slug) && typeof s.category === "string" && typeof s.example === "string"
  );

  const sidebar = document.getElementById("sidebar");
  const byCat = {};
  scenarios.forEach(s => { (byCat[s.category] ||= []).push(s); });
  Object.entries(byCat).forEach(([cat, list]) => {
    const h = document.createElement("h2"); h.textContent = cat; sidebar.appendChild(h);
    list.forEach(s => {
      const d = document.createElement("div");
      d.className = "item"; d.dataset.slug = s.slug;
      // DOM construction only (no innerHTML) to neutralize XSS from any manifest field.
      d.appendChild(document.createTextNode(s.example));
      const c = document.createElement("span");
      c.className = "count";
      c.textContent = `${s.frame_count | 0} frames`;
      d.appendChild(c);
      d.onclick = () => load(s);
      sidebar.appendChild(d);
    });
  });

  const frameImg = document.getElementById("frame");
  const scrub = document.getElementById("scrub");
  const btnPlay = document.getElementById("btn-play");
  const btnPrev = document.getElementById("btn-prev");
  const btnNext = document.getElementById("btn-next");
  const metaSpan = document.getElementById("meta");
  const title = document.getElementById("scn-title");
  const sub = document.getElementById("scn-sub");

  let current = null, frames = [], times = [], idx = 0, playing = false, timer = null, speed = 1, fps = 1.25;
  const baseMs = () => (1000 / fps) / speed;

  function render() {
    if (!current) return;
    const fname = frames[idx];
    if (!isSafeSeg(fname)) return;  // refuse any non-allowlisted frame name
    frameImg.src = `${current.frames_base}/${fname}`;
    scrub.value = idx;
    const t = times[idx];
    const ts = isFiniteNum(t) ? t : 0;
    metaSpan.textContent = `${idx + 1} / ${frames.length} · ${ts.toFixed(1)}s`;
  }

  function step(dir) {
    if (!current) return;
    idx = Math.max(0, Math.min(frames.length - 1, idx + dir));
    render();
  }

  function setPlaying(on) {
    playing = on;
    btnPlay.textContent = on ? "❚❚ Pause" : "▶ Play";
    if (timer) clearInterval(timer);
    if (on) {
      timer = setInterval(() => {
        if (idx >= frames.length - 1) { setPlaying(false); return; }
        idx++; render();
      }, baseMs());
    }
  }

  async function load(s) {
    if (!isSafeSlug(s.slug)) return;
    document.querySelectorAll(".item").forEach(e => e.classList.toggle("active", e.dataset.slug === s.slug));
    title.textContent = s.example;
    const totalSec = isFiniteNum(s.total_seconds) ? s.total_seconds : 0;
    sub.textContent = `${s.category} · ${s.frame_count | 0} frames · ${totalSec.toFixed(1)}s · ${s.slug}`;
    const [cat, name] = s.slug.split("/");
    if (!isSafeSeg(cat) || !isSafeSeg(name)) return;
    // Always derive paths from the (validated) slug — never trust meta_path directly.
    const metaUrl = `${cat}/${name}.json`;
    const meta = await fetch(metaUrl).then(r => r.json()).catch(() => null);
    if (!meta) return;
    const validFrames = Array.isArray(meta.frames) ? meta.frames.filter(isSafeSeg) : [];
    const validTimes = Array.isArray(meta.timestamps) ? meta.timestamps.filter(isFiniteNum) : [];
    if (!validFrames.length) return;
    frames = validFrames;
    times = validTimes;
    fps = isFiniteNum(meta.fps) && meta.fps > 0 && meta.fps <= 60 ? meta.fps : 1.25;
    current = { slug: s.slug, frames_base: `${cat}/${name}_frames` };
    idx = 0;
    scrub.max = frames.length - 1;
    setPlaying(false);
    render();
  }

  btnPlay.onclick = () => setPlaying(!playing);
  btnPrev.onclick = () => step(-1);
  btnNext.onclick = () => step(1);
  scrub.oninput = () => { idx = parseInt(scrub.value); render(); if (playing) setPlaying(true); };
  document.querySelectorAll(".speed button").forEach(b => {
    b.onclick = () => {
      document.querySelectorAll(".speed button").forEach(x => x.classList.remove("on"));
      b.classList.add("on");
      speed = parseFloat(b.dataset.speed);
      if (playing) setPlaying(true);
    };
  });
  document.addEventListener("keydown", (e) => {
    if (!current) return;
    if (e.code === "Space") { e.preventDefault(); setPlaying(!playing); }
    else if (e.code === "ArrowLeft") step(-1);
    else if (e.code === "ArrowRight") step(1);
    else if (e.code === "Home") { idx = 0; render(); }
    else if (e.code === "End") { idx = frames.length - 1; render(); }
    else if (e.key >= "1" && e.key <= "4") {
      const map = {"1":0.5,"2":1,"3":2,"4":4};
      speed = map[e.key];
      document.querySelectorAll(".speed button").forEach(b => b.classList.toggle("on", parseFloat(b.dataset.speed) === speed));
      if (playing) setPlaying(true);
    }
  });

  if (manifest.scenarios.length) load(manifest.scenarios[0]);
})();
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", default=[], help="Run only scenarios whose slug contains this (repeatable)")
    parser.add_argument("--list", action="store_true", help="List scenarios and exit")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    if args.list:
        for slug, cat, ex, _ in SCENARIOS:
            print(f"{slug:32}  {cat} / {ex}")
        return

    selected = [s for s in SCENARIOS if not args.only or any(m in s[0] for m in args.only)]
    if not selected:
        print("No scenarios matched.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)

        completed = []
        for slug, category, example, handler in selected:
            print(f"\n=== [{slug}] ===")
            # Fresh context per scenario so session_state doesn't pollute
            # (custom_env leaves an un-picklable WeatherEnvironment in state)
            ctx = browser.new_context(viewport={"width": 1280, "height": 820})
            page = ctx.new_page()
            try:
                setup_page(page)
                select_category(page, category)
                select_example(page, example)
                rec = Recorder(page, OUT_DIR / f"{slug}.gif")
                rec.snap(force=True)
                print(f"  executing…")
                t0 = time.time()
                handler(page, rec)
                print(f"  scroll-reveal…")
                rec.scroll_reveal()
                print(f"  done in {time.time()-t0:.1f}s, {len(rec.frames)} frames")
                rec.save()
                print(f"  saved {rec.output.relative_to(ROOT)}")
                completed.append((slug, category, example))
            except Exception as e:
                print(f"  FAILED: {type(e).__name__}: {e}")
            finally:
                ctx.close()

        browser.close()

    # Rebuild manifest and viewer HTML even if some failed, from existing JSON files
    _write_manifest_and_viewer()


if __name__ == "__main__":
    main()
