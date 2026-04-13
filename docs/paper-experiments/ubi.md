# Paper: UBI Experiment (Section 7.4) - UI Design & Scenario

## Overview

보편적 기본소득(UBI) 정책의 경제적/심리적 영향을 시뮬레이션. 텍사스 주민 프로필 기반으로 UBI 유/무 조건을 비교.

## Paper Reference

- **논문**: arXiv:2502.08691, Section 7.4
- **원래 실험 결과**:
  - UBI가 소비 수준 증가
  - UBI가 우울증 수준 감소
  - 에이전트 인터뷰: 금리, 장기 혜택, 저축에 대한 우려

## Scenario (시나리오)

### 에이전트 생성 (8명, 텍사스 주민)
| Agent | Occupation | Income | Savings | Happiness |
|-------|-----------|--------|---------|-----------|
| Resident_1 | retail worker | ~$2,500 | ~$5,000 | 3-7 |
| Resident_2 | teacher | ~$3,500 | ~$8,000 | 3-7 |
| ... | (varied) | $1,200-$8,000 | $1,000-$15,000 | 3.0-7.0 |

직업: retail worker, teacher, nurse, truck driver, software engineer, construction worker, cashier, waiter, office clerk, mechanic

### 2가지 실험 조건
| 조건 | UBI | 가처분소득 |
|------|-----|----------|
| **No UBI** | $0/month | 급여만 |
| **With UBI** | $1,000/month | 급여 + $1,000 |

### 실행 흐름 (조건당 3개월)
1. 매월 각 에이전트에게 지출 결정 요청:
   - "Your monthly disposable income is $X. How much will you spend? Rate happiness 0-10."
2. 응답에서 지출액과 행복도 파싱
3. 저축 = 이전 저축 + 가처분소득 - 지출
4. UBI 조건에서는 추가로 인터뷰 (상위 3명):
   - "What is your opinion on UBI? How has it affected your life?"

## UI Design

```
┌─────────────────────────────────────────────────────────┐
│  UBI Experiment (Paper Section 7.4)                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Settings                                               │
│  Agents: [8]  UBI Amount: [$1000]  Months: [3]         │
│  [Run Experiment]                                       │
│                                                         │
│  Agent Profiles                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Name        Occupation    Income   Savings  😊  │   │
│  │ Resident_1  retail worker $2,500   $5,000   4.2 │   │
│  │ Resident_2  teacher       $3,500   $8,000   5.8 │   │
│  │ Resident_3  nurse         $4,200   $12,000  6.1 │   │
│  │ ...                                              │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─ Monthly Consumption ────┬─ Happiness ─────────────┐│
│  │                          │                          ││
│  │  $5k┤        _-- UBI    │  8┤          _-- UBI     ││
│  │     │      /             │   │        /             ││
│  │  $4k┤    /               │  7┤      /               ││
│  │     │  /                 │   │    /                 ││
│  │  $3k┤/   --- No UBI     │  6┤──/   --- No UBI     ││
│  │     │   /                │   │   /                  ││
│  │  $2k┤__/                 │  5┤__/                   ││
│  │     └────────────        │   └────────────          ││
│  │      M1   M2   M3       │    M1   M2   M3          ││
│  └──────────────────────────┴──────────────────────────┘│
│                                                         │
│  Savings Comparison (final month)                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │         No UBI          With UBI                 │   │
│  │ Res_1   $3,200  ████    $5,800  ████████        │   │
│  │ Res_2   $6,500  ██████  $9,200  █████████       │   │
│  │ Res_3   $10,800 ████████ $13,500 ███████████    │   │
│  │ ...                                              │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Summary                                                │
│  ┌───────────────────────────────────────┐             │
│  │ Metric          No UBI    With UBI    │             │
│  │ Avg Consumption  $2,800    $3,600     │             │
│  │ Avg Savings      $5,200    $7,800     │             │
│  │ Avg Happiness    5.2       7.1        │             │
│  │ GDP (total)      $22,400   $28,800    │             │
│  └───────────────────────────────────────┘             │
│                                                         │
│  Agent Interviews (UBI condition only)                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 💬 Resident_1 (retail worker):                   │   │
│  │ "The extra $1000 has allowed me to finally      │   │
│  │  build an emergency fund. I worry less about    │   │
│  │  unexpected expenses now..."                    │   │
│  │                                                  │   │
│  │ 💬 Resident_2 (teacher):                         │   │
│  │ "I appreciate the support, but I'm concerned    │   │
│  │  about inflation eating away at the benefit..." │   │
│  │                                                  │   │
│  │ 💬 Resident_3 (nurse):                           │   │
│  │ "I've been able to pay off some debts and       │   │
│  │  invest in my professional development..."      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Paper Comparison                                       │
│  Paper: UBI increases consumption, reduces depression  │
└─────────────────────────────────────────────────────────┘
```

### Components

| Component | Streamlit Widget | Description |
|-----------|-----------------|-------------|
| Agent Table | `st.dataframe` | 에이전트 프로필 목록 |
| Dual Line Charts | Plotly (2 subplots) | 소비/행복도 시계열 (UBI vs No UBI) |
| Savings Bars | Plotly grouped bar | 최종 저축 비교 |
| Summary Table | `st.metric` x4 | 핵심 지표 요약 |
| Interviews | `st.chat_message` | 에이전트 인터뷰 (UBI 조건만) |
| Paper Note | `st.caption` | 논문 결과 대조 |

## Dependencies

- `google-genai`, `streamlit`, `plotly`
- `agentsociety2_lite` (PersonAgent, EnvBase, @tool, AgentSociety)

## Branch

`paper-ubi` — 파일: `examples/paper_experiments/ubi/run_ubi.py`
