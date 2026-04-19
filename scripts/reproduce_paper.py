"""Headless reproduction runner — executes the 4 paper scenarios + a smoke-test
pass over basics/advanced/games, writes a single JSON report. Driven by
docs/reproduction_plan.md.

Usage:
    # activate the env + load .env.local into environment, then:
    python scripts/reproduce_paper.py --out results/reproduction_$(date +%Y%m%d).json

    # run only a subset:
    python scripts/reproduce_paper.py --only polarization inflammatory

The script calls the per-page runner coroutines directly (no Streamlit).
Secrets never printed — only `mask_key()` previews are shown.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Make the package importable when invoked from repo root.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load .env.local first (dev key), then .env as fallback.
load_dotenv(ROOT / ".env.local", override=True)
load_dotenv(ROOT / ".env", override=False)


def mask_key(k: str) -> str:
    if not k:
        return "<missing>"
    return k[:8] + "<redacted>"


def _must_have_key() -> None:
    k = os.getenv("GEMINI_API_KEY", "").strip()
    if not k:
        raise SystemExit("GEMINI_API_KEY not set — populate .env.local before running.")
    print(f"[env] GEMINI_API_KEY = {mask_key(k)}")
    print(f"[env] GEMINI_MODEL   = {os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')}")
    print(f"[env] LLM_BACKEND    = {os.getenv('LLM_BACKEND', 'gemini')}")


# ──────────────────────────── Runners ────────────────────────────────────────


async def run_hello_agent() -> dict:
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from agentsociety2_lite.contrib import SimpleSocialSpace

    profile = {
        "name": "Alice", "age": 28,
        "personality": "friendly, curious, and optimistic",
        "bio": "A software engineer who loves hiking, reading sci-fi novels, and cooking.",
        "location": "San Francisco",
    }
    agent = PersonAgent(id=1, profile=profile)
    env = SimpleSocialSpace(agent_id_name_pairs=[(agent.id, agent.name)])
    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=[agent], env_router=router, start_t=datetime.now())
    await society.init()
    resp = await society.ask("Tell me about Alice's personality and interests.")
    await society.close()
    return {
        "question": "Tell me about Alice's personality and interests.",
        "response_head": resp[:240],
        "response_len": len(resp),
        "profile_reflected": any(w in resp.lower() for w in ("hiking", "sci-fi", "cooking", "friendly", "curious")),
    }


async def run_custom_env() -> dict:
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from app.pages.basics.custom_env import WeatherEnvironment

    env = WeatherEnvironment()
    agents = [PersonAgent(id=i, profile={"name": f"Agent{i}"}) for i in (1, 2)]
    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=agents, env_router=router, start_t=datetime.now())
    await society.init()

    ask_resp = await society.ask("What is the current weather?")
    weather_before = env._weather
    int_resp = await society.intervene("Change the weather to rainy at 14 degrees.")
    weather_after = env._weather
    temp_after = env._temperature
    await society.close()

    return {
        "ask_response_head": ask_resp[:200],
        "intervene_response_head": int_resp[:200],
        "weather_before": weather_before,
        "weather_after": weather_after,
        "temperature_after": temp_after,
        "readonly_preserved_state": weather_before == "sunny",
        "intervene_mutated_state": weather_after != weather_before,
    }


async def run_replay_system() -> dict:
    from app.pages.basics.replay_system import _run_simulation
    rows = await _run_simulation()
    return {
        "rows_recorded": len(rows),
        "first_row": {k: (str(v)[:120] if k != "timestamp" else v) for k, v in (rows[0] or {}).items()} if rows else {},
        "agents_covered": len({r.get("agent") for r in rows if r.get("agent")}),
    }


async def run_prisoners_dilemma() -> dict:
    # We invoke the page's helper directly.
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from agentsociety2_lite.contrib import PrisonersDilemma

    env = PrisonersDilemma(["Alice", "Bob"])
    agents = [
        PersonAgent(id=1, profile={"name": "Alice", "personality": "strategic and rational"}),
        PersonAgent(id=2, profile={"name": "Bob", "personality": "trusting but cautious"}),
    ]
    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=agents, env_router=router, start_t=datetime.now())
    await society.init()

    rounds = []
    for r in range(2):
        a = await society.ask(
            "You are Alice in Prisoner's Dilemma. T=5 > R=3 > P=1 > S=0. "
            "Choose COOPERATE or DEFECT. One word."
        )
        b = await society.ask(
            "You are Bob in Prisoner's Dilemma. T=5 > R=3 > P=1 > S=0. "
            "Choose COOPERATE or DEFECT. One word."
        )
        da = "COOPERATE" if "cooperate" in a.lower() else "DEFECT"
        db = "COOPERATE" if "cooperate" in b.lower() else "DEFECT"
        rounds.append({"round": r + 1, "alice": da, "bob": db})
    await society.close()
    return {"rounds": rounds}


async def run_public_goods() -> dict:
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from agentsociety2_lite.contrib import PublicGoodsGame

    n = 4
    env = PublicGoodsGame(endowment=20, contribution_factor=2.0)
    agents = [PersonAgent(id=i + 1, profile={"name": f"Player{i+1}", "personality": "pragmatic"})
              for i in range(n)]
    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=agents, env_router=router, start_t=datetime.now())
    await society.init()

    contribs_per_round = []
    for r in range(2):
        row = []
        for i in range(n):
            resp = await society.ask(
                f"You are Player{i+1}. Endowment=20, multiplier=2.0, group size={n}. "
                "Choose how many tokens (0-20) to contribute to the public pot. One integer."
            )
            m = re.search(r"\d+", resp)
            c = int(m.group(0)) if m else 0
            c = max(0, min(20, c))
            row.append(c)
        contribs_per_round.append(row)
    await society.close()
    return {
        "rounds_contributions": contribs_per_round,
        "avg_contribution_r1": sum(contribs_per_round[0]) / n,
        "avg_contribution_r2": sum(contribs_per_round[1]) / n,
    }


async def run_polarization(mode: str = "broadcast") -> dict:
    from app.pages.papers.polarization import (
        _generate_profiles, _run_condition, _run_broadcast,
    )
    profiles = _generate_profiles(n=10, seed=42)
    runner = _run_broadcast if mode == "broadcast" else _run_condition
    out = {}
    for cond in ("control", "homophilic", "heterogeneous"):
        res = await runner(cond, profiles, num_rounds=2)
        out[cond] = {
            "polarized_pct": res["polarized_pct"],
            "moderated_pct": res["moderated_pct"],
            "unchanged": res["unchanged"],
        }
        if res.get("propagation_stats"):
            out[cond]["propagation_stats"] = res["propagation_stats"]
    return {"mode": mode, "by_condition": out}


async def run_inflammatory() -> dict:
    from app.pages.papers.inflammatory import (
        _run_spread, NORMAL_MSG, INFLAMMATORY_MSG,
    )
    n, steps = 8, 3
    out = {}
    for cond in ("control", "experimental", "node_intervention", "edge_intervention"):
        is_inflammatory_seed = cond != "control"
        msg = INFLAMMATORY_MSG if is_inflammatory_seed else NORMAL_MSG
        r = await _run_spread(
            cond, n, msg, is_inflammatory_seed, steps,
            use_llm_classifier=True,
        )
        out[cond] = {
            "final_spread": r["final_spread"],
            "final_emotion": r["final_emotion"],
            "total_messages": r["total_messages"],
            "banned": r["banned"],
            "removed_edges": r["removed_edges"],
            "classifier_calls": r.get("classifier_calls", 0),
        }
    return out


async def run_ubi() -> dict:
    from app.pages.papers.ubi import _run_ubi, _generate_profiles
    profiles = _generate_profiles(n=6)
    months = 4
    ubi_start = 2
    r_no = await _run_ubi(profiles, 0, months, 0, run_cesd=True)
    r_yes = await _run_ubi(profiles, 1000, months, ubi_start, run_cesd=True)
    return {
        "months": months, "ubi_start_month": ubi_start,
        "without_ubi": {
            "final_consumption": r_no["final"]["avg_consumption"],
            "final_savings": r_no["final"]["avg_savings"],
            "final_happiness": r_no["final"]["avg_happiness"],
            "cesd_mean": r_no.get("cesd_mean"),
        },
        "with_ubi": {
            "final_consumption": r_yes["final"]["avg_consumption"],
            "final_savings": r_yes["final"]["avg_savings"],
            "final_happiness": r_yes["final"]["avg_happiness"],
            "cesd_mean": r_yes.get("cesd_mean"),
        },
    }


async def run_hurricane() -> dict:
    from app.pages.papers.hurricane import _run_hurricane
    r = await _run_hurricane(10)
    return {
        "days": [
            {"day": d["day"], "activity": d["activity"], "trips": d["trips"]}
            for d in r["daily"]
        ],
    }


# ────────────────────────── Orchestration ────────────────────────────────────

SCENARIOS = {
    "hello_agent":       run_hello_agent,
    "custom_env":        run_custom_env,
    "replay_system":     run_replay_system,
    "prisoners_dilemma": run_prisoners_dilemma,
    "public_goods":      run_public_goods,
    "polarization":      run_polarization,
    "inflammatory":      run_inflammatory,
    "ubi":               run_ubi,
    "hurricane":         run_hurricane,
}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=list(SCENARIOS.keys()),
                    help="subset of scenarios to run")
    ap.add_argument("--out", default="results/reproduction_report.json")
    args = ap.parse_args()

    _must_have_key()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    results: dict = {
        "meta": {
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            "backend": os.getenv("LLM_BACKEND", "gemini"),
        },
        "scenarios": {},
    }

    for name in args.only:
        fn = SCENARIOS.get(name)
        if not fn:
            print(f"[skip] unknown scenario: {name}")
            continue
        print(f"\n=== running: {name} ===")
        t0 = time.perf_counter()
        try:
            data = await fn()
            elapsed = time.perf_counter() - t0
            results["scenarios"][name] = {
                "ok": True,
                "elapsed_sec": round(elapsed, 2),
                "data": data,
            }
            print(f"[ok] {name} done in {elapsed:.1f}s")
        except Exception as e:
            elapsed = time.perf_counter() - t0
            print(f"[FAIL] {name}: {type(e).__name__}: {e}")
            traceback.print_exc()
            results["scenarios"][name] = {
                "ok": False,
                "elapsed_sec": round(elapsed, 2),
                "error": f"{type(e).__name__}: {e}",
            }

    results["meta"]["finished_at"] = datetime.now().isoformat(timespec="seconds")
    Path(args.out).write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[done] wrote {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
