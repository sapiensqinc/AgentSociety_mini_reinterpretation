# AgentSociety-mini-reinterpretation

A mini reinterpretation of Piao et al.'s **AgentSociety: Large-Scale Simulation of LLM-Driven Generative Agents Advances Understanding of Human Behaviors and Society** (Piao et al., 2025). Scoped for research/demo replay.

## What this is

**Keeps** the paper's core contribution:
- LLM-driven generative agents with emotion / needs / cognition layers (Paper §3)
- Social environment composed of urban space, social space, and economic space (§4)
- The four flagship social simulations: **Polarization**, **Inflammatory Messages**, **Universal Basic Income**, **Hurricane Impact** (§7.2–§7.5)
- Environment router abstraction (`ReAct` / `PlanExecute` / `CodeGen`) as interchangeable strategies

**Adds**:
- **Python 3.14 compatibility** — the original `agentsociety2` pins ≤ 3.13
- **9-dependency core** (down from 45+): `google-genai`, `pydantic`, `json-repair`, `python-dotenv`, `sqlalchemy`, `streamlit`, `plotly`, `pyvis`, `aiohttp`
- **BYOK security model** — no server-side key storage, per-session rate limits, prompt-injection input sanitization, simulation-parameter caps against DoS
- **Playwright-based GIF recorder + HTML timeline viewer** for every scenario (`gifs/viewer.html`) — play / pause / scrub / speed, no server round-trip after initial load

**GIF preview** (Hurricane Impact, §7.5)

![hurricane](gifs/papers/hurricane.gif)

Twelve scenarios recorded end-to-end — see [`gifs/`](gifs/) or open [`gifs/viewer.html`](gifs/viewer.html) for the scrubbable timeline.

## Directory layout

```
AgentSociety_mini_reinterpretation/
├── run.py                      # Streamlit entry point (home + routing)
├── requirements.txt
├── agentsociety2_lite/         # lightweight core library
│   ├── llm/                    # Gemini client (direct google-genai)
│   ├── agent/                  # PersonAgent + base
│   ├── env/                    # environment router (ReAct, PlanExecute, CodeGen)
│   ├── society/                # AgentSociety orchestrator
│   ├── contrib/                # optional env modules (social, games)
│   └── storage/                # replay writer (SQLite)
├── app/
│   ├── config.py               # BYOK session state
│   ├── security.py             # rate limit + input sanitization + param caps
│   ├── components/             # agent_card, chat_view
│   └── pages/
│       ├── basics/             # hello_agent, custom_env, replay_system
│       ├── advanced/           # custom_agent, multi_router
│       ├── games/              # prisoner's dilemma, public goods, reputation
│       └── papers/             # polarization, inflammatory, ubi, hurricane
├── docs/                       # architecture, security review, per-example design
├── scripts/
│   ├── record_gifs.py          # Playwright driver + GIF writer
│   └── extract_from_gifs.py    # regenerate viewer frames from existing GIFs
└── gifs/
    ├── <category>/<name>.gif           # per-scenario animated GIF
    ├── <category>/<name>_frames/*.jpg  # raw frames for the viewer
    ├── <category>/<name>.json          # frame list + timestamps
    ├── manifest.json                   # index of all scenarios
    └── viewer.html                     # scrubbable timeline player
```

## Quick start

```bash
# 1. install
python -m venv .venv
source .venv/Scripts/activate     # Windows
# source .venv/bin/activate       # Linux/Mac
pip install -r requirements.txt

# 2. set API key
#    the app is BYOK — the key is entered in the Streamlit sidebar and
#    stored only in session state. For local/CI use you can also put it
#    in .env.local so scripts/record_gifs.py can pick it up.
cp .env.example .env.local
# then set GEMINI_API_KEY=...  (default model: gemini-2.5-flash)

# 3. run the Streamlit app (sidebar → category → example → enter API key → run)
streamlit run run.py
# open http://localhost:8501

# 4. record every scenario as a GIF (CAUTION: spends Gemini credits)
#    each scenario uses minimum-cost defaults:
#      - agents capped to the lower bound
#      - rounds / steps / months = 1–2
#      - multiselect conditions trimmed to a single branch
#    full 12-scenario sweep ≈ $0.05–$0.15 in Gemini Flash credits
playwright install chromium
python scripts/record_gifs.py                  # all 12 scenarios
python scripts/record_gifs.py --only hurricane # one at a time
python scripts/record_gifs.py --list           # see slugs

# 5. view the recordings (timeline scrubber, play/pause, keyboard shortcuts)
python -m http.server 8700 --directory gifs
# open http://localhost:8700/viewer.html
```

## Scenarios

| Category | Example | Paper ref | What it demonstrates |
|----------|---------|-----------|----------------------|
| Basics | Hello Agent | §3 | Profile → system prompt → LLM dialogue |
| Basics | Custom Environment | §4 | Environment module + natural-language query via CodeGenRouter |
| Basics | Replay System | §5 | SQLite event log of agent interactions |
| Advanced | Custom Agent | §3 | Specialist / Reflection / Recursive-CoT agent variants |
| Advanced | Multi-Router | §4 | ReAct vs PlanExecute vs CodeGen on the same task |
| Games | Prisoner's Dilemma | — | 2-agent payoff game + LLM reasoning + reflection |
| Games | Public Goods | — | N-agent contribution game over multiple rounds |
| Games | Reputation Game | — | Indirect reciprocity under `stern_judging` / `image_score` / `simple_standing` norms |
| Papers | Polarization | §7.2 | Opinion shift under homophilic vs heterogeneous exposure |
| Papers | Inflammatory Messages | §7.3 | Spread of inflammatory content, node / edge moderation |
| Papers | UBI Policy | §7.4 | Consumption, savings, well-being under monthly UBI |
| Papers | Hurricane Impact | §7.5 | Pre / during / post evacuation decisions by persona |

## Attribution

This project is a reinterpretation of the architecture described in:

> Jinghua Piao, Yuwei Yan, Jun Zhang, Nian Li, Junbo Yan, Xiaochong Lan, Zhihong Lu,
> Zhiheng Zheng, Jing Yi Wang, Di Zhou, Chen Gao, Fengli Xu, Fang Zhang, Ke Rong,
> Jun Su, and Yong Li. 2025.
> *AgentSociety: Large-Scale Simulation of LLM-Driven Generative Agents Advances Understanding of Human Behaviors and Society.*
> [Paper](https://arxiv.org/abs/2502.08691) ·
> [Original repo](https://github.com/tsinghua-fib-lab/AgentSociety)
