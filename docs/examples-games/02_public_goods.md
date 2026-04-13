# 02. Public Goods Game - UI Design & Scenario

## Overview

4명의 에이전트가 공공재에 기여하는 경제 실험. 기여금 합계에 배수를 곱해 균등 분배.

## Scenario (시나리오)

### 게임 규칙
- **Endowment**: $100 (각 에이전트 초기 보유금)
- **Contribution Factor**: 1.5x (총 기여금에 곱하는 배수)
- **Rounds**: 3라운드 반복
- **공식**: 수익 = (보유금 - 기여금) + (총기여금 × 1.5 / 4)

### 에이전트 성격 (기여 전략에 영향)
| Agent | Personality | 예상 행동 |
|-------|------------|----------|
| Alice | altruistic, community-minded | 높은 기여 |
| Bob | self-interested, rational | 낮은 기여 (무임승차) |
| Charlie | cautious, skeptical | 중간, 관망 |
| Diana | optimistic, trusting | 높은 기여 |

### 실행 흐름
1. 각 라운드마다 4명에게 기여액 결정 요청
2. 기여금 합산 → 배수 적용 → 균등 분배
3. 개인별 수익 계산
4. 3라운드 후 최종 회고

## UI Design

```
┌─────────────────────────────────────────────────────────┐
│  Public Goods Game                                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Settings                                               │
│  Endowment: [$100]  Factor: [1.5x]  Rounds: [3]       │
│  [Start Game]                                           │
│                                                         │
│  Round [1▼] of 3                                        │
│  ┌──────────┬──────────┬──────────┬──────────┐         │
│  │  Alice    │  Bob     │  Charlie  │  Diana   │         │
│  │  altruist │  selfish │  cautious │  optimist│         │
│  │           │          │           │          │         │
│  │  $80      │  $20     │  $50      │  $70     │         │
│  │  ████████ │  ██      │  █████    │  ███████ │         │
│  └──────────┴──────────┴──────────┴──────────┘         │
│                                                         │
│  Round Calculation                                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Total: $80+$20+$50+$70 = $220                   │   │
│  │ After 1.5x multiplier: $330                     │   │
│  │ Each receives: $330 / 4 = $82.50                │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Payoffs This Round                                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Alice:   $100 - $80 + $82.5 = $102.5  (+$2.5)  │   │
│  │ Bob:     $100 - $20 + $82.5 = $162.5  (+$62.5) │ ★ │
│  │ Charlie: $100 - $50 + $82.5 = $132.5  (+$32.5) │   │
│  │ Diana:   $100 - $70 + $82.5 = $112.5  (+$12.5) │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Contribution Trend (across rounds)                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │ $100│                                           │   │
│  │     │ ●Alice                                    │   │
│  │  $75│  \                                        │   │
│  │     │   \    ●Diana                             │   │
│  │  $50│    ●───●Charlie                           │   │
│  │     │                                           │   │
│  │  $25│        ●Bob                               │   │
│  │   $0└────────────────────                       │   │
│  │     R1      R2      R3                          │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Final Reflection                                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │ "The group could have done better if everyone   │   │
│  │ contributed more. Bob's free-riding strategy     │   │
│  │ gave him the highest payoff individually..."     │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Components

| Component | Streamlit Widget | Description |
|-----------|-----------------|-------------|
| Settings | `st.number_input` x3 | 게임 파라미터 조정 |
| Round Selector | `st.selectbox` | 라운드별 결과 보기 |
| Contribution Bars | `st.columns(4)` + `st.progress` | 에이전트별 기여 비율 |
| Calculation | `st.info` | 당 라운드 계산 과정 |
| Payoff Table | `st.dataframe` + highlighting | 수익 (무임승차자 하이라이트) |
| Trend Chart | `st.line_chart` / Plotly | 라운드별 기여액 추이 |
| Reflection | `st.chat_message` | LLM의 최종 분석 |

### Key Learning Point

무임승차 문제(free-rider problem). 개인 이익 극대화(낮은 기여)가 집단 비효율을 야기하는 구조.

## Dependencies

- `google-genai`, `streamlit`, `plotly`
- `agentsociety2_lite` (PersonAgent, AgentSociety)

## Branch

`examples-games` — 파일: `examples/games/02_public_goods.py`
