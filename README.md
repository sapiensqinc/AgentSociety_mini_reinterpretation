# AgentSociety Replica

AgentSociety 논문과 코드베이스의 비교 분석 및 실행 가능한 예시 모음입니다.

## 구조

- **main**: 논문 vs 코드 비교 분석 (`PAPER_VS_CODE.md`) + 공통 설정
- **examples-basics**: 기본 예시 (hello agent, custom env module, replay system)
- **examples-advanced**: 고급 예시 (custom agent, multi router)
- **examples-games**: 게임이론 예시 (prisoner's dilemma, public goods, reputation game)
- **paper-polarization**: 논문 재현 — 양극화 실험 (총기규제 의견 변화)
- **paper-inflammatory**: 논문 재현 — 선동적 메시지 확산 실험
- **paper-ubi**: 논문 재현 — 보편적 기본소득(UBI) 정책 실험
- **paper-hurricane**: 논문 재현 — 허리케인 외부 충격 실험

## 사전 요구사항

```bash
# Python 3.11+
pip install agentsociety2

# 또는 원본 프로젝트에서 (uv workspace)
cd <AgentSociety_root>
uv sync
```

## 환경 변수 설정

`.env.example`을 `.env`로 복사하고 API 키를 입력하세요:

```bash
cp .env.example .env
# AGENTSOCIETY_LLM_API_KEY, AGENTSOCIETY_LLM_API_BASE 등 설정
```

## 실행 방법

각 브랜치를 체크아웃한 뒤, 해당 디렉토리의 Python 스크립트를 실행합니다:

```bash
# 예: 기본 예시
git checkout examples-basics
python examples/basics/01_hello_agent.py

# 예: 논문 재현 - 양극화 실험
git checkout paper-polarization
python examples/paper_experiments/polarization/run_polarization.py
```

## 참고

- **논문**: arXiv:2502.08691 (2025.02.12)
- **원본 코드**: [tsinghua-fib-lab/AgentSociety](https://github.com/tsinghua-fib-lab/AgentSociety)
- 논문 실험(v1)은 agentsociety2(v2) API로 재구현되었습니다
