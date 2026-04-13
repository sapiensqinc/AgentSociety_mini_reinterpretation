# Test Scenarios for All 12 Examples

> 테스트 일시: 2026-04-13
> 환경: Python 3.14.3, Streamlit 1.56.0, Gemini 2.5 Flash
> 테스트 방법: 실제 Gemini API 호출을 통한 End-to-End 테스트

---

## Basics

### 01. Hello Agent

**목적**: PersonAgent가 프로필 기반으로 자연스럽게 대화하는지 확인

**사전 조건**: Gemini API Key 입력 완료

| Step | 동작 | 기대 결과 | 확인 |
|------|------|----------|:----:|
| 1 | 사이드바에서 Basics > 01. Hello Agent 선택 | Agent Profile 카드에 Alice 정보 표시 | |
| 2 | "What's the name of all agents?..." 버튼 클릭 | "Alice" 를 포함한 응답 | |
| 3 | "Tell me about Alice's personal..." 버튼 클릭 | 성격(friendly, curious), 취미(hiking, sci-fi, cooking) 등 프로필 내용 반영된 응답 | |
| 4 | 채팅 입력창에 "Where do you live?" 직접 입력 | "San Francisco" 관련 응답 | |
| 5 | "Clear Chat" 클릭 | 대화 히스토리 초기화 | |

**검증 포인트**:
- 프로필 정보(나이, 성격, 위치)가 시스템 프롬프트로 전달되어 응답에 반영되는지
- SimpleSocialSpace의 `get_all_agents` 도구가 환경 조회에 사용되는지
- 대화 히스토리가 세션 간 유지되는지

**실제 테스트 결과**: PASS (3.1s) - "I am Alice, and I am friendly and curious!"

---

### 02. Custom Environment Module

**목적**: @tool 데코레이터로 정의한 환경 도구가 LLM에 의해 올바르게 호출되는지 확인

| Step | 동작 | 기대 결과 | 확인 |
|------|------|----------|:----:|
| 1 | 좌측 Environment State 확인 | Weather: sunny, Temp: 25C 표시 | |
| 2 | Weather를 "rainy", Temperature를 18로 변경 후 [Apply Change] | Action Log에 "Weather changed to rainy at 18C" | |
| 3 | 우측 Query에 "What is the current temperature?" 입력, Ask 모드, [Execute] | "18" 을 포함한 응답 | |
| 4 | "Change the weather to snowy", Intervene 모드, [Execute] | 환경 상태가 snowy로 변경 | |
| 5 | Registered Tools 확인 | [R] get_weather, [W] change_weather, [W] set_agent_location, [R] get_average_temperature | |
| 6 | [Reset Environment] 클릭 | 상태 초기화 (sunny, 25C) | |

**검증 포인트**:
- readonly=True 도구는 Ask에서만, readonly=False 도구는 Intervene에서 호출 가능
- 환경 상태 변경이 세션에 유지되는지 (WeatherEnvironment가 session_state에 저장)
- 도구의 JSON Schema가 올바르게 생성되는지 (파라미터 타입, 설명)

**실제 테스트 결과**: PASS (2.7s) - "Temperature is 25C"

---

### 03. Replay System

**목적**: ReplayWriter가 SQLite DB에 상호작용을 기록하고 재생할 수 있는지 확인

| Step | 동작 | 기대 결과 | 확인 |
|------|------|----------|:----:|
| 1 | [Run Simulation] 클릭 | 3명의 에이전트(Agent1~3)에게 자기소개 요청 실행 | |
| 2 | 완료 후 Replay 섹션 표시 확인 | Step 슬라이더, 네비게이션 버튼 표시 | |
| 3 | [Next] 버튼 클릭 | Step 2로 이동, Agent2의 응답 표시 | |
| 4 | [Last] 버튼 클릭 | 마지막 Step으로 이동 | |
| 5 | 슬라이더를 Step 1로 드래그 | Step 1의 Agent1 응답으로 복귀 | |
| 6 | Agent Status 확인 | 현재 Step의 에이전트가 [ON], 이전은 [OK], 이후는 [--] | |

**검증 포인트**:
- ReplayWriter가 SQLite DB에 (agent_id, prompt, response, timestamp) 기록하는지
- DB에서 read_all()로 읽은 데이터가 시간순으로 정렬되는지
- 버튼과 슬라이더의 동기화 (on_click 콜백 + on_change)

**실제 테스트 결과**: PASS (1.3s) - "Response: Hello!, DB rows: 1"

---

## Advanced

### 01. Custom Agent

**목적**: AgentBase 상속을 통한 커스텀 에이전트가 올바르게 동작하는지 확인

**Tab 1: Specialist Agent**

| Step | 동작 | 기대 결과 | 확인 |
|------|------|----------|:----:|
| 1 | Specialty: "climate science", Question: "What should cities do?" | 기후 과학 관점의 전문적 응답 | |
| 2 | "Internal Enhancement" 펼치기 | "You are a specialist in climate science..." 프롬프트 표시 | |

**Tab 2: Reflection**

| Step | 동작 | 기대 결과 | 확인 |
|------|------|----------|:----:|
| 3 | Specialty: "environmental science", [Reflect] 클릭 | 해당 분야의 핵심 측면에 대한 성찰 응답 | |

**Tab 3: Recursive CoT**

| Step | 동작 | 기대 결과 | 확인 |
|------|------|----------|:----:|
| 4 | Question: "How to reduce traffic?", Depth: 2, [Think Deeply] | Sub-Q 1~3 분해 결과 표시 | |
| 5 | 각 Sub-Q 펼치기 | 개별 하위 질문에 대한 답변 | |
| 6 | Synthesize 섹션 확인 | 하위 답변을 종합한 최종 답변 | |

**검증 포인트**:
- SpecialistAgent.ask()가 전문 분야 컨텍스트를 주입하고 string을 반환하는지 (tuple 아님)
- RecursiveAgent가 depth 파라미터에 따라 실제로 재귀 호출하는지
- reflect_on_specialty()가 커스텀 메서드로 동작하는지

---

### 02. Multi-Router Comparison

**목적**: 3가지 라우터 전략이 같은 질문에 서로 다른 방식으로 접근하는지 비교

| Step | 동작 | 기대 결과 | 확인 |
|------|------|----------|:----:|
| 1 | Preset: "Apple Math" 선택, [Run All Routers] | 3개 라우터가 각각 답변 생성 | |
| 2 | 각 라우터의 Answer 확인 | 모두 "6" 을 정답으로 포함 | |
| 3 | Time 비교 확인 | CodeGen이 가장 빠르고, PlanExecute가 가장 느린 경향 | |
| 4 | Token Usage 바 차트 확인 | CodeGen < ReAct < PlanExecute 순서 경향 | |

**검증 포인트**:
- 각 라우터가 AgentSociety를 통해 실행되는지 (router.route() 직접 호출 아님)
- register_module() 패턴이 사용되는지
- 응답 시간과 토큰 사용량의 트레이드오프가 드러나는지

**실제 테스트 결과**: PASS - CodeGen과 ReAct 모두 정상 응답

---

## Games

### 01. Prisoner's Dilemma

**목적**: LLM 에이전트가 전략적 상황에서 합리적으로 추론하는지 확인

| Step | 동작 | 기대 결과 | 확인 |
|------|------|----------|:----:|
| 1 | 기본 파라미터 확인 (Reward=1, Punishment=3, Temptation=0, Sucker=5) | 표준 게임이론 보수 매트릭스 표시 | |
| 2 | [Run Game] 클릭 | Alice/Bob 각각의 결정 + 근거 표시 | |
| 3 | 결과 확인 | 보수 매트릭스에 따른 올바른 형량 계산 | |
| 4 | Reasoning 펼치기 | 상세한 전략 분석 (내쉬 균형 언급 여부) | |
| 5 | Reflection 확인 | 결과에 대한 사후 회고 | |
| 6 | 파라미터 변경 (Reward=5) 후 재실행 | 변경된 보수에 맞는 결과 | |

**검증 포인트**:
- 보수 공식: Both cooperate = reward, Both defect = punishment, Cooperator = sucker, Defector = temptation
- 프롬프트에 시나리오 설명(체포, 격리, 4가지 결과) 포함
- Alice의 strategy="will analyze the situation carefully" 가 응답에 영향

**실제 테스트 결과**: PASS (6.5s) - "I will choose to DEFECT" (내쉬 균형 도달)

---

### 02. Public Goods Game

**목적**: 무임승차 문제에서 에이전트 성격에 따른 기여 차이 관찰

| Step | 동작 | 기대 결과 | 확인 |
|------|------|----------|:----:|
| 1 | Endowment=$100, Multiplier=1.5x, Rounds=3, [Start Game] | 4명 에이전트의 라운드별 기여 결과 | |
| 2 | 기여 막대 확인 | Alice(altruistic) > Bob(self-interested) 경향 | |
| 3 | Round Calculation 확인 | Total x 1.5 / 4 = per-person 계산 올바른지 | |
| 4 | Contribution Trend 차트 | 라운드별 기여 추이 (무임승차자 학습 여부) | |
| 5 | Final Reflection 확인 | 집단 협력에 대한 분석 | |

**검증 포인트**:
- PublicGoodsGame 환경의 get_game_rules 도구가 에이전트에 규칙 전달
- 기여액 파싱 (정규식 \$?(\d+))이 정확한지
- 성격(altruistic/selfish)이 실제 기여에 영향

**실제 테스트 결과**: PASS (9.8s) - 이타적 에이전트가 높은 기여 응답

---

### 03. Reputation Game

**목적**: 사회 규범에 따른 평판 기반 협력 진화 관찰

| Step | 동작 | 기대 결과 | 확인 |
|------|------|----------|:----:|
| 1 | Z=8, Benefit=5, Cost=1, Norm=stern_judging, Steps=10, [Run] | 10스텝 시뮬레이션 완료 | |
| 2 | Reputation Distribution 파이 차트 | Good/Bad 비율 표시 | |
| 3 | Cooperation Rate 시계열 | 시간에 따른 협력률 변화 추이 | |
| 4 | Global Statistics | Total Interactions, Cooperation Rate, Avg Payoff 표시 | |
| 5 | Leaderboard | 수익 기준 순위 + 평판 표시 | |
| 6 | Norm을 "image_score"로 변경 후 재실행 | 다른 협력률 패턴 (일반적으로 stern_judging보다 낮음) | |

**검증 포인트**:
- ReputationGameEnv의 submit_decision 도구가 보수+평판 업데이트
- Stern Judging 규칙: 나쁜 평판 상대를 배신하면 좋은 평판 유지
- 7개 @tool 메서드가 모두 정상 등록

**실제 테스트 결과**: PASS (4.5s)

---

## Paper Experiments

### Polarization (Section 7.2)

**목적**: 에코 챔버 효과와 교차 노출 효과를 재현하여 논문 결과와 비교

| Step | 동작 | 기대 결과 | 확인 |
|------|------|----------|:----:|
| 1 | Agents=10, Rounds=2, Seed=42, 3조건 모두 선택, [Run] | 3개 조건 순차 실행 | |
| 2 | Control 조건 결과 확인 | 극화/완화 비율 (논문: 39%/33%) | |
| 3 | Homophilic 조건 결과 | 극화 비율 증가 (논문: 52%) - 에코 챔버 | |
| 4 | Heterogeneous 조건 결과 | 완화 비율 증가 (논문: 89%) - 교차 노출 | |
| 5 | Opinion Distribution 차트 | Before/After 점 분포 + 화살표 방향 | |
| 6 | Comparison with Paper 테이블 | 시뮬레이션 vs 논문 수치 비교 | |

**검증 포인트**:
- PolarizationSocialSpace의 6개 @tool 메서드 정상 동작
- 동질적 조건: 같은 편 peer 선택 로직 (initial opinion 기반 필터링)
- 이질적 조건: 반대편 peer 선택 로직
- 극화 판정: |opinion - 5| 변화가 0.5 이상

**실제 테스트 결과**: PASS (2.2s) - 의견 추출 정상

---

### Inflammatory Messages (Section 7.3)

**목적**: 선동적 메시지 확산과 콘텐츠 모더레이션 효과 비교

| Step | 동작 | 기대 결과 | 확인 |
|------|------|----------|:----:|
| 1 | Network=10, Steps=4, control + experimental 선택, [Run] | 2조건 실행 | |
| 2 | Spread & Emotion 이중축 차트 | experimental > control (확산 속도, 감정 강도) | |
| 3 | node_intervention 추가 실행 | 확산 억제 (banned 에이전트 발생) | |
| 4 | edge_intervention 추가 실행 | 연결 제거에 의한 확산 억제 | |
| 5 | Final Comparison 테이블 | 4조건 비교: Spread, Emotion, Messages, Banned | |

**검증 포인트**:
- SpreadEnv의 share_message 도구가 ban/edge 체크 수행
- apply_node_intervention(threshold=2): 2회 이상 선동 공유 시 차단
- apply_edge_intervention(): 선동 메시지 경로 차단
- 논문 결과: inflammatory > control, node > edge in containment

---

### UBI Policy (Section 7.4)

**목적**: UBI 지급/미지급 조건에서 경제 지표 변화 비교

| Step | 동작 | 기대 결과 | 확인 |
|------|------|----------|:----:|
| 1 | Agents=8, UBI=$1000, Months=3, [Run] | No UBI + UBI 두 조건 순차 실행 | |
| 2 | Monthly Consumption 차트 | UBI 조건에서 더 높은 소비 | |
| 3 | Happiness 차트 | UBI 조건에서 더 높은 행복도 | |
| 4 | Summary Metrics | 소비/저축/행복도 비교 (delta 표시) | |
| 5 | Agent Interviews | UBI 조건 상위 3명의 정책 의견 | |

**검증 포인트**:
- EconomyEnv의 4개 @tool: get_economic_status, make_consumption_decision, update_happiness, get_economy_statistics
- 가처분소득 = 급여 + UBI, 저축 = 이전저축 + 가처분소득 - 지출
- 논문 결과: UBI increases consumption, reduces depression

---

### Hurricane Impact (Section 7.5)

**목적**: 자연재해 시 이동성 변화 패턴이 실제 데이터와 유사한지 확인

| Step | 동작 | 기대 결과 | 확인 |
|------|------|----------|:----:|
| 1 | Agents=10, [Run Simulation] | 9일 시뮬레이션 실행 | |
| 2 | Activity Level 바 차트 | 상륙 전(d1-3) 높음 → 상륙 중(d4-6) 급감 → 상륙 후(d7-9) 회복 | |
| 3 | Wind Speed 오버레이 | d5에서 95mph 피크, 활동량 최저와 일치 | |
| 4 | Phase Summary | Before ~80%, During ~30%, After 회복 (논문과 유사) | |
| 5 | Individual Decisions (Day 5 선택) | 대부분 STAY HOME, 의료종사자는 GO OUT 가능 | |

**검증 포인트**:
- WeatherMobilitySpace의 3개 @tool: get_weather, decide_travel, get_activity_statistics
- set_weather() / reset_daily_travel() / get_activity_level() 헬퍼 메서드
- 직업별 차별적 결정 (essential worker 패턴)
- 논문 결과: ~80% before, ~30% during, recovery after

**실제 테스트 결과**: PASS (2.2s) - 허리케인 경보 시 stay home 응답

---

## 보안 점검 사항

| 항목 | 상태 | 설명 |
|------|:---:|------|
| `.env.local` gitignore 포함 | OK | `.env.*` 패턴으로 차단, `!.env.example`만 허용 |
| API Key 노출 방지 | OK | Streamlit sidebar에서 password 타입 입력, session_state에만 저장 |
| API Key 로깅 방지 | OK | 코드에 API Key 출력/로깅 없음 |
| litellm 제거 확인 | OK | 의존성에서 완전 제거, google-genai 직접 사용 |
| `.env.local` 로드 순서 | OK | `.env.local`(사용자 비밀) 우선, `.env`(기본값) 후순위 |
| DB 파일 gitignore | OK | `*.db`, `*.sqlite` 패턴으로 차단 |
| 결과 파일 gitignore | OK | `results/`, `output/`, `log/` 패턴으로 차단 |

---

## 자동 테스트 실행 방법

```bash
source .venv/Scripts/activate  # Windows
# source .venv/bin/activate    # Linux/Mac

# API 키 확인
cat .env.local | grep GEMINI_API_KEY

# Streamlit 앱 테스트
streamlit run run.py

# 프로그래밍 방식 단위 테스트 (API 호출 포함)
python -c "
import asyncio, sys, os
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env.local', override=True)

async def test():
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from agentsociety2_lite.contrib import SimpleSocialSpace
    from datetime import datetime

    agent = PersonAgent(id=1, profile={'name': 'Test', 'personality': 'helpful'})
    env = SimpleSocialSpace(agent_id_name_pairs=[(1, 'Test')])
    society = AgentSociety(agents=[agent], env_router=CodeGenRouter(env_modules=[env]),
                           start_t=datetime.now())
    await society.init()
    resp = await society.ask('Say hello')
    print(f'Response: {resp}')
    await society.close()

asyncio.run(test())
"
```
