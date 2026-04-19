# Basic Examples

AgentSociety2의 기본 사용법을 보여주는 예시들입니다.

## 실행 전 준비

```bash
pip install agentsociety2 python-dotenv
cp ../../.env.example ../../.env
# .env 파일에 API 키 설정
```

## 예시 목록

### 01. Hello Agent
가장 기본적인 에이전트 생성과 질의응답.

```bash
python 01_hello_agent.py
```

**학습 포인트**: PersonAgent 생성, SimpleSocialSpace, CodeGenRouter, AgentSociety 초기화

### 02. Custom Environment Module
커스텀 환경 모듈 생성 (`@tool` 데코레이터 활용).

```bash
python 02_custom_env_module.py
```

**학습 포인트**: EnvBase 상속, @tool(readonly, kind) 데코레이터, society.ask() vs society.intervene()

### 03. Replay System
ReplayWriter를 사용한 시뮬레이션 기록/재생.

```bash
python 03_replay_system.py
```

**학습 포인트**: ReplayWriter, SQLite 기반 재생 데이터 저장, env_router.set_replay_writer()
