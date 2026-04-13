# 03. Replay System - UI Design & Scenario

## Overview

ReplayWriter를 사용해 에이전트 상호작용을 SQLite DB에 기록하고, 이를 타임라인 형태로 재생하는 예제.

## Scenario (시나리오)

1. **에이전트 생성**: Agent1(friendly), Agent2(curious), Agent3(friendly) — 3명
2. **환경**: SimpleSocialSpace (에이전트 이름 목록 공유)
3. **리플레이 설정**: `ReplayWriter` → `example_replay.db`
4. **상호작용 실행**:
   - Agent1에게 자기소개 요청
   - Agent2에게 자기소개 요청
   - Agent3에게 자기소개 요청
5. **재생**: DB에서 기록된 상호작용을 시간순으로 탐색

## UI Design

```
┌─────────────────────────────────────────────────────┐
│  Replay System                                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Controls                                           │
│  ┌─────────────────────────────────────────────┐   │
│  │ [⏮ First] [◀ Prev] [▶ Play] [Next ▶] [Last ⏭] │ │
│  │                                              │   │
│  │  Step: ●───────○───────○───────○──────○      │   │
│  │        1       2       3       4      5      │   │
│  │                                              │   │
│  │  Speed: [1x ▼]                               │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌──────────────────┬──────────────────────────┐   │
│  │  Agent Status     │  Interaction Detail      │   │
│  │                   │                          │   │
│  │  Agent1 ● active  │  Step 2 of 5             │   │
│  │  Agent2 ● active  │                          │   │
│  │  Agent3 ○ waiting │  Prompt:                 │   │
│  │                   │  "Hello Agent2!           │   │
│  │  DB Stats:        │   Introduce yourself."   │   │
│  │  Records: 5       │                          │   │
│  │  Agents: 3        │  Response:               │   │
│  │  Duration: 12.3s  │  "Hi! I'm Agent2, and    │   │
│  │                   │  I have a curious nature. │   │
│  │                   │  I love exploring new     │   │
│  │                   │  ideas and asking..."     │   │
│  │                   │                          │   │
│  │                   │  Timestamp: 14:23:05     │   │
│  │                   │  Tokens: 142             │   │
│  └──────────────────┴──────────────────────────┘   │
│                                                     │
│  Timeline View                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │ Agent1  [██████]·····························│   │
│  │ Agent2  ·········[██████]····················│   │
│  │ Agent3  ····················[██████]··········│   │
│  │         ──────────────────────────────── t   │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Components

| Component | Streamlit Widget | Description |
|-----------|-----------------|-------------|
| Playback Controls | `st.button` x5 | 재생/정지/이동 |
| Step Slider | `st.slider` | 특정 단계로 이동 |
| Agent Status | `st.status` / colored dots | 에이전트별 활동 상태 |
| Interaction Detail | `st.container` | 현재 단계의 프롬프트/응답 |
| DB Stats | `st.metric` | 총 기록 수, 에이전트 수, 소요 시간 |
| Timeline | Custom HTML or `st.plotly_chart` (Gantt) | 에이전트별 활동 타임라인 |

### Key Learning Point

시뮬레이션 기록의 저장과 재생. DB에 저장된 데이터를 시각적으로 탐색하며, 어떤 순서로 에이전트가 활동했는지 파악 가능.

## Dependencies

- `google-genai`, `streamlit`
- `agentsociety2_lite` (ReplayWriter, SQLite)
- `plotly` (타임라인 차트)

## Branch

`examples-basics` — 파일: `examples/basics/03_replay_system.py`
