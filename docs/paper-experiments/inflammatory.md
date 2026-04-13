# Paper: Inflammatory Messages Experiment (Section 7.3) - UI Design & Scenario

## Overview

선동적 메시지의 소셜 미디어 확산 실험 재현. 일반 메시지 vs 선동적 메시지의 확산 속도/범위를 비교하고, 노드/엣지 개입(moderation)의 효과를 측정.

## Paper Reference

- **논문**: arXiv:2502.08691, Section 7.3
- **모티프**: 쉬저우 체인우먼 사건 기반 정보 확산
- **원래 실험 결과**:
  - 선동적 메시지 > 일반 메시지 (확산 속도, 감정 강도)
  - 노드 개입(계정 정지) > 엣지 개입(연결 제거) (억제 효과)

## Scenario (시나리오)

### 네트워크 구성
- **12명 에이전트**: User_1 ~ User_12
- **소셜 네트워크**: 에이전트당 4명의 친구 (소규모 세계 네트워크)
- **시드 에이전트**: User_1, User_2 (최초 정보 보유자)

### 두 종류의 메시지
| 유형 | 메시지 | 초기 감정 |
|------|--------|----------|
| **일반** | "A woman was found in difficult circumstances in a rural village. Authorities are investigating." | 0.2 |
| **선동적** | "SHOCKING: Woman found chained in village! Government cover-up! Share before they delete this!" | 0.6 |

### 4가지 실험 조건
| 조건 | 메시지 유형 | 개입 | 설명 |
|------|-----------|------|------|
| Control | 일반 | 없음 | 기준선 |
| Experimental | 선동적 | 없음 | 선동 효과 측정 |
| Node Intervention | 선동적 | 2회 이상 선동 공유 시 계정 정지 | 노드 제거 |
| Edge Intervention | 선동적 | 선동 메시지 전달 경로 차단 | 엣지 제거 |

### 실행 흐름 (조건당 4 스텝)
1. 시드 에이전트에게 메시지 전달 + 감정 설정
2. 각 스텝: 정보 보유 에이전트에게 공유 결정 질의 → YES/NO + 감정 수치
3. 공유 시 친구 2명에게 전달 (개입 조건에 따라 차단될 수 있음)
4. 스텝별 확산률/감정 기록

## UI Design

```
┌─────────────────────────────────────────────────────────┐
│  Inflammatory Messages Experiment (Paper Section 7.3)   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Condition: [Control] [Experimental] [Node] [Edge]     │
│  Network Size: [12]  Steps: [4]  [Run All]             │
│                                                         │
│  ┌─ Network Spread ──────────┬─ Metrics ──────────────┐│
│  │                           │                         ││
│  │  Step: [1] [2] [●3] [4]  │  Spread Over Time       ││
│  │                           │  100%┤         ___      ││
│  │     ◉──→●                 │      │       /          ││
│  │    ↙     ↘                │   50%┤     /            ││
│  │   ●       ○               │      │   /              ││
│  │  ↙ ↘      ↑               │    0%└──────────        ││
│  │ ●   ○     ○               │      s1  s2  s3  s4    ││
│  │  ↓                        │                         ││
│  │  ○                        │  Avg Emotion            ││
│  │                           │  1.0┤     _  _          ││
│  │  ◉ = seed  ● = informed  │     │   /  \/           ││
│  │  ○ = uninformed           │  0.5┤  /                ││
│  │  🚫 = banned              │     │ /                 ││
│  │  ╳ = edge removed        │  0.0└──────────         ││
│  │                           │      s1  s2  s3  s4    ││
│  └───────────────────────────┴─────────────────────────┘│
│                                                         │
│  Four-Condition Comparison                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │                Spread     Emotion   Msgs  Banned │   │
│  │  Control       42%        0.15      8     0     │   │
│  │  Experimental  83%        0.45      22    0     │   │
│  │  Node Interv.  58%        0.30      15    3     │   │
│  │  Edge Interv.  67%        0.35      18    0     │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  Paper: inflammatory > control (spread+emotion) │   │
│  │  Paper: node intervention > edge intervention   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Agent Decision Log (expandable)                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Step 2, User_3:                                  │   │
│  │   Received: "SHOCKING: Woman found chained..."   │   │
│  │   Emotion: 0.6 → 0.8                            │   │
│  │   Decision: YES (share)                          │   │
│  │   "I feel compelled to share this because..."    │   │
│  │   → Shared to: User_5, User_8                   │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Components

| Component | Streamlit Widget | Description |
|-----------|-----------------|-------------|
| Condition Tabs | `st.radio` | 4조건 전환 |
| Network Graph | `pyvis` / Plotly scatter | 확산 상태 애니메이션 (색상=상태) |
| Step Slider | `st.slider` | 시간 단계별 탐색 |
| Dual Chart | Plotly (2-axis) | 확산률 + 감정 강도 시계열 |
| Comparison Table | `st.dataframe` + highlighting | 4조건 최종 비교 |
| Decision Log | `st.expander` per agent per step | 에이전트 결정 과정 |

## Dependencies

- `google-genai`, `streamlit`, `plotly`, `pyvis`
- `agentsociety2_lite` (PersonAgent, EnvBase, @tool, AgentSociety)

## Branch

`paper-inflammatory` — 파일: `examples/paper_experiments/inflammatory_messages/run_inflammatory.py`
