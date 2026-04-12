# AgentSociety: 논문 vs 코드 비교 분석

> **논문**: "AgentSociety: Large-Scale Simulation of LLM-Driven Generative Agents Advances Understanding of Human Behaviors and Society"
> (arXiv:2502.08691, 2025.02.12, 칭화대학교)
>
> **코드**: [AgentSociety GitHub Repository](https://github.com/tsinghua-fib-lab/AgentSociety) — `agentsociety` (v1, 레거시) / `agentsociety2` (v2.x, 현재 주력)

---

## 인프라 & 시스템 아키텍처

| 항목 | 논문 (v1) | 코드 (v2) |
|------|----------|----------|
| **분산 컴퓨팅** | Ray 프레임워크 기반, 다중 머신/프로세스 병렬 실행 | Ray 의존성 완전 제거, 단일 프로세스 asyncio 기반 |
| **에이전트 그룹핑** | Agent Group 단위로 Ray Actor에 배정, TCP 포트 고갈 방지 설계 | 그룹 개념 없음, 에이전트를 직접 오케스트레이터가 관리 |
| **메시징 시스템** | MQTT (emqx) — publish/subscribe, 10만 에이전트 동시 연결 | MQTT 미사용, 내부 함수 호출 기반 통신 |
| **데이터 저장** | PostgreSQL (COPY FROM 고성능 배치 쓰기) + AVRO 로컬 파일 | SQLite (ReplayWriter, aiosqlite 비동기) |
| **메트릭 기록** | MLflow 서버 (중앙집중형 협업용) | 자체 로거 (ColoredFormatter + 파일 핸들러) |
| **환경 시뮬레이터** | 별도 서브프로세스로 실행, gRPC 기반 클라이언트-서버 통신 | Python 모듈로 내장, 동일 프로세스 내 직접 호출 |
| **목표 규모** | 10,000+ 에이전트 (분산 환경에서 수평 확장) | 소~중규모 중심, 유연성/확장성에 초점 |

## 에이전트 설계

| 항목 | 논문 (v1) | 코드 (v2) |
|------|----------|----------|
| **에이전트 아키텍처** | 고정 파이프라인: 감정→욕구→인지→행동 | 스킬 기반 플러그인: LLM이 메타데이터 보고 스킬 선택 후 실행 |
| **정신 프로세스** | 감정/욕구/인지가 코드에 하드코딩된 순차 모듈 | observation, memory, needs, cognition, plan, thought 등 독립 스킬 디렉토리 |
| **스킬 로딩** | 모든 모듈 항상 로드 | Lazy Loading — 선택된 스킬만 SKILL.md 로드 후 실행 |
| **커스텀 확장** | 논문에 언급 없음 | workspace/custom/skills/에 스킬 배치 시 런타임 핫로딩 |
| **메모리 시스템** | Event Flow + Perception Flow (스트림 메모리) | 3계층: 단기(최근 N개) + 장기(mem0/ChromaDB) + 인지 메모리(버퍼) |
| **메모리 백엔드** | PostgreSQL에 직접 저장 | mem0 + ChromaDB (텔레메트리 강제 비활성화) |
| **LLM 연동** | OpenAI Python 라이브러리 직접 호출 + 자체 어댑터 | litellm Router — 역할별 모델 분리 (default/coder/nano/embedding) |

## 환경 모듈

| 항목 | 논문 (v1) | 코드 (v2) |
|------|----------|----------|
| **환경 정의** | 도시/사회/경제 공간을 외부 시뮬레이터로 구현 | EnvBase 상속 + @tool 데코레이터로 Python 클래스 정의 |
| **도시 공간** | OpenStreetMap + SafeGraph 기반, IDM/MOBIL 교통 모델, 4가지 교통수단 | mobility_space/ 모듈 (간소화된 이동성 시뮬레이션) |
| **사회 공간** | 소셜 네트워크 + 온/오프라인 상호작용 + 감독자(콘텐츠 모더레이션) | simple_social_space.py, social_media/ (추천 알고리즘 추가) |
| **경제 공간** | DSGE 기반 거시경제 (기업/정부/은행/통계청), Taylor Rule | economy_space.py (기본 경제 모듈) |
| **라우터 패턴** | 없음 (직접 API 호출) | 5가지: ReAct / PlanExecute / CodeGen / TwoTierReAct / TwoTierPlanExecute |
| **게임이론 모듈** | 논문에 없음 | 죄수의 딜레마, 공공재 게임, 공유지의 비극, 신뢰게임, 자원봉사 딜레마, 평판 게임 |
| **심리학 실험 모듈** | 논문에 없음 | 부존효과, 자기고양, 자기참조 효과, IAT |

## 사회 실험 & 연구 도구

| 항목 | 논문 (v1) | 코드 (v2) |
|------|----------|----------|
| **실험 사례** | 양극화, 선동적 메시지 확산, UBI, 허리케인 (4가지 대규모 실험) | 게임이론 + 심리학 실험 위주 (예제 코드 제공) |
| **개입 도구** | 사전 설정/상태 조작/메시지 알림 3가지 | AgentSocietyHelper — Plan-and-Execute 워크플로우로 질의/개입 |
| **설문/인터뷰** | MQTT를 통한 실시간 전달, GUI에서 직접 대화 | CLI --steps YAML에서 ask/intervene/step 명령으로 처리 |
| **연구 스킬** | 논문에 없음 | literature→hypothesis→experiment→analysis→paper 워크플로우 |

## UI & 인터페이스

| 항목 | 논문 (v1) | 코드 (v2) |
|------|----------|----------|
| **GUI** | 자체 개발 (PostgreSQL + MQTT 연동) | React 18 + Ant Design + Mapbox GL/Deck.gl + Plotly.js |
| **API** | 논문에 명시 없음 | FastAPI REST API |
| **IDE 통합** | 없음 | VSCode Extension — MCP 기반 10개+ 스킬 |
| **CLI** | 없음 | python -m agentsociety2.society.cli |

## 핵심 패러다임 전환 요약

| 관점 | 논문 (v1) | 코드 (v2) |
|------|----------|----------|
| **설계 철학** | 대규모 분산 시뮬레이션 — 성능/규모 최우선 | 모듈화/유연성 — 연구자가 쉽게 확장 가능 |
| **에이전트 모델** | 이론 기반 고정 파이프라인 (심리학/경제학/행동과학 통합) | LLM-네이티브 스킬 선택 (에이전트가 스스로 필요한 능력 선택) |
| **환경 모델** | 고충실도 외부 시뮬레이터 (교통 시뮬레이션, 거시경제 엔진) | 경량 내장 모듈 + 풍부한 contrib 라이브러리 |
| **주 사용 시나리오** | 10K 에이전트 대규모 사회 실험 재현 | 연구자/개발자의 다양한 실험 설계 및 빠른 프로토타이핑 |
