# 01. Prisoner's Dilemma - UI Design & Scenario

## Overview

고전 게임이론 시나리오. 두 에이전트(Alice, Bob)가 서로 격리된 상태에서 협력/배신을 선택.

## Scenario (시나리오)

### 게임 규칙
| | Bob: Cooperate | Bob: Defect |
|---|:---:|:---:|
| **Alice: Cooperate** | 1년, 1년 | 5년, 0년 |
| **Alice: Defect** | 0년, 5년 | 3년, 3년 |

- `cooperate_reward=1` — 둘 다 협력 시 각 1년
- `defect_punishment=1` — 둘 다 배신 시 각 3년 (base + punishment)
- `temptation=3` — 배신 유혹 (상대 협력 시 석방)
- `sucker_punishment=3` — 호구 벌칙 (상대 배신 시 5년)

### 에이전트 성격
- **Alice**: strategic and rational (전략적, 이성적)
- **Bob**: trusting but cautious (신뢰하지만 조심스러움)

### 실행 흐름
1. Alice에게 상황 설명 → COOPERATE/DEFECT 결정 + 근거
2. Bob에게 상황 설명 → COOPERATE/DEFECT 결정 + 근거
3. 결과 계산 (보수 매트릭스 적용)
4. Alice에게 결과 공개 → 회고 ("같은 선택을 하겠는가?")

## UI Design

```
┌─────────────────────────────────────────────────────────┐
│  Prisoner's Dilemma                                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Game Setup                                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Cooperate Reward: [1] Defect Punishment: [1]    │   │
│  │ Temptation:       [3] Sucker Punishment: [3]    │   │
│  │ [Run Game]                                      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Payoff Matrix                                          │
│  ┌───────────────────────────────────────┐             │
│  │              Bob                      │             │
│  │          Cooperate    Defect          │             │
│  │  Alice  ┌──────────┬──────────┐      │             │
│  │  Coop   │  -1, -1  │  -5,  0  │      │             │
│  │  Defect │   0, -5  │ [-3, -3] │ ← ●  │             │
│  │         └──────────┴──────────┘      │             │
│  └───────────────────────────────────────┘             │
│                                                         │
│  ┌─────────────────────┬───────────────────────┐       │
│  │  Alice               │  Bob                  │       │
│  │  "strategic, rational"│ "trusting, cautious"  │       │
│  │                      │                       │       │
│  │  Decision: DEFECT    │  Decision: DEFECT     │       │
│  │                      │                       │       │
│  │  Reasoning:          │  Reasoning:           │       │
│  │  "Rationally, the    │  "While I value       │       │
│  │  dominant strategy   │  trust, I can't risk  │       │
│  │  is to defect..."    │  being the sucker..." │       │
│  │                      │                       │       │
│  │  Sentence: 3 years   │  Sentence: 3 years    │       │
│  └─────────────────────┴───────────────────────┘       │
│                                                         │
│  Result: Both DEFECTED (Nash Equilibrium)               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Alice's Reflection:                              │   │
│  │ "Looking at the outcome, we both got 3 years.   │   │
│  │  If we had both cooperated, we'd only get 1     │   │
│  │  year each. But I couldn't trust that Bob       │   │
│  │  would cooperate..."                            │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Outcome History (if multiple runs)                     │
│  Run 1: Both Defect (3,3) | Run 2: ... | Run 3: ...   │
└─────────────────────────────────────────────────────────┘
```

### Components

| Component | Streamlit Widget | Description |
|-----------|-----------------|-------------|
| Game Setup | `st.number_input` x4 | 보수 매트릭스 파라미터 조정 |
| Payoff Matrix | `st.table` + conditional highlighting | 결과 셀 하이라이트 |
| Agent Cards | `st.columns(2)` | Alice/Bob 나란히 |
| Decision | `st.warning`/`st.success` | COOPERATE=초록, DEFECT=빨강 |
| Reasoning | `st.expander` | 에이전트의 의사결정 근거 |
| Reflection | `st.info` | 사후 회고 |
| History | `st.line_chart` | 반복 게임 시 결과 추이 |

### Key Learning Point

내쉬 균형과 파레토 최적의 괴리. 개별 합리성이 집단 최적해를 방해하는 사회적 딜레마.

## Dependencies

- `google-genai`, `streamlit`
- `agentsociety2_lite` (PersonAgent, AgentSociety)

## Branch

`examples-games` — 파일: `examples/games/01_prisoners_dilemma.py`
