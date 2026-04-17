# Streamlit App Structure

## Overview

모든 예제를 하나의 Streamlit 앱에서 사이드바 메뉴로 탐색하는 통합 UI.

## File Structure

```
app/
├── app.py                       # Entry point (streamlit run app/app.py)
├── config.py                    # Gemini API config, session state init
│
├── pages/
│   ├── __init__.py
│   │
│   ├── basics/
│   │   ├── hello_agent.py       # 01. Hello Agent
│   │   ├── custom_env.py        # 02. Custom Environment
│   │   └── replay_system.py     # 03. Replay System
│   │
│   ├── advanced/
│   │   ├── custom_agent.py      # 01. Custom Agent
│   │   └── multi_router.py      # 02. Multi-Router Comparison
│   │
│   ├── games/
│   │   ├── prisoners_dilemma.py # 01. Prisoner's Dilemma
│   │   ├── public_goods.py      # 02. Public Goods Game
│   │   └── reputation_game.py   # 03. Reputation Game
│   │
│   └── papers/
│       ├── polarization.py      # Polarization (7.2)
│       ├── inflammatory.py      # Inflammatory Messages (7.3)
│       ├── ubi.py               # UBI (7.4)
│       └── hurricane.py         # Hurricane (7.5)
│
└── components/
    ├── __init__.py
    ├── agent_card.py            # Reusable agent profile card
    ├── chat_view.py             # Chat message display
    ├── network_graph.py         # Network visualization (pyvis/plotly)
    ├── comparison_table.py      # Paper vs simulation comparison
    └── metrics_panel.py         # st.metric based summary panels
```

## App Entry Point (app.py)

```python
import streamlit as st

st.set_page_config(
    page_title="AgentSociety Mini Reinterpretation",
    page_icon="🏛️",
    layout="wide",
)

# Sidebar navigation
st.sidebar.title("AgentSociety Mini Reinterpretation")
st.sidebar.markdown("---")

category = st.sidebar.selectbox("Category", [
    "Basics", "Advanced", "Games", "Paper Experiments"
])

if category == "Basics":
    page = st.sidebar.radio("Example", [
        "01. Hello Agent",
        "02. Custom Environment",
        "03. Replay System",
    ])
elif category == "Advanced":
    page = st.sidebar.radio("Example", [
        "01. Custom Agent",
        "02. Multi-Router Comparison",
    ])
elif category == "Games":
    page = st.sidebar.radio("Example", [
        "01. Prisoner's Dilemma",
        "02. Public Goods Game",
        "03. Reputation Game",
    ])
else:
    page = st.sidebar.radio("Experiment", [
        "Polarization (Sec 7.2)",
        "Inflammatory Messages (Sec 7.3)",
        "UBI Policy (Sec 7.4)",
        "Hurricane Impact (Sec 7.5)",
    ])

# API Key status
st.sidebar.markdown("---")
api_key = st.sidebar.text_input("Gemini API Key", type="password")
if api_key:
    st.sidebar.success("API Key set")
else:
    st.sidebar.warning("Enter API Key to run experiments")

# Route to page
# ... import and render selected page
```

## Shared State Management

```python
# config.py
import streamlit as st

def init_session():
    """Initialize session state for the app."""
    defaults = {
        "api_key": "",
        "chat_history": [],
        "experiment_results": {},
        "current_experiment": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
```

## Reusable Components

### Agent Profile Card
```python
def agent_card(name, profile, col=None):
    """Display agent profile as an info card."""
    container = col or st
    with container:
        st.markdown(f"**{name}**")
        for k, v in profile.items():
            st.caption(f"{k}: {v}")
```

### Chat View
```python
def chat_view(messages):
    """Display chat messages with role-based styling."""
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
```

### Network Graph
```python
def network_graph(nodes, edges, highlight=None):
    """Render interactive network using pyvis or plotly."""
    # pyvis for interactive, plotly for static
    ...
```

## Page Template Pattern

각 페이지는 동일한 패턴을 따름:

```python
# pages/basics/hello_agent.py
import streamlit as st
from agentsociety2_lite import PersonAgent
from agentsociety2_lite.society import AgentSociety

def render():
    st.header("Hello Agent")

    # 1. Setup section
    with st.expander("Agent Profile", expanded=True):
        # Display agent info

    # 2. Scenario buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Preset Q1"):
            ...

    # 3. Chat interface
    if prompt := st.chat_input("Ask a question"):
        # Call LLM, display response
        ...

    # 4. Results
    # Display accumulated results
```

## Running the App

```bash
# From project root
cd AgentSociety_mini_reinterpretation
source .venv/Scripts/activate  # or .venv/bin/activate on Linux/Mac
streamlit run app/app.py
```

## Design Principles

1. **Progressive Disclosure**: 기본 결과를 먼저 보여주고, 상세(추론 과정, tool calls)는 expander로
2. **Consistent Layout**: 모든 페이지가 Setup → Execution → Results 흐름
3. **Session Persistence**: 실험 결과를 session_state에 캐싱 (페이지 전환 시 유지)
4. **API Key Safety**: 사이드바에서 입력, session_state에만 저장 (파일 저장 안 함)
5. **Responsive**: `st.columns`로 넓은 화면 활용, 좁은 화면에서는 세로 스택
