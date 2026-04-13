# 02. Custom Environment Module - UI Design & Scenario

## Overview

커스텀 환경 모듈(`WeatherEnvironment`)을 만들고, `@tool` 데코레이터로 LLM이 호출 가능한 도구를 정의하는 예제.

## Scenario (시나리오)

1. **환경 생성**: WeatherEnvironment (날씨, 온도, 에이전트 위치 관리)
2. **도구 등록**:
   - `get_weather(agent_id)` — 현재 날씨 조회 (readonly, observe)
   - `change_weather(weather, temperature)` — 날씨 변경 (write)
   - `set_agent_location(agent_id, location)` — 위치 설정 (write)
   - `get_average_temperature()` — 평균 온도 조회 (readonly, statistics)
3. **실행 흐름**:
   - Query: "What's the current weather and temperature?" → sunny, 25°C
   - Intervene: "Change the weather to rainy and set temperature to 18°C"
   - Query: "What's the current temperature?" → 18°C (변경 확인)

## UI Design

```
┌─────────────────────────────────────────────────────┐
│  Custom Environment Module                          │
├────────────────────────┬────────────────────────────┤
│                        │                            │
│  Environment State     │  Action Log                │
│  ┌──────────────────┐  │                            │
│  │ Weather: sunny   │  │  Step 1: Query             │
│  │ Temp: 25°C       │  │  > get_weather()           │
│  │                  │  │  Response: "The weather    │
│  │ Agent Locations: │  │  is sunny with 25°C"       │
│  │  Agent1: unknown │  │                            │
│  │  Agent2: unknown │  │  Step 2: Intervene         │
│  └──────────────────┘  │  > change_weather(         │
│                        │      "rainy", 18)          │
│  Manual Controls       │  Response: "Weather        │
│  ┌──────────────────┐  │  changed to rainy at 18°C" │
│  │ Weather: [rainy▼]│  │                            │
│  │ Temp: [18    ]   │  │  Step 3: Query             │
│  │ [Apply Change]   │  │  > get_average_temperature │
│  └──────────────────┘  │  Response: "The current    │
│                        │  temperature is 18°C"      │
│  ┌──────────────────┐  │                            │
│  │ Agent: [Agent1▼] │  │                            │
│  │ Location: [____] │  │                            │
│  │ [Set Location]   │  │                            │
│  └──────────────────┘  │                            │
│                        │                            │
│  Free Query            │  Registered Tools          │
│  ┌──────────────────┐  │  ┌────────────────────┐   │
│  │ Ask anything...  │  │  │ get_weather     [R] │   │
│  │ [Ask] [Intervene]│  │  │ change_weather  [W] │   │
│  └──────────────────┘  │  │ set_agent_loc   [W] │   │
│                        │  │ get_avg_temp    [R] │   │
│                        │  └────────────────────┘   │
├────────────────────────┴────────────────────────────┤
│  Tool Call Trace (expandable)                       │
│  ▶ change_weather("rainy", 18) → "Weather changed"  │
│  ▶ get_average_temperature() → "18°C"               │
└─────────────────────────────────────────────────────┘
```

### Components

| Component | Streamlit Widget | Description |
|-----------|-----------------|-------------|
| Environment State | `st.metric` + `st.json` | 실시간 상태 표시 |
| Manual Controls | `st.selectbox`, `st.number_input`, `st.button` | 직접 환경 조작 |
| Action Log | `st.container` with timestamped entries | 실행 이력 |
| Tool Registry | `st.expander` | 등록된 도구 목록 (R=readonly, W=write) |
| Free Query | `st.text_input` + 2 buttons (ask/intervene) | 자연어 질의 |
| Tool Trace | `st.expander` | 실제 tool call 상세 |

### Key Learning Point

이 예제의 핵심은 `@tool` 데코레이터가 어떻게 Python 메서드를 LLM callable function으로 변환하는지 보여주는 것. UI에서 Tool Registry와 Tool Call Trace를 통해 이 과정을 투명하게 노출.

## Dependencies

- `google-genai` (Gemini API)
- `streamlit`
- `agentsociety2_lite` (경량 코어: EnvBase, @tool, CodeGenRouter)

## Branch

`examples-basics` — 파일: `examples/basics/02_custom_env_module.py`
