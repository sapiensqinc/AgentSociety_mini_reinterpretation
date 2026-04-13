# 02. Multi-Router Comparison - UI Design & Scenario

## Overview

같은 질문을 3가지 라우터 전략(ReAct, PlanExecute, CodeGen)으로 처리하고 결과를 비교하는 예제.

## Scenario (시나리오)

### Test 1: 산술 문제
- 질문: "I have 10 apples. I give 3 to Alice and 2 to Bob. Then Alice gives me back 1. How many do I have?"
- 3개 라우터로 각각 처리하여 추론 과정과 정확도 비교

### Test 2: 복합 시나리오
- 질문: "Simulate a small auction where 3 people bid on an item. Start at $10, increment by $5, stop after 3 rounds."
- PlanExecute 라우터로 처리하여 다단계 계획-실행 시연

### Router 특성
| Router | 전략 | 적합한 상황 |
|--------|------|------------|
| **ReAct** | Think → Act → Observe → 반복 | 반복적 추론+행동이 필요한 태스크 |
| **PlanExecute** | Plan(전체 계획) → Execute(순차 실행) | 명확한 목표의 다단계 태스크 |
| **CodeGen** | Python 코드 생성 → 실행 | 계산/로직으로 풀 수 있는 태스크 |

## UI Design

```
┌─────────────────────────────────────────────────────────┐
│  Multi-Router Comparison                                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Question                                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ I have 10 apples. I give 3 to Alice and 2 to   │   │
│  │ Bob. Then Alice gives me back 1 apple. How many │   │
│  │ apples do I have now? Show your work.           │   │
│  └─────────────────────────────────────────────────┘   │
│  [Use preset ▼] [Run All Routers]                       │
│                                                         │
│  ┌───────────────┬───────────────┬───────────────┐     │
│  │ ReAct         │ PlanExecute   │ CodeGen       │     │
│  │ Think→Act     │ Plan→Execute  │ Generate Code │     │
│  ├───────────────┼───────────────┼───────────────┤     │
│  │               │               │               │     │
│  │ Answer: 6     │ Answer: 6     │ Answer: 6     │     │
│  │ Correct: Yes  │ Correct: Yes  │ Correct: Yes  │     │
│  │               │               │               │     │
│  │ Time: 2.1s    │ Time: 3.5s    │ Time: 1.8s    │     │
│  │ Tokens: 1,200 │ Tokens: 1,800 │ Tokens: 650   │     │
│  │ Steps: 4      │ Steps: 5      │ Steps: 2      │     │
│  │               │               │               │     │
│  └───────────────┴───────────────┴───────────────┘     │
│                                                         │
│  Token Usage Comparison                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ReAct      ████████████░░░░░░░░  1,200         │   │
│  │ PlanExec   ██████████████████░░  1,800         │   │
│  │ CodeGen    ██████░░░░░░░░░░░░░░    650         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Reasoning Trace (expandable per router)                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ▼ ReAct Trace                                   │   │
│  │   Thought: I need to track apple count...       │   │
│  │   Action: calculate(10 - 3 = 7)                 │   │
│  │   Observation: 7 apples remaining               │   │
│  │   Thought: Now subtract Bob's share...          │   │
│  │   Action: calculate(7 - 2 = 5)                  │   │
│  │   Observation: 5 apples                         │   │
│  │   Thought: Alice returns 1...                   │   │
│  │   Action: calculate(5 + 1 = 6)                  │   │
│  │   Final: 6 apples                               │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ ▶ PlanExecute Trace                             │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ ▶ CodeGen Trace                                 │   │
│  │   ```python                                     │   │
│  │   apples = 10                                   │   │
│  │   apples -= 3  # give to Alice                  │   │
│  │   apples -= 2  # give to Bob                    │   │
│  │   apples += 1  # Alice returns                  │   │
│  │   print(apples)  # 6                            │   │
│  │   ```                                           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Summary                                                │
│  - ReAct: Good for iterative reasoning and action      │
│  - PlanExecute: Good for complex multi-step tasks      │
│  - CodeGen: Good for computation-solvable tasks        │
└─────────────────────────────────────────────────────────┘
```

### Components

| Component | Streamlit Widget | Description |
|-----------|-----------------|-------------|
| Question Input | `st.text_area` + preset `st.selectbox` | 질문 입력 |
| Run Button | `st.button` | 3개 라우터 동시 실행 |
| Result Columns | `st.columns(3)` | 라우터별 결과 나란히 |
| Metrics | `st.metric` | 시간, 토큰, 정확도 |
| Token Bar Chart | `st.bar_chart` or Plotly | 토큰 사용량 비교 |
| Reasoning Trace | `st.expander` per router | 내부 추론 과정 상세 |

### Key Learning Point

같은 태스크를 다른 전략으로 접근할 때의 트레이드오프. 토큰 효율성 vs 추론 깊이 vs 정확도.

## Dependencies

- `google-genai`, `streamlit`, `plotly`
- `agentsociety2_lite` (ReActRouter, PlanExecuteRouter, CodeGenRouter)

## Branch

`examples-advanced` — 파일: `examples/advanced/02_multi_router.py`
