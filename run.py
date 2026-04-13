"""AgentSociety Replica — Streamlit App Entry Point.

Usage: streamlit run run.py
"""

import sys
from pathlib import Path

# Ensure project root is on the path
PROJECT_ROOT = str(Path(__file__).parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from app.config import init_session, set_api_key, get_api_key

st.set_page_config(
    page_title="AgentSociety Replica",
    page_icon="AS",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session()

# --- Sidebar ---
st.sidebar.title("AgentSociety Replica")
st.sidebar.caption("Python 3.14 + Gemini API")
st.sidebar.markdown("---")

category = st.sidebar.selectbox("Category", [
    "Home",
    "Basics",
    "Advanced",
    "Games",
    "Paper Experiments",
])

page = None
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
elif category == "Paper Experiments":
    page = st.sidebar.radio("Experiment", [
        "Polarization (Sec 7.2)",
        "Inflammatory Messages (Sec 7.3)",
        "UBI Policy (Sec 7.4)",
        "Hurricane Impact (Sec 7.5)",
    ])

# API Key input
st.sidebar.markdown("---")
api_key = st.sidebar.text_input(
    "Gemini API Key",
    value=get_api_key(),
    type="password",
    help="Get your key at https://aistudio.google.com/apikey",
)
if api_key:
    set_api_key(api_key)
    st.sidebar.success("API Key set")
else:
    st.sidebar.warning("API Key required")

st.sidebar.markdown("---")
st.sidebar.caption(
    "Based on [AgentSociety](https://arxiv.org/abs/2502.08691) paper.  \n"
    "Uses `agentsociety2_lite` (no litellm)."
)

# --- Main Content ---
if category == "Home" or page is None:
    st.title("AgentSociety Replica")
    st.markdown("""
    AgentSociety \ub17c\ubb38\uc758 \uc2e4\ud5d8\uc744 Python 3.14 + Gemini API \uae30\ubc18\uc73c\ub85c \uc7ac\uad6c\uc131\ud55c \ud504\ub85c\uc81d\ud2b8\uc785\ub2c8\ub2e4.

    ### Categories

    **Basics** \u2014 \uae30\ubcf8 \uc608\uc81c
    - Hello Agent: \uc5d0\uc774\uc804\ud2b8\uc640 \ub300\ud654
    - Custom Environment: \ucee4\uc2a4\ud140 \ud658\uacbd \ubaa8\ub4c8 + @tool
    - Replay System: \uc0c1\ud638\uc791\uc6a9 \uae30\ub85d/\uc7ac\uc0dd

    **Advanced** \u2014 \uc2ec\ud654 \uc608\uc81c
    - Custom Agent: AgentBase \uc0c1\uc18d, CoT \ucd94\ub860
    - Multi-Router: ReAct vs PlanExecute vs CodeGen \ube44\uad50

    **Games** \u2014 \uac8c\uc784\uc774\ub860
    - Prisoner's Dilemma: \ud611\ub825/\ubc30\uc2e0 \ub51c\ub808\ub9c8
    - Public Goods: \uacf5\uacf5\uc7ac \uae30\uc5ec \uac8c\uc784
    - Reputation Game: \ud3c9\ud310 \uae30\ubc18 \ud611\ub825 \uc9c4\ud654

    **Paper Experiments** \u2014 \ub17c\ubb38 \uc7ac\ud604
    - Polarization (7.2): \uc758\uacac \uc591\uadf9\ud654
    - Inflammatory (7.3): \uc120\ub3d9\uc801 \uba54\uc2dc\uc9c0 \ud655\uc0b0
    - UBI (7.4): \ubcf4\ud3b8\uc801 \uae30\ubcf8\uc18c\ub4dd
    - Hurricane (7.5): \ud5c8\ub9ac\ucf00\uc778 \ucda9\uaca9

    ---
    \uc67c\ucabd \uc0ac\uc774\ub4dc\ubc14\uc5d0\uc11c Category\uc640 Example\uc744 \uc120\ud0dd\ud558\uc138\uc694.
    """)

elif category == "Basics":
    if page == "01. Hello Agent":
        from app.pages.basics.hello_agent import render
        render()
    elif page == "02. Custom Environment":
        from app.pages.basics.custom_env import render
        render()
    elif page == "03. Replay System":
        from app.pages.basics.replay_system import render
        render()

elif category == "Advanced":
    if page == "01. Custom Agent":
        from app.pages.advanced.custom_agent import render
        render()
    elif page == "02. Multi-Router Comparison":
        from app.pages.advanced.multi_router import render
        render()

elif category == "Games":
    if page == "01. Prisoner's Dilemma":
        from app.pages.games.prisoners_dilemma import render
        render()
    elif page == "02. Public Goods Game":
        from app.pages.games.public_goods import render
        render()
    elif page == "03. Reputation Game":
        from app.pages.games.reputation_game import render
        render()

elif category == "Paper Experiments":
    if page == "Polarization (Sec 7.2)":
        from app.pages.papers.polarization import render
        render()
    elif page == "Inflammatory Messages (Sec 7.3)":
        from app.pages.papers.inflammatory import render
        render()
    elif page == "UBI Policy (Sec 7.4)":
        from app.pages.papers.ubi import render
        render()
    elif page == "Hurricane Impact (Sec 7.5)":
        from app.pages.papers.hurricane import render
        render()
