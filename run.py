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
    st.caption("LLM 기반 사회 시뮬레이션의 재현 및 실험 플랫폼 — arXiv:2502.08691 기반")

    st.markdown("""
## 이 프로젝트는 무엇을 다루나

AgentSociety는 **LLM 기반 생성 에이전트로 사람의 행동과 사회 현상을 대규모로 시뮬레이션**하는
칭화대학교의 연구 프로젝트입니다. 본 저장소는 해당 논문과 코드베이스의 핵심을 재현하고,
연구자·개발자가 Python 3.14 + Gemini API만으로 즉시 실험할 수 있도록 경량화한 플랫폼입니다.

---

## AgentSociety가 해결하려는 문제

### 사회과학의 근본적 딜레마
- **실제 사회 실험은 비용, 윤리, 규모의 장벽으로 실행 불가능한 경우가 많음**
  - UBI(기본소득) 정책을 10만 명에게 3년간 지급하고 우울증 변화를 측정? → 현실에서 불가능
  - 허리케인이 닥치기 전에 주민 대피 정책을 사전 검증? → 한 번뿐인 자연재해
  - 선동적 메시지가 소셜 미디어에서 어떻게 확산되는가? → 실시간 관찰과 개입의 한계
- **기존 에이전트 기반 모델(ABM)의 한계**
  - 에이전트 행동이 수식·규칙으로 단순화되어 인간의 복잡한 인지·감정·사회적 맥락을 반영하지 못함
  - 한 번 세팅한 규칙으로는 새로운 시나리오에 대한 일반화가 어려움

### 기존 LLM 에이전트 연구의 한계
- **소규모(수십 명 수준)에 머무름** — Generative Agents(스탠퍼드, 2023)는 25명 규모
- **단편적 실험에 그침** — 하나의 시나리오만 다루고 재현성·확장성이 낮음
- **사회 인프라 부재** — 도시 공간, 경제 시스템, 대규모 네트워크 통합이 없음

---

## 착안점: 세 가지 축의 통합

AgentSociety는 아래 **세 요소를 하나의 프레임워크로 통합**했다는 점이 핵심 기여입니다.

| 축 | 내용 | 근거 섹션 |
|----|------|:---:|
| **LLM 기반 생성 에이전트** | 감정(Emotion)-욕구(Needs)-인지(Cognition) 계층으로 인간다운 의사결정 | Sec 3 |
| **현실 반영 사회 환경** | 도시공간(OSM·SafeGraph), 사회공간(SNS·평판), 경제공간(DSGE) | Sec 4 |
| **대규모 시뮬레이션 엔진** | Ray 분산, MQTT 메시징, 10,000+ 에이전트 500만 상호작용 | Sec 5 |

### 왜 이 결합이 의미 있는가
- **LLM만으로는 환경이 없음** → 감정적 판단은 가능하나 경제·지리적 맥락이 빠짐
- **ABM만으로는 인간다움이 없음** → 규모는 커도 결정이 단순함
- **LLM + 환경 + 엔진의 결합이 처음으로 "사회적 실재감"을 재현 가능하게 만듦**

---

## 해결 방향: 논문 Section 7의 네 가지 실험

논문은 네 가지 대표 사회 실험으로 프레임워크의 실증적 가치를 입증했습니다.

1. **Polarization (7.2)** — 의견 양극화가 에코 챔버에서 강화되고 교차 노출에서 완화됨을 확인
2. **Inflammatory Messages (7.3)** — 선동 콘텐츠의 확산 가속과 모더레이션 전략별 효과 비교
3. **UBI (7.4)** — 기본소득 정책이 소비·저축·웰빙에 미치는 다차원 영향 계산
4. **Hurricane (7.5)** — 외부 충격(자연재해) 시 이동성 변화를 실제 SafeGraph 데이터와 대조

네 실험 모두 **"실제로는 수행이 불가능하거나 비싼 사회 실험"의 사전 시뮬레이션**이라는 공통점이 있습니다.

---

## 이 논문·GitHub이 가지는 가치

### 학술적 가치
- 계산사회과학(Computational Social Science)의 새로운 방법론 제시
- 정책 결정 이전에 가상 실험을 수행하는 **정책 실험실(policy sandbox)** 가능성
- 인문·사회과학과 AI의 융합 연구를 위한 공통 플랫폼

### 공학적 가치
- **스킬 기반 플러그인 아키텍처 (v2)** — 연구자가 고정 파이프라인이 아닌 필요한 모듈만 선택 사용
- **`@tool` 데코레이터 패턴** — Python 메서드를 LLM 호출 가능한 함수로 자동 변환
- **환경 라우터 추상화** — ReAct, PlanExecute, CodeGen 등 추론 전략을 호환 교체 가능

### 활용 시나리오
- **정책 사전 시뮬레이션** — 세금·복지·도시계획 정책의 사회적 영향 예측
- **마케팅/미디어 연구** — 콘텐츠 전파·여론 형성 동태 실험
- **재난 대응 계획** — 대피 경로·필수 인력 배치의 사전 검증
- **교육·훈련** — 사회 현상에 대한 학생·의사결정자의 직관을 돕는 가시화 도구
- **AI 안전성 연구** — LLM 에이전트 집단의 창발 행동(collective emergent behavior) 관찰

---

## 이 재구현 프로젝트의 특징

본 저장소는 원본과 다음 지점에서 차이를 둡니다.

| 항목 | 원본 agentsociety2 | 본 프로젝트 (agentsociety2_lite) |
|------|---|---|
| Python 호환성 | 3.10 ~ 3.13 | **3.14 호환** |
| LLM 백엔드 | litellm (2026.03 공급망 공격 이슈) | **google-genai 직접 호출** (보안 강화) |
| 의존성 | 45+ 패키지 (torch, mineru, faiss 등) | **9개 핵심 패키지** |
| 인터페이스 | CLI + React GUI | **Streamlit 통합 UI** (사이드바 탐색) |
| 목적 | 대규모 분산 시뮬레이션 | **교육·탐색·빠른 프로토타이핑** |

---

## 이 앱에서 직접 체험할 수 있는 것

왼쪽 사이드바에서 카테고리와 예제를 선택해 **즉시 실행**해볼 수 있습니다.

- **Basics** — 에이전트 생성, 환경 모듈, 기록·재생의 기초 개념
- **Advanced** — 커스텀 에이전트 설계, 라우터 전략 비교 (ReAct vs PlanExecute vs CodeGen)
- **Games** — 게임이론 실험 (죄수의 딜레마, 공공재, 평판 게임)
- **Paper Experiments** — 논문 4대 실험의 직접 재현 (7.2 ~ 7.5)

각 예제 페이지 상단의 "이 예제에 대하여"를 펼치면 해당 실험의
**논문 대응 섹션, 원본 코드 위치, 동작 원리, 해결하는 문제**를 확인할 수 있습니다.

---

> **Quick Start**: 사이드바에서 Gemini API Key 입력 → 원하는 예제 선택 → 실행
>
> **참고**: 논문 arXiv:2502.08691 · [원본 코드](https://github.com/tsinghua-fib-lab/AgentSociety) · [본 프로젝트 코드](https://github.com/sapiensqinc/AgentSociety_Replica)
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
