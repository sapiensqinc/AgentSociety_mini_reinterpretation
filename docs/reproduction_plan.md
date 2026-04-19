# Paper Reproduction Plan — Cost-Minimized

**Goal**: Verify that this mini-reinterpretation reproduces the **qualitative
patterns** of AgentSociety §7.2–§7.5 at a fraction of the paper's compute cost.

Paper baseline: 100–1,000 agents × multi-day simulation on DeepSeek-V3 API,
off-peak hours. Our target: recover the **direction and ordering** of each
paper finding for **under USD 2 total** across all 4 scenarios.

## Cost-minimization principles

1. **Minimum viable N** — pick the smallest agent count that still shows the
   paper's effect. For opinion dynamics, N=10 is enough to see polarization
   direction; for mobility, N=15 is enough to show the activity collapse.
2. **Shortest useful time axis** — paper Fig 17 runs 30 steps; we use 4.
   Paper UBI runs 120+ months; we introduce UBI at month 4 of 8.
3. **Single LLM call per agent per tick** — batch all decisions (opinion +
   forward + emotion + CES-D ratings) into one prompt where possible.
4. **Cheapest model that preserves the ordering** — Gemini 2.5 Flash at
   ~$0.30/M output tokens; faithful-mode toggles only flip when necessary.
5. **Seed fixed** — `random.seed(42)` throughout, so one successful run is
   the whole cost; no averaging across 10 seeds.
6. **Skip expensive branches by default** — LLM classifier in inflammatory
   and CES-D in UBI are opt-in checkboxes. The report runs them exactly once
   per scenario on the faithful path.

## Model choice

| Tier | Model | Price (per 1K) | Used for |
|---|---|---|---|
| Default | `gemini-2.5-flash` | in: $0.075 / out: $0.30 | All scenarios in this report |
| Optional | `mistralai/Mistral-Small-3.1-24B-Instruct-2503` on HF Router | ~$0.20 blended | Second-track validation (ungate via `LLM_BACKEND=openai_compat`) |

Claude Sonnet 4.7 gives slightly better persona consistency but at 6–10× the
cost per token; not recommended for the baseline run.

## Scenario-by-scenario budget

All estimates assume Gemini 2.5 Flash with ~500 input + 250 output tokens
per LLM call. Numbers rounded up to allow 20 % retry headroom.

### §7.2 Polarization — **~60 LLM calls, ~$0.02**

- Agents: **10** (paper: 100 NY residents)
- Rounds: **2** (peer-to-peer mode) or **2** (broadcast mode; adds ~20 extra
  calls for forwards)
- Conditions: 3 (control, homophilic, heterogeneous) → 3 × 10 × 2 = 60 calls
- Success criterion: **ordering** matches paper —
  `homophilic polarized % ≥ control polarized % ≥ heterogeneous polarized %`
  AND `heterogeneous moderated % ≥ control moderated %`.
- Faithful knob: enable broadcast mode for the final report run
  (propagation_count ≤ 5, ~+30 % calls).

### §7.3 Inflammatory Messages — **~160 LLM calls, ~$0.06**

- Agents: **10** (paper: "hundreds")
- Steps: **4** (paper: 30 Fig 17)
- Conditions: 4 (control / experimental / node / edge) → 4 × 10 × 4 = 160 calls
- LLM classifier: **ON** for the faithful run (+≈ 16 classifier calls,
  deduplicated by message content, total still under $0.07).
- Success criteria (three comparisons):
  1. `experimental.final_spread > control.final_spread`
  2. `node_intervention.final_spread < edge_intervention.final_spread`
  3. `node_intervention.final_emotion < experimental.final_emotion`

### §7.4 UBI — **~100 LLM calls (+20 CES-D), ~$0.05**

- Agents: **8** (paper: 100 Texas residents)
- Total months: **6**, UBI introduction at **month 3**, follow-up 3 months
- 2 conditions (w/ vs w/o UBI) → 2 × 8 × 6 = 96 main-loop calls
- CES-D survey: **ON** → +2 × 8 = 16 calls (single-batch JSON per agent)
- Success criteria:
  1. `consumption_with_ubi[final] > consumption_without_ubi[final]`
  2. `depression_with_ubi < depression_without_ubi`

### §7.5 Hurricane — **~135 LLM calls, ~$0.05**

- Agents: **15** (paper: 1,000 Columbia SC)
- Days: **9** (paper: 9, matches exactly) → 15 × 9 = 135 calls
- Single condition (the hurricane schedule is the treatment)
- Success criteria:
  1. `activity_before > 0.6` AND `activity_during < 0.4`
  2. `activity_after > activity_during + 0.2` (recovery)
  3. Total Daily Trips follows U-shape (max before/after, min during)

## Total

| Scenario | LLM calls | Gemini Flash cost | Notes |
|---|---:|---:|---|
| Polarization | ~60 | $0.02 | 10 agents × 2 rounds × 3 conditions |
| Inflammatory | ~175 | $0.07 | includes classifier |
| UBI | ~115 | $0.05 | includes CES-D |
| Hurricane | ~135 | $0.05 | 15 agents × 9 days |
| **Total** | **~485 calls** | **~$0.19** | one baseline run |

**Plus 20 % retry headroom → target ceiling $0.25.** Session token cap in
`app/security.py` is set to 500 K tokens / $2, comfortably above this.

## Execution protocol

1. Set `GEMINI_API_KEY` in `.env.local` (or sidebar), `LLM_BACKEND=gemini`.
2. Seed `random.seed(42)` is already hardcoded per scenario.
3. Run each scenario once from the Streamlit UI:
   - Polarization: mode = `broadcast + propagation`, all 3 conditions.
   - Inflammatory: check "논문 충실: LLM 분류기", all 4 conditions.
   - UBI: check "CES-D 우울증 평가", UBI intro month = 3, total 6 months.
   - Hurricane: defaults (15 agents).
4. Capture each scenario's result block as JSON:
   ```python
   {"scenario": "polarization", "model": "gemini-2.5-flash",
    "seed": 42, "mode": "broadcast",
    "results": { ... as emitted by the runner ... }}
   ```
5. Paste alongside the paper's numbers in the template below.

## Reporting template

`docs/reproduction_report.md` (to be created after the first run):

```markdown
# Reproduction Report

Model: gemini-2.5-flash · Date: YYYY-MM-DD · Seed: 42 · Total cost: $X.XX

## §7.2 Polarization (target ordering match)

| Condition | Paper polarized % | Ours polarized % | Paper moderated % | Ours moderated % | ✓ / ✗ |
|---|---:|---:|---:|---:|:---:|
| control | 39 | ? | 33 | ? | |
| homophilic | 52 | ? | — | ? | |
| heterogeneous | — | ? | 89 | ? | |

Ordering check: …

## §7.3 Inflammatory …

[fill in after run]
```

## When to escalate

Re-run with more agents / more rounds / larger model only if **at least one**
of the success criteria fails qualitatively. A numerical mismatch against the
paper's exact percentages does not count as failure; we target direction and
ordering only.

If escalation is needed:

1. First — bump N per-scenario by 2×. Cost ≈ 2×.
2. Second — switch to `mistralai/Mistral-Small-3.1-24B-Instruct-2503` via
   HF Router (~30 % cost bump over Flash, stronger reasoning).
3. Last — Claude Sonnet 4.7. ~10× cost, only if still failing.

Never bump N beyond 20 in the Streamlit UI (the `PARAM_CAPS["agents"] = 20`
guard in `app/security.py` protects shared deployments).
