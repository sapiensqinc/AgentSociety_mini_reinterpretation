# Architecture: agentsociety2_lite

## Overview

Python 3.14 호환을 위해 `agentsociety2`의 핵심 API 표면만 경량 재구현.
LLM 백엔드를 litellm에서 google-genai (Gemini)로 교체하여 보안 리스크 해소.

## Why Not agentsociety2 Directly?

| 문제 | 상세 |
|------|------|
| Python 호환성 | `mineru`, `faiss-cpu` 등이 Python <3.14만 지원 |
| 의존성 비대 | 45+ 패키지 (torch, ultralytics 등 ML 스택) |
| 보안 리스크 | litellm 공급망 공격 (2026.03) |
| 실제 사용률 | 예제가 사용하는 API는 전체의 10-15% |

## Core Architecture

```
agentsociety2_lite/
├── __init__.py              # Public API exports
│
├── agent/
│   ├── __init__.py
│   ├── base.py              # AgentBase: LLM 기반 에이전트 추상 클래스
│   │   - ask(question, readonly) → str
│   │   - set_router(router)
│   │   - _name, _id, _profile
│   └── person.py            # PersonAgent: 프로필 기반 기본 에이전트
│       - profile → system prompt 변환
│       - ask() 호출 시 프로필 컨텍스트 자동 주입
│
├── env/
│   ├── __init__.py
│   ├── env_base.py          # EnvBase: 환경 모듈 기반 클래스
│   │   - @tool 데코레이터
│   │   - get_tools() → List[ToolSchema]
│   │   - call_tool(name, args) → result
│   ├── router_base.py       # RouterBase: 라우터 추상 클래스
│   │   - route(question, tools, llm) → response
│   │   - register_module(env_module)
│   ├── router_codegen.py    # CodeGenRouter: Python 코드 생성→실행
│   │   - tool schema → code prompt
│   │   - 코드 실행 + 결과 반환
│   │   - faiss 제거 → dict 캐시 또는 캐시 없음
│   ├── router_react.py      # ReActRouter: Reason-Act-Observe 루프
│   │   - Think → tool call → Observe → 반복
│   │   - max_iterations 제한
│   └── router_plan.py       # PlanExecuteRouter: 계획-실행 분리
│       - Plan: 전체 계획 수립 (sub-tasks)
│       - Execute: 각 sub-task 순차 실행
│
├── contrib/
│   ├── __init__.py
│   ├── simple_social.py     # SimpleSocialSpace
│   │   - agent_id_name_pairs 관리
│   │   - get_all_agents() tool
│   ├── prisoners_dilemma.py # PrisonersDilemma
│   │   - 보수 매트릭스 설정
│   │   - get_payoff() tool
│   └── public_goods.py      # PublicGoodsGame
│       - endowment, contribution_factor
│       - contribute(), get_results() tools
│
├── society/
│   ├── __init__.py
│   └── society.py           # AgentSociety: 오케스트레이터
│       - init(): 에이전트←→라우터 연결
│       - ask(question) → str: 읽기 전용 질의
│       - intervene(action) → str: 환경 변경
│       - run(num_steps, tick): 자동 시뮬레이션
│       - close(): 정리
│
├── storage/
│   ├── __init__.py
│   └── replay_writer.py     # ReplayWriter: SQLite 기반 기록
│       - init(): DB 초기화
│       - write_interaction(agent_id, prompt, response)
│       - read_all() → List[Interaction]
│
└── llm/
    ├── __init__.py
    └── client.py            # LLM 클라이언트 (Gemini)
        - GeminiClient:
          - chat(messages, tools?) → response
          - function_calling 지원
          - .env에서 GEMINI_API_KEY 로드
        - 인터페이스:
          - complete(prompt, system?) → str
          - complete_with_tools(prompt, tools) → (text, tool_calls)
```

## @tool Decorator Design

```python
def tool(readonly: bool = True, kind: str = "action"):
    """Mark a method as an LLM-callable tool."""
    def decorator(func):
        func._is_tool = True
        func._readonly = readonly
        func._kind = kind
        return func
    return decorator
```

EnvBase가 `get_tools()`에서 `@tool` 표시된 메서드를 스캔하여 JSON schema 생성:
- 함수 이름 → tool name
- docstring → description
- type hints → parameter schema (via pydantic or inspect)
- readonly → ask()에서만 호출 가능, intervene() 필요 없음

## LLM Client: Gemini

```python
import google.genai as genai

class GeminiClient:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    async def complete(self, prompt: str, system: str = "") -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=system,
            ),
        )
        return response.text

    async def complete_with_tools(self, prompt, tools):
        # Gemini native function calling
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                tools=tools,  # Gemini tool format
            ),
        )
        return response
```

## .env Configuration

```env
# Gemini API (Required)
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash

# Optional: different model for different purposes
GEMINI_CODER_MODEL=gemini-2.0-flash
```

## Migration from Original Scripts

기존 스크립트의 import 경로만 변경:

```python
# Before (agentsociety2)
from agentsociety2 import PersonAgent
from agentsociety2.env import CodeGenRouter, EnvBase, tool
from agentsociety2.society import AgentSociety

# After (agentsociety2_lite)
from agentsociety2_lite import PersonAgent
from agentsociety2_lite.env import CodeGenRouter, EnvBase, tool
from agentsociety2_lite.society import AgentSociety
```

paper-* 브랜치의 커스텀 EnvBase 구현은 그대로 동작 (동일 인터페이스).

## Dependencies (Total: 9 packages)

```
google-genai>=1.0.0    # Gemini API (litellm 대체)
pydantic>=2.0          # 데이터 검증
json-repair>=0.30.0    # JSON 파싱 복구
python-dotenv>=1.0.0   # .env 로드
sqlalchemy>=2.0        # ReplayWriter DB (선택)
aiohttp>=3.9           # 비동기 HTTP (선택)
streamlit>=1.30        # UI
plotly>=5.0            # 차트
pyvis>=0.3             # 네트워크 시각화 (선택)
```

vs 원본 agentsociety2: 45+ packages, 500MB+ 설치 크기
