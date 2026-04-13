# 01. Hello Agent - UI Design & Scenario

## Overview

가장 기본적인 에이전트 시뮬레이션. 하나의 PersonAgent(Alice)를 생성하고 대화하는 예제.

## Scenario (시나리오)

1. **에이전트 생성**: Alice (28세, SF 거주, SW 엔지니어, 하이킹/SF소설/요리 좋아함)
2. **환경 구성**: SimpleSocialSpace (에이전트 이름 목록 제공)
3. **대화 진행**:
   - "What's the name of all agents?" → 환경에서 에이전트 목록 조회
   - "Tell me about Alice's personality and interests." → 프로필 기반 응답
   - "What agents exist in this simulation?" → 환경 상태 조회
4. **사용자 자유 질문**: 추가 질문 입력 가능

## UI Design

```
┌─────────────────────────────────────────────────┐
│  Sidebar                                        │
│  ┌───────────┐  ┌─────────────────────────────┐ │
│  │ Examples  │  │  Hello Agent                │ │
│  │ > Hello   │  │                             │ │
│  │   Agent   │  │  ┌─────────────────────┐    │ │
│  │   Custom  │  │  │ Agent Profile       │    │ │
│  │   Env     │  │  │ Name: Alice         │    │ │
│  │   Replay  │  │  │ Age: 28             │    │ │
│  │   ...     │  │  │ Location: SF        │    │ │
│  │           │  │  │ Personality:        │    │ │
│  │           │  │  │  friendly, curious  │    │ │
│  │           │  │  └─────────────────────┘    │ │
│  │           │  │                             │ │
│  │           │  │  --- Conversation ---       │ │
│  │           │  │                             │ │
│  │           │  │  You: What's the name of    │ │
│  │           │  │       all agents?           │ │
│  │           │  │                             │ │
│  │           │  │  Alice: The agents in this  │ │
│  │           │  │  simulation are: Alice.     │ │
│  │           │  │                             │ │
│  │           │  │  You: Tell me about Alice's │ │
│  │           │  │       personality...        │ │
│  │           │  │                             │ │
│  │           │  │  Alice: I'm a friendly and  │ │
│  │           │  │  curious person who loves   │ │
│  │           │  │  hiking, reading sci-fi...  │ │
│  │           │  │                             │ │
│  │           │  │  ┌─────────────────────┐    │ │
│  │           │  │  │ Ask a question...   │    │ │
│  │           │  │  └─────────────────────┘    │ │
│  └───────────┘  └─────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### Components

| Component | Streamlit Widget | Description |
|-----------|-----------------|-------------|
| Agent Profile Card | `st.expander` / `st.info` | 에이전트 프로필 정보 표시 |
| Conversation History | `st.chat_message` | user/assistant 역할별 메시지 |
| Input Box | `st.chat_input` | 사용자 자유 질문 입력 |
| Preset Questions | `st.button` x3 | 시나리오 기본 질문 버튼 |

### Interaction Flow

1. 페이지 로드 시 Alice 프로필 카드 표시
2. 기본 질문 3개를 버튼으로 제공 (원래 시나리오)
3. 버튼 클릭 또는 자유 입력 → LLM 호출 → 응답 표시
4. 대화 히스토리 `st.session_state`에 유지

## Dependencies

- `google-genai` (Gemini API)
- `streamlit`
- `agentsociety2_lite` (경량 코어)

## Branch

`examples-basics` — 파일: `examples/basics/01_hello_agent.py`
