# Game Theory Examples

게임이론 시나리오를 AgentSociety2로 시뮬레이션하는 예시들입니다.

## 예시 목록

### 01. Prisoner's Dilemma (죄수의 딜레마)
클래식 게임이론: 두 에이전트가 협력/배신을 선택합니다.

```bash
python 01_prisoners_dilemma.py
```

**보수 행렬**: 둘 다 협력(1년) / 둘 다 배신(3년) / 한쪽만 배신(0년 vs 5년)

### 02. Public Goods Game (공공재 게임)
각 에이전트가 공공재에 기여할 금액을 결정합니다.

```bash
python 02_public_goods.py
```

**메커니즘**: 기여금 총합 x 1.5배 → 균등 분배. 무임승차 vs 협력 딜레마.

### 03. Reputation Game (평판 게임)
LLMDonorAgent를 사용한 평판 기반 협력 실험.

```bash
python 03_reputation_game.py
```

**참고**: mem0 메모리 시스템이 필요하며, API 키 설정이 필요합니다.
