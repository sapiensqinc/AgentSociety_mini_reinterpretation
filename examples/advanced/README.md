# Advanced Examples

AgentSociety2의 고급 패턴을 보여주는 예시들입니다.

## 예시 목록

### 01. Custom Agent
AgentBase를 상속하여 전문화된 에이전트 생성.

```bash
python 01_custom_agent.py
```

**학습 포인트**: AgentBase 상속, ask() 오버라이드, SpecialistAgent (도메인 전문가), RecursiveAgent (Chain-of-Thought)

### 02. Multi Router
서로 다른 라우터 전략 비교 (ReAct vs PlanExecute vs CodeGen).

```bash
python 02_multi_router.py
```

**학습 포인트**: ReActRouter (추론+행동 반복), PlanExecuteRouter (계획 후 실행), CodeGenRouter (코드 생성)
