# 03. Reputation Game - UI Design & Scenario

## Overview

간접 상호성(indirect reciprocity) 기반 평판 게임. 10명의 에이전트가 사회 규범에 따라 협력/배신하며, 평판이 진화하는 과정을 관찰.

## Scenario (시나리오)

### 게임 설정
- **Z=10**: 종군 크기 (에이전트 수)
- **BENEFIT=5**: 협력 시 수혜자가 받는 이익
- **COST=1**: 협력 시 기여자가 지불하는 비용
- **norm_type="stern_judging"**: 사회 규범 유형
  - `image_score`: 단순 점수 (협력=+1, 배신=-1)
  - `simple_standing`: 좋은 평판인 상대에 협력하면 좋은 평판 유지
  - `stern_judging`: 엄격한 판단 — 나쁜 평판인 상대에 배신해도 좋은 평판

### 에이전트 성격 (8종 랜덤 배정)
- rational/cautious, emotional, fair-minded, altruistic
- selfish, vengeful, optimistic, pessimistic

### 사회 규범별 평판 규칙 (Stern Judging)
| 기여자 행동 | 수혜자 평판 | 결과 평판 |
|------------|-----------|----------|
| Cooperate | Good | Good |
| Cooperate | Bad | Bad |
| Defect | Good | Bad |
| Defect | Bad | Good |

### 실행 흐름
1. 에이전트 10명 생성 (LLMDonorAgent + mem0 메모리)
2. 매 틱마다 무작위 쌍 매칭 → 기여 결정
3. 사회 규범에 따라 평판 업데이트
4. 일정 주기마다 학습 (learning_frequency=5)
5. 시뮬레이션 종료 후 통계 분석

### 알려진 이슈
- `society = AgentSociety(config=config, ...)` — `config` 변수 미정의 (버그)
- mem0 + litellm Router 의존 — 별도 설정 필요

## UI Design

```
┌─────────────────────────────────────────────────────────┐
│  Reputation Game                                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Config                                                 │
│  Z: [10]  Benefit: [5]  Cost: [1]                      │
│  Norm: [stern_judging ▼]  Steps: [15]  [Run]           │
│                                                         │
│  ┌─────────────────────────┬───────────────────────┐   │
│  │  Agent Network           │  Cooperation Rate     │   │
│  │                          │                       │   │
│  │      ●G───●G             │ 100%┤        ___      │   │
│  │     / \    |             │     │      /          │   │
│  │   ●B   ●G──●B           │  50%┤─────/           │   │
│  │    \  / \   |            │     │   /             │   │
│  │     ●G───●B              │   0%└────────────     │   │
│  │      \   /               │     0   5   10  step │   │
│  │       ●G                 │                       │   │
│  │                          │                       │   │
│  │  ● Good (green)          │  Current η: 72.5%     │   │
│  │  ● Bad (red)             │                       │   │
│  └─────────────────────────┴───────────────────────┘   │
│                                                         │
│  ┌─────────────────────────┬───────────────────────┐   │
│  │  Reputation Distribution │  Leaderboard          │   │
│  │                          │                       │   │
│  │  Good ████████████ 70%  │  1. Agent3  +12.0    │   │
│  │  Bad  █████ 30%         │  2. Agent7  +10.5    │   │
│  │                          │  3. Agent0   +9.0    │   │
│  │  Step [●○○○○]           │  4. Agent5   +7.5    │   │
│  │  Good 7→8→7→8→8         │  ...                  │   │
│  │  Bad  3→2→3→2→2         │  10. Agent4  -2.0    │   │
│  └─────────────────────────┴───────────────────────┘   │
│                                                         │
│  Strategy Convergence                                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Trend: Increasing cooperation                    │   │
│  │ Convergence: Approaching stable state           │   │
│  │ Analysis: Under stern_judging norm, agents      │   │
│  │ learn that discriminating based on reputation    │   │
│  │ is the optimal strategy...                      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Recent Interactions (expandable)                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Step 14: Agent2(G) → Agent5(B): DEFECT          │   │
│  │ Step 14: Agent7(G) → Agent0(G): COOPERATE       │   │
│  │ Step 13: Agent1(B) → Agent3(G): DEFECT          │   │
│  │ ...                                             │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Components

| Component | Streamlit Widget | Description |
|-----------|-----------------|-------------|
| Config Panel | `st.number_input`, `st.selectbox` | 게임 파라미터 |
| Agent Network | `pyvis` or `plotly` scatter | 평판 기반 네트워크 (색상=평판) |
| Cooperation Chart | `st.line_chart` | 시계열 합작률 |
| Reputation Dist | `st.bar_chart` | Good/Bad 분포 추이 |
| Leaderboard | `st.dataframe` (sorted) | 수익 기준 순위 |
| Convergence | `st.info` | 전략 수렴 분석 텍스트 |
| Interaction Log | `st.expander` | 최근 상호작용 기록 |

### Key Learning Point

간접 상호성에서 사회 규범이 협력 진화에 미치는 영향. Stern Judging이 Image Score보다 높은 협력률을 유도하는 이유.

## Dependencies

- `google-genai`, `streamlit`, `plotly`, `pyvis`
- `agentsociety2_lite` (AgentBase, EnvBase, AgentSociety)
- Note: 원본은 mem0 의존 → 경량 버전에서는 dict 기반 메모리로 대체

## Branch

`examples-games` — 파일: `examples/games/03_reputation_game.py`

## Known Issues

1. **Bug**: `config` 변수 미정의 — `AgentSociety(config=config, ...)` 에서 NameError
2. **Heavy deps**: mem0, litellm.Router — 경량 버전에서 대체 필요
