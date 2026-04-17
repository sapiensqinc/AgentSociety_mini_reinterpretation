"""Extract per-frame JPEGs + metadata from already-recorded GIFs.

This avoids re-running scenarios (saving LLM cost) when we only need to add
the timeline viewer artifacts.
"""
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "gifs"

SCENARIOS = [
    ("basics/hello_agent",      "Basics",            "01. Hello Agent"),
    ("basics/custom_env",       "Basics",            "02. Custom Environment"),
    ("basics/replay_system",    "Basics",            "03. Replay System"),
    ("advanced/custom_agent",   "Advanced",          "01. Custom Agent"),
    ("advanced/multi_router",   "Advanced",          "02. Multi-Router"),
    ("games/prisoners_dilemma", "Games",             "01. Prisoner's Dilemma"),
    ("games/public_goods",      "Games",             "02. Public Goods"),
    ("games/reputation_game",   "Games",             "03. Reputation Game"),
    ("papers/polarization",     "Paper Experiments", "Polarization (Sec 7.2)"),
    ("papers/inflammatory",     "Paper Experiments", "Inflammatory (Sec 7.3)"),
    ("papers/ubi",              "Paper Experiments", "UBI Policy (Sec 7.4)"),
    ("papers/hurricane",        "Paper Experiments", "Hurricane (Sec 7.5)"),
]


def extract_one(slug: str) -> dict | None:
    gif_path = OUT_DIR / f"{slug}.gif"
    if not gif_path.exists():
        return None
    im = Image.open(gif_path)
    n = im.n_frames
    # Frame duration from GIF header
    durations = []
    for i in range(n):
        im.seek(i)
        durations.append(im.info.get("duration", 800))
    total_ms = sum(durations)
    fps = 1000.0 / (total_ms / n) if n else 1.25

    frames_dir = gif_path.parent / f"{Path(slug).name}_frames"
    frames_dir.mkdir(exist_ok=True)
    for old in frames_dir.glob("*.jpg"):
        old.unlink()

    frame_files = []
    timestamps = []
    t_acc = 0.0
    for i in range(n):
        im.seek(i)
        fname = f"f{i:03d}.jpg"
        im.convert("RGB").save(frames_dir / fname, format="JPEG", quality=80, optimize=True)
        frame_files.append(fname)
        timestamps.append(round(t_acc / 1000.0, 3))
        t_acc += durations[i]

    meta = {
        "slug": slug,
        "width": im.width,
        "height": im.height,
        "fps": round(fps, 3),
        "frames": frame_files,
        "timestamps": timestamps,
        "total_seconds": round(t_acc / 1000.0, 3),
    }
    (gif_path.parent / f"{Path(slug).name}.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    return meta


def main():
    entries = []
    for slug, cat, ex in SCENARIOS:
        meta = extract_one(slug)
        if not meta:
            print(f"[skip] {slug} (no gif)")
            continue
        entries.append({
            "slug": slug,
            "category": cat,
            "example": ex,
            "meta_path": f"{slug}.json",
            "gif_path": f"{slug}.gif",
            "frames_dir": f"{Path(slug).parent.as_posix()}/{Path(slug).name}_frames",
            "frame_count": len(meta["frames"]),
            "total_seconds": meta["total_seconds"],
        })
        print(f"[ok] {slug}: {len(meta['frames'])} frames, {meta['total_seconds']}s")

    (OUT_DIR / "manifest.json").write_text(
        json.dumps({"scenarios": entries}, indent=2), encoding="utf-8"
    )
    # Import viewer HTML from main script
    sys.path.insert(0, str(Path(__file__).parent))
    from record_gifs import _VIEWER_HTML
    (OUT_DIR / "viewer.html").write_text(_VIEWER_HTML, encoding="utf-8")

    print(f"\nmanifest: {len(entries)} scenarios → gifs/manifest.json")
    print(f"viewer:   gifs/viewer.html")


if __name__ == "__main__":
    main()
