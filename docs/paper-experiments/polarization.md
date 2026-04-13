# Paper: Polarization Experiment (Section 7.2) - UI Design & Scenario

## Overview

논문의 총기규제 의견 양극화 실험 재현. 3가지 사회적 조건(통제/동질/이질)에서 에이전트 의견이 어떻게 변화하는지 관찰.

## Paper Reference

- **논문**: arXiv:2502.08691, Section 7.2
- **원래 실험 결과**:
  - Control: 39% polarized, 33% moderated
  - Homophilic (echo chamber): 52% polarized
  - Heterogeneous: 89% moderated, 11% adopted opposing views

## Scenario (시나리오)

### 에이전트 생성 (10명)
- 이름: Alex, Jordan, Taylor, Morgan, Casey, Riley, Quinn, Avery, Cameron, Dakota
- 성격: conservative / liberal / libertarian / moderate / progressive (랜덤)
- 초기 의견: 0-10 척도 (0=반대, 10=찬성), 양극단에 분포 (1-4 또는 6-9)

### 3가지 실험 조건

| 조건 | 대화 상대 | 기대 효과 |
|------|----------|----------|
| **Control** | 자연스러운 토론 | 기준선 |
| **Homophilic** | 같은 입장의 상대와 대화 | 에코 챔버 → 극화 |
| **Heterogeneous** | 반대 입장의 상대와 대화 | 의견 완화 |

### 실행 흐름 (조건당)
1. 10명 에이전트 + PolarizationSocialSpace 환경 생성
2. 2라운드 반복:
   - 각 에이전트에게 조건별 프롬프트로 대화 유도
   - 응답에서 숫자 추출 → 의견 업데이트
3. 초기 vs 최종 의견 비교 → 극화/완화/불변 분류
4. 3조건 결과를 논문 수치와 비교

### 극화/완화 판정 기준
- **Polarized**: 중심(5)으로부터의 거리가 0.5 이상 증가
- **Moderated**: 중심(5)으로부터의 거리가 0.5 이상 감소
- **Unchanged**: 그 외

## UI Design

```
┌─────────────────────────────────────────────────────────┐
│  Polarization Experiment (Paper Section 7.2)            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Condition: [Control] [Homophilic] [Heterogeneous]     │
│  Agents: [10]   Rounds: [2]   Seed: [42]              │
│  [Run All Conditions]  [Run Selected]                   │
│                                                         │
│  Opinion Distribution                                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  0   1   2   3   4   5   6   7   8   9   10    │   │
│  │  Oppose ←──────────────────────────→ Support    │   │
│  │                                                  │   │
│  │  Before: ●  ●  ●  ●           ●  ●  ●  ●  ●   │   │
│  │  After:  ●  ●              ●   ●  ●  ●  ●  ●●  │   │
│  │                                                  │   │
│  │  ● = one agent (jittered for overlap)           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Individual Opinion Shifts                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Alex      ■■■■■■■■▸■■■■■■■■■■   7.2 → 9.1  ↑P │   │
│  │ Jordan    ■■■▸■■                 3.0 → 2.0  ↑P │   │
│  │ Taylor    ■■■■■■▸■■■■■          6.5 → 5.2  ↓M │   │
│  │ Morgan    ■■■■▸■■■■              4.0 → 4.2  ── │   │
│  │ Casey     ■■■■■■■■▸■■■■■■■■■    8.0 → 8.5  ↑P │   │
│  │ Riley     ■■▸■■                  2.5 → 2.0  ↑P │   │
│  │ Quinn     ■■■■■■■▸■■■■■■        7.0 → 6.0  ↓M │   │
│  │ Avery     ■■■■■■■■■▸■■■■■■■■■   8.5 → 9.0  ↑P │   │
│  │ Cameron   ■■■■▸■■■■■            3.5 → 4.5  ↓M │   │
│  │ Dakota    ■■■■■■▸■■■■■■          6.0 → 6.2  ── │   │
│  │                                                  │   │
│  │ ↑P = Polarized   ↓M = Moderated   ── = Unchanged│   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Three-Condition Comparison                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Polarized    Moderated    Unchanged │   │
│  │  Control     ████ 40%    ███ 30%     ███ 30%   │   │
│  │  Homophilic  ██████ 50%  █ 10%       ████ 40%  │   │
│  │  Heterogen.  █ 10%       ████████ 80% █ 10%    │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  Paper Ref:                                      │   │
│  │  Control     39%          33%          28%       │   │
│  │  Homophilic  52%          —            —         │   │
│  │  Heterogen.  —            89%          11%       │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Agent Conversations (expandable per agent)             │
│  ▶ Alex (Round 1): "As someone who values..."          │
│  ▶ Alex (Round 2): "After discussing with..."          │
└─────────────────────────────────────────────────────────┘
```

### Components

| Component | Streamlit Widget | Description |
|-----------|-----------------|-------------|
| Condition Tabs | `st.tabs` or `st.radio` | 3조건 전환 |
| Dot Plot | Plotly scatter | 의견 분포 (before/after 오버레이) |
| Shift Arrows | Custom Plotly/HTML | 개인별 의견 이동 방향+크기 |
| Comparison Chart | `st.bar_chart` / Plotly grouped bar | 3조건 극화/완화 비율 |
| Paper Reference | `st.table` | 논문 수치 대조 |
| Conversations | `st.expander` per agent per round | 실제 LLM 대화 내용 |

## Dependencies

- `google-genai`, `streamlit`, `plotly`
- `agentsociety2_lite` (PersonAgent, EnvBase, @tool, AgentSociety)

## Branch

`paper-polarization` — 파일: `examples/paper_experiments/polarization/run_polarization.py`
