# AgentSociety Replica

AgentSociety 논문의 비교 분석 및 실행 가능한 예시 모음.


## Architecture

```
agentsociety2_lite/     ← 경량 코어 (Gemini 백엔드)
app/                    ← Streamlit 통합 UI
docs/                   ← 예제별 UI 디자인 + 시나리오
examples/               ← 실험 스크립트 (브랜치별)
```

## Branches

| Branch | Description | Examples |
|--------|-------------|----------|
| **main** | 코어 라이브러리 + UI + 문서 | - |
| **examples-basics** | 기본 예시 | hello agent, custom env, replay |
| **examples-advanced** | 고급 예시 | custom agent, multi router |
| **examples-games** | 게임이론 | prisoner's dilemma, public goods, reputation |
| **paper-polarization** | 논문 7.2 | 총기규제 의견 양극화 |
| **paper-inflammatory** | 논문 7.3 | 선동적 메시지 확산 |
| **paper-ubi** | 논문 7.4 | 보편적 기본소득(UBI) |
| **paper-hurricane** | 논문 7.5 | 허리케인 외부 충격 |

## Quick Start

```bash
# 1. Clone & setup
git clone https://github.com/sapiensqinc/AgentSociety_Replica.git
cd AgentSociety_Replica
python -m venv .venv
source .venv/Scripts/activate  # Windows
# source .venv/bin/activate    # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API key
cp .env.example .env
# Edit .env: GEMINI_API_KEY=your-key-here

# 4. Run Streamlit UI
streamlit run app/app.py
```

## Documentation

- [Architecture](docs/architecture.md) — 경량 코어 라이브러리 설계
- [Streamlit App](docs/streamlit_app.md) — UI 구조
- [Security Review](docs/security_review.md) — 의존성 보안 감사
- [Paper vs Code](PAPER_VS_CODE.md) — 논문-코드 비교 분석

### Example Designs (UI Mockups)

**Basics:**
- [01. Hello Agent](docs/examples-basics/01_hello_agent.md)
- [02. Custom Environment](docs/examples-basics/02_custom_env.md)
- [03. Replay System](docs/examples-basics/03_replay_system.md)

**Advanced:**
- [01. Custom Agent](docs/examples-advanced/01_custom_agent.md)
- [02. Multi-Router](docs/examples-advanced/02_multi_router.md)

**Games:**
- [01. Prisoner's Dilemma](docs/examples-games/01_prisoners_dilemma.md)
- [02. Public Goods](docs/examples-games/02_public_goods.md)
- [03. Reputation Game](docs/examples-games/03_reputation_game.md)

**Paper Experiments:**
- [Polarization (Sec 7.2)](docs/paper-experiments/polarization.md)
- [Inflammatory Messages (Sec 7.3)](docs/paper-experiments/inflammatory.md)
- [UBI Policy (Sec 7.4)](docs/paper-experiments/ubi.md)
- [Hurricane Impact (Sec 7.5)](docs/paper-experiments/hurricane.md)

## References

- **논문**: arXiv:2502.08691 (2025.02.12)
- **원본 코드**: [tsinghua-fib-lab/AgentSociety](https://github.com/tsinghua-fib-lab/AgentSociety)
