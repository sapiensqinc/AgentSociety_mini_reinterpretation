# Paper: Hurricane External Shock Experiment (Section 7.5) - UI Design & Scenario

## Overview

허리케인 도리안이 사우스캐롤라이나 콜럼비아 시의 이동성에 미치는 영향을 시뮬레이션. 9일간의 날씨 변화에 따른 에이전트 활동량 변화를 관찰.

## Paper Reference

- **논문**: arXiv:2502.08691, Section 7.5
- **실제 데이터**: SafeGraph 모빌리티 데이터 기반
- **원래 실험 결과**:
  - 상륙 전: 활동량 70-90%
  - 상륙 중: 활동량 ~30%로 급감
  - 상륙 후: 정상 수준으로 회복

## Scenario (시나리오)

### 에이전트 생성 (12명, 콜럼비아 SC 주민)
- 직업: office worker, teacher, retail worker, healthcare worker, student, retiree
- 나이: 22-70세 (랜덤)

### 9일 날씨 스케줄 (허리케인 도리안)

| Day | Date | Phase | Weather | Temp(°F) | Wind(mph) | Hurricane |
|-----|------|-------|---------|----------|-----------|:---------:|
| 1 | Aug 28 | Before | partly cloudy | 88 | 12 | |
| 2 | Aug 29 | Before | cloudy | 84 | 18 | |
| 3 | Aug 30 | Before | overcast with rain | 78 | 30 | |
| 4 | Aug 31 | **Landfall** | severe storm | 72 | 75 | **Yes** |
| 5 | Sep 1 | **Landfall** | hurricane conditions | 70 | 95 | **Yes** |
| 6 | Sep 2 | **Landfall** | tropical storm | 74 | 55 | **Yes** |
| 7 | Sep 3 | After | rain clearing | 80 | 25 | |
| 8 | Sep 4 | After | partly cloudy | 84 | 15 | |
| 9 | Sep 5 | After | clear skies | 87 | 10 | |

### 실행 흐름
1. 매일 날씨 설정 (WeatherMobilitySpace)
2. 각 에이전트에게 외출 결정 질의:
   - "Today is [date]. [weather]. Will you go out or stay home? YES/NO"
3. 활동량 집계 (외출 비율)
4. 9일 완료 후 Before/During/After 위상별 평균 비교

## UI Design

```
┌─────────────────────────────────────────────────────────┐
│  Hurricane Dorian Mobility Impact (Paper Section 7.5)   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Settings                                               │
│  Agents: [12]   [Run Simulation]                       │
│                                                         │
│  Weather Timeline                                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Day   Date     Weather          Wind   Phase    │   │
│  │  1    Aug 28   partly cloudy    12mph  Before   │   │
│  │  2    Aug 29   cloudy           18mph  Before   │   │
│  │  3    Aug 30   overcast+rain    30mph  Before   │   │
│  │  4    Aug 31   severe storm     75mph  LANDFALL │ ← │
│  │  5    Sep 1    HURRICANE        95mph  LANDFALL │ ← │
│  │  6    Sep 2    tropical storm   55mph  LANDFALL │ ← │
│  │  7    Sep 3    rain clearing    25mph  After    │   │
│  │  8    Sep 4    partly cloudy    15mph  After    │   │
│  │  9    Sep 5    clear skies      10mph  After    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Activity Level Chart                                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 100%┤ ██ ██                          ██ ██     │   │
│  │     │ ██ ██ ██                    ██ ██ ██     │   │
│  │  75%┤ ██ ██ ██                 ██ ██ ██ ██     │   │
│  │     │ ██ ██ ██              ██ ██ ██ ██ ██     │   │
│  │  50%┤ ██ ██ ██           ██ ██ ██ ██ ██ ██     │   │
│  │     │ ██ ██ ██        ██ ██ ██ ██ ██ ██ ██     │   │
│  │  25%┤ ██ ██ ██ ██  ██ ██ ██ ██ ██ ██ ██ ██     │   │
│  │     │ ██ ██ ██ ██  ██ ██ ██ ██ ██ ██ ██ ██     │   │
│  │   0%└─d1─d2─d3─d4──d5─d6─d7─d8─d9─────────    │   │
│  │                                                  │   │
│  │   ░ Before   ▓ Landfall (hurricane)   ░ After   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Wind Speed Overlay                                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 100┤              ●                              │   │
│  │  80┤           ●     ●                           │   │
│  │  60┤                                             │   │
│  │  40┤        ●           ●                        │   │
│  │  20┤  ●  ●                  ●  ●  ●              │   │
│  │   0└──d1─d2─d3─d4─d5─d6─d7─d8─d9──              │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Phase Summary                                          │
│  ┌──────────────┬───────────────┬───────────────┐      │
│  │ Before (d1-3)│ During (d4-6) │ After (d7-9)  │      │
│  │              │               │               │      │
│  │ Avg: 83%     │ Avg: 25%      │ Avg: 75%      │      │
│  │ Paper: ~80%  │ Paper: ~30%   │ Paper: recovery│     │
│  │              │               │               │      │
│  │   Match: ✅   │   Match: ✅    │   Match: ✅    │      │
│  └──────────────┴───────────────┴───────────────┘      │
│                                                         │
│  Individual Decisions (Day [5▼])                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Resident_1 (teacher, 35):     STAY HOME         │   │
│  │   "Hurricane conditions with 95mph winds —      │   │
│  │    it would be dangerous to go outside."         │   │
│  │                                                  │   │
│  │ Resident_2 (healthcare, 42):  GO OUT             │   │
│  │   "As a healthcare worker, I need to report     │   │
│  │    to duty even in these conditions."            │   │
│  │                                                  │   │
│  │ Resident_3 (student, 23):     STAY HOME         │   │
│  │   "No way I'm going out in a hurricane!"        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Components

| Component | Streamlit Widget | Description |
|-----------|-----------------|-------------|
| Weather Table | `st.dataframe` + row highlighting | 9일 날씨 스케줄 (허리케인=빨강) |
| Activity Bar Chart | Plotly bar + phase colors | 날짜별 활동량 (3색 구분) |
| Wind Speed Line | Plotly line (overlay) | 풍속 오버레이 |
| Phase Summary | `st.columns(3)` + `st.metric` | Before/During/After 평균 + 논문 대비 |
| Day Selector | `st.selectbox` | 특정 날짜의 개별 결정 보기 |
| Individual Log | `st.expander` per agent | 에이전트별 결정 + 이유 |

### Key Insight

에이전트의 직업/나이에 따라 같은 허리케인 상황에서도 다른 결정을 내림. 특히 의료종사자는 악천후에도 출근하는 경향 → 실제 SafeGraph 데이터의 essential worker 패턴과 유사.

## Dependencies

- `google-genai`, `streamlit`, `plotly`
- `agentsociety2_lite` (PersonAgent, EnvBase, @tool, AgentSociety)

## Branch

`paper-hurricane` — 파일: `examples/paper_experiments/hurricane/run_hurricane.py`
