"""AgentSociety Mini Reinterpretation — Streamlit App Entry Point.

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


def _render_home():
    # Hero section
    st.title("AgentSociety Mini Reinterpretation")
    st.caption("LLM 기반 사회 시뮬레이션의 재현 및 실험 플랫폼 — arXiv:2502.08691 기반")

    # Quick stats
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("논문 실험", "4개", "Sec 7.2-7.5")
    m2.metric("예제", "12개", "4 카테고리")
    m3.metric("의존성", "9개", "45+ → 9")
    m4.metric("Python", "3.14", "호환")

    st.divider()

    # Intro
    with st.container(border=True):
        st.markdown(
            "**AgentSociety**는 LLM 기반 생성 에이전트로 사람의 행동과 사회 현상을 "
            "대규모로 시뮬레이션하는 칭화대학교의 연구 프로젝트입니다. "
            "본 저장소는 해당 논문과 코드베이스의 핵심을 재현하고, 연구자·개발자가 "
            "**Python 3.14 + Gemini API**만으로 즉시 실험할 수 있도록 경량화한 플랫폼입니다."
        )

    # Section 1: Problems
    st.markdown("## AgentSociety가 해결하려는 문제")

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("#### 사회과학의 근본적 딜레마")
            st.markdown(
                "**실제 사회 실험은 비용·윤리·규모 장벽으로 실행 불가능한 경우가 많습니다.**\n\n"
                "- UBI를 10만 명에게 3년간 지급하고 우울증 변화 측정? **현실에서 불가능**\n"
                "- 허리케인 대피 정책을 사전 검증? **한 번뿐인 자연재해**\n"
                "- 선동적 메시지의 확산 동태? **실시간 관찰·개입의 한계**\n\n"
                "**기존 에이전트 기반 모델(ABM, Agent-Based Model)의 한계**\n"
                "- 수식·규칙 기반 단순화로 복잡한 인지·감정·맥락 미반영\n"
                "- 고정 규칙으로는 새로운 시나리오에 일반화 불가"
            )
    with c2:
        with st.container(border=True):
            st.markdown("#### 기존 LLM 에이전트 연구의 한계")
            st.markdown(
                "- **소규모에 머무름** — Generative Agents (스탠퍼드, 2023)는 25명 규모\n"
                "- **단편적 실험** — 하나의 시나리오만 다루고 재현성·확장성 낮음\n"
                "- **사회 인프라 부재** — 도시·경제·네트워크 통합 없음\n\n"
                "**결과**\n"
                "- LLM의 인간다움 × 대규모 환경이 결합된 사례 부족\n"
                "- 사회 수준의 창발 행동 관찰 불가"
            )

    st.markdown("")

    # Section 2: Key Insight (3-axis integration)
    st.markdown("## 착안점 — 세 가지 축의 통합")
    st.info("**세 요소를 하나의 프레임워크로 통합한 점이 AgentSociety의 핵심 기여입니다.**")

    a1, a2, a3 = st.columns(3)
    with a1:
        with st.container(border=True):
            st.markdown("##### 1. LLM 생성 에이전트")
            st.caption("논문 Section 3")
            st.markdown(
                "감정(Emotion)-욕구(Needs)-인지(Cognition) 계층 구조로 "
                "인간다운 의사결정을 재현"
            )
    with a2:
        with st.container(border=True):
            st.markdown("##### 2. 현실 반영 사회 환경")
            st.caption("논문 Section 4")
            st.markdown(
                "**도시공간**(OSM·SafeGraph) · **사회공간**(SNS·평판) · "
                "**경제공간**(DSGE) 통합"
            )
    with a3:
        with st.container(border=True):
            st.markdown("##### 3. 대규모 시뮬레이션 엔진")
            st.caption("논문 Section 5")
            st.markdown(
                "Ray 분산, MQTT 메시징으로 **10,000+ 에이전트, 500만 상호작용** 지원"
            )

    with st.expander("왜 이 결합이 의미 있는가"):
        st.markdown(
            "- **LLM만으로는 환경이 없음** — 감정적 판단은 가능하나 경제·지리적 맥락이 빠짐\n"
            "- **ABM(Agent-Based Model)만으로는 인간다움이 없음** — 규모는 커도 결정이 단순함\n"
            "- **LLM + 환경 + 엔진의 결합**이 처음으로 **사회적 실재감**을 재현 가능하게 함"
        )

    st.markdown("")

    # Section 3: Solution direction - 4 experiments
    st.markdown("## 해결 방향 — 논문의 네 가지 대표 실험")
    st.caption("실제로는 수행이 불가능하거나 비싼 사회 실험의 사전 시뮬레이션")

    e1, e2 = st.columns(2)
    with e1:
        with st.container(border=True):
            st.markdown("**Polarization** `Sec 7.2`")
            st.caption("총기규제 의견 양극화")
            st.markdown(
                "에코 챔버에서의 극화 강화와 "
                "교차 노출에서의 완화 효과를 검증"
            )
        with st.container(border=True):
            st.markdown("**Universal Basic Income** `Sec 7.4`")
            st.caption("보편적 기본소득 정책")
            st.markdown(
                "월 $1,000 UBI가 소비·저축·우울증에 미치는 "
                "다차원 영향을 정량 계산"
            )
    with e2:
        with st.container(border=True):
            st.markdown("**Inflammatory Messages** `Sec 7.3`")
            st.caption("선동적 메시지 확산")
            st.markdown(
                "선동 콘텐츠의 확산 가속과 "
                "모더레이션 전략(노드/엣지)별 효과 비교"
            )
        with st.container(border=True):
            st.markdown("**Hurricane** `Sec 7.5`")
            st.caption("자연재해 외부 충격")
            st.markdown(
                "허리케인 전/중/후 이동성 변화를 "
                "실제 SafeGraph 데이터와 대조 검증"
            )

    st.markdown("")

    # Section 4: Value
    st.markdown("## 이 논문·GitHub의 가치")

    v1, v2 = st.columns(2)
    with v1:
        with st.container(border=True):
            st.markdown("#### 학술적 가치")
            st.markdown(
                "- 계산사회과학의 새로운 방법론\n"
                "- **정책 실험실(policy sandbox)** 가능성\n"
                "- 인문·사회과학 × AI 융합 플랫폼"
            )
    with v2:
        with st.container(border=True):
            st.markdown("#### 공학적 가치")
            st.markdown(
                "- **스킬 플러그인 아키텍처** — 필요한 모듈만 선택 사용\n"
                "- **`@tool` 데코레이터** — Python 메서드를 LLM 함수로 자동 변환\n"
                "- **환경 라우터 추상화** — ReAct/PlanExecute/CodeGen 호환 교체"
            )

    st.markdown("##### 활용 시나리오")
    u1, u2, u3, u4, u5 = st.columns(5)
    u1.info("**정책 사전 시뮬레이션**\n\n세금·복지·도시계획")
    u2.info("**마케팅·미디어 연구**\n\n콘텐츠 전파·여론 형성")
    u3.info("**재난 대응 계획**\n\n대피·필수인력 배치")
    u4.info("**교육·훈련**\n\n사회 현상 가시화")
    u5.info("**AI 안전성 연구**\n\n집단 창발 행동 관찰")

    st.markdown("")

    # Section 5: Project differences
    st.markdown("## 본 재구현 프로젝트의 특징")

    comparison = [
        {"항목": "Python 호환성", "원본 agentsociety2": "3.10 ~ 3.13", "본 프로젝트 (lite)": "3.14 호환"},
        {"항목": "LLM 백엔드", "원본 agentsociety2": "litellm (2026.03 공급망 공격)", "본 프로젝트 (lite)": "google-genai 직접 호출"},
        {"항목": "의존성", "원본 agentsociety2": "45+ 패키지 (torch, faiss 등)", "본 프로젝트 (lite)": "9개 핵심 패키지"},
        {"항목": "인터페이스", "원본 agentsociety2": "CLI + React GUI", "본 프로젝트 (lite)": "Streamlit 통합 UI"},
        {"항목": "목적", "원본 agentsociety2": "대규모 분산 시뮬레이션", "본 프로젝트 (lite)": "교육·탐색·빠른 프로토타이핑"},
    ]
    st.dataframe(comparison, hide_index=True, use_container_width=True)

    st.markdown("")

    # Section 6: What you can experience
    st.markdown("## 앱에서 체험할 수 있는 것")

    b1, b2, b3, b4 = st.columns(4)
    with b1:
        with st.container(border=True):
            st.markdown("##### Basics")
            st.caption("3 예제")
            st.markdown("- Hello Agent\n- Custom Env\n- Replay System")
    with b2:
        with st.container(border=True):
            st.markdown("##### Advanced")
            st.caption("2 예제")
            st.markdown("- Custom Agent\n- Multi-Router")
    with b3:
        with st.container(border=True):
            st.markdown("##### Games")
            st.caption("3 예제")
            st.markdown("- Prisoner's Dilemma\n- Public Goods\n- Reputation Game")
    with b4:
        with st.container(border=True):
            st.markdown("##### Paper Experiments")
            st.caption("4 실험")
            st.markdown("- Polarization\n- Inflammatory\n- UBI\n- Hurricane")

    st.caption(
        "각 예제 페이지 상단의 **이 예제에 대하여**를 펼치면 "
        "논문 대응 섹션, 원본 코드 위치, 동작 원리, 해결하는 문제를 확인할 수 있습니다."
    )

    st.divider()

    # Footer
    with st.container(border=True):
        st.markdown(
            "**Quick Start** — 사이드바에서 Gemini API Key 입력 → 원하는 예제 선택 → 실행\n\n"
            "**참고** — 논문 [arXiv:2502.08691](https://arxiv.org/abs/2502.08691) · "
            "[원본 코드](https://github.com/tsinghua-fib-lab/AgentSociety) · "
            "[본 프로젝트 코드](https://github.com/sapiensqinc/AgentSociety_mini_reinterpretation)"
        )

st.set_page_config(
    page_title="AgentSociety Mini Reinterpretation",
    page_icon="AS",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session()

# --- Sidebar ---
st.sidebar.title("AgentSociety Mini Reinterpretation")
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

# API Key input — BYOK (Bring Your Own Key) enforcement
st.sidebar.markdown("---")
st.sidebar.markdown("### Gemini API Key")
st.sidebar.caption(
    "이 앱은 **BYOK** 방식으로 동작합니다. "
    "서버에 저장된 키가 없으며 사용자 본인의 키만 사용됩니다."
)
api_key = st.sidebar.text_input(
    "API Key",
    value=get_api_key(),
    type="password",
    help="https://aistudio.google.com/apikey 에서 무료로 발급",
    label_visibility="collapsed",
)
if api_key:
    set_api_key(api_key)
    st.sidebar.success("API Key 입력됨 (세션 메모리에만 저장)")
else:
    st.sidebar.warning("API Key 입력 필요")

st.sidebar.markdown("---")
st.sidebar.caption(
    "Based on [AgentSociety](https://arxiv.org/abs/2502.08691) paper.  \n"
    "No litellm, no server-side key storage."
)

# --- Main Content ---
if category == "Home" or page is None:
    _render_home()

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
