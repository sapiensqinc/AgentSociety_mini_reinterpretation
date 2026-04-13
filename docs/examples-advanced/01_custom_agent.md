# 01. Custom Agent - UI Design & Scenario

## Overview

AgentBase를 상속해 커스텀 에이전트를 만드는 예제. SpecialistAgent(전문 분야 컨텍스트 주입)와 RecursiveAgent(Chain-of-Thought 재귀 추론)를 시연.

## Scenario (시나리오)

### Part 1: SpecialistAgent
1. **Dr. Climate** 생성 (전문분야: climate science and environmental policy)
2. 질문: "What should cities do to prepare for extreme weather?"
3. → 전문 분야 컨텍스트가 자동 주입된 응답

### Part 2: Specialist Reflection
1. **Dr. Science** 생성 (전문분야: environmental science)
2. 커스텀 메서드 `reflect_on_specialty()` 호출
3. → "As a specialist in X, what are the most important aspects?"

### Part 3: RecursiveAgent (CoT)
1. **Deep Thinker** 생성 (analytical and methodical)
2. 질문: "How can we reduce urban traffic congestion?"
3. → 질문 분해 (sub-questions) → 개별 답변 → 종합 (depth=2)

## UI Design

```
┌─────────────────────────────────────────────────────────┐
│  Custom Agent Examples                                  │
│                                                         │
│  [Specialist] [Reflection] [Recursive CoT]  ← tabs     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─ Specialist Agent ─────────────────────────────────┐ │
│  │                                                     │ │
│  │  Agent: Dr. Climate                                 │ │
│  │  Specialty: climate science & environmental policy  │ │
│  │  Personality: scientific and concerned              │ │
│  │                                                     │ │
│  │  ┌─ Question ────────────────────────────────────┐ │ │
│  │  │ What should cities do to prepare for extreme  │ │ │
│  │  │ weather?                                      │ │ │
│  │  └───────────────────────────────────────────────┘ │ │
│  │                                                     │ │
│  │  ┌─ Internal Enhancement ──────── (expandable) ──┐ │ │
│  │  │ "You are a specialist in climate science and  │ │ │
│  │  │  environmental policy. Answer the following   │ │ │
│  │  │  question from this perspective: ..."         │ │ │
│  │  └───────────────────────────────────────────────┘ │ │
│  │                                                     │ │
│  │  ┌─ Response ────────────────────────────────────┐ │ │
│  │  │ Cities should invest in resilient infra-      │ │ │
│  │  │ structure, improve drainage systems, create   │ │ │
│  │  │ urban cooling zones with green roofs...       │ │ │
│  │  └───────────────────────────────────────────────┘ │ │
│  │                                                     │ │
│  │  Time: 1.2s  |  Tokens: 345                        │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                         │
│  ── vs Recursive CoT ──────────────────────────────── │
│                                                         │
│  ┌─ Recursive Agent (CoT, depth=2) ──────────────────┐ │
│  │                                                     │ │
│  │  Agent: Deep Thinker                                │ │
│  │  Question: "How can we reduce urban traffic         │ │
│  │            congestion?"                             │ │
│  │                                                     │ │
│  │  Step 1: Decompose                                  │ │
│  │  ┌───────────────────────────────────────────────┐ │ │
│  │  │ Sub-Q1: What causes urban traffic congestion? │ │ │
│  │  │ Sub-Q2: What public transit solutions exist?  │ │ │
│  │  │ Sub-Q3: How can technology reduce traffic?    │ │ │
│  │  └───────────────────────────────────────────────┘ │ │
│  │                                                     │ │
│  │  Step 2: Answer Each         (expandable per Q)     │ │
│  │  ▶ Sub-Q1 → "Congestion is caused by..."           │ │
│  │  ▶ Sub-Q2 → "Bus rapid transit, subway..."         │ │
│  │  ▶ Sub-Q3 → "Smart traffic signals, ride-share..." │ │
│  │                                                     │ │
│  │  Step 3: Synthesize                                 │ │
│  │  ┌───────────────────────────────────────────────┐ │ │
│  │  │ Based on the above analysis, reducing urban   │ │ │
│  │  │ traffic congestion requires a multi-pronged   │ │ │
│  │  │ approach: improving public transit, leveraging│ │ │
│  │  │ technology, and addressing root causes...     │ │ │
│  │  └───────────────────────────────────────────────┘ │ │
│  │                                                     │ │
│  │  Time: 4.8s  |  Tokens: 1,230  |  LLM Calls: 5    │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                         │
│  ┌─ Comparison ───────────────────────────────────────┐ │
│  │  Metric         Specialist    Recursive CoT        │ │
│  │  Response Time   1.2s          4.8s                 │ │
│  │  Tokens          345           1,230                │ │
│  │  LLM Calls       1             5                    │ │
│  │  Depth            shallow       deep (multi-step)  │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Components

| Component | Streamlit Widget | Description |
|-----------|-----------------|-------------|
| Agent Tabs | `st.tabs` | Specialist / Reflection / Recursive 전환 |
| Agent Card | `st.info` | 에이전트 프로필 요약 |
| Internal Enhancement | `st.expander` | ask() 오버라이드로 변환된 실제 프롬프트 |
| CoT Decomposition | `st.expander` per sub-Q | 분해된 하위 질문과 개별 답변 |
| Synthesis | `st.success` | 최종 종합 답변 |
| Comparison Table | `st.dataframe` | 시간/토큰/호출수 비교 |

### Key Learning Point

AgentBase 상속을 통한 에이전트 커스터마이징 패턴. `ask()` 오버라이드, 커스텀 메서드 추가, 재귀적 추론 구현.

## Dependencies

- `google-genai`, `streamlit`, `json-repair`
- `agentsociety2_lite` (AgentBase, SimpleSocialSpace, AgentSociety)

## Branch

`examples-advanced` — 파일: `examples/advanced/01_custom_agent.py`
