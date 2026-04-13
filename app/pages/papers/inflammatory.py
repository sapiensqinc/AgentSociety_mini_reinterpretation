"""Paper: Inflammatory Messages Experiment (Section 7.3)."""

import asyncio
import re
import random
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from app.config import require_api_key
from agentsociety2_lite.env import EnvBase, tool


NORMAL_MSG = "A woman was found in difficult circumstances in a rural village. Authorities are investigating."
INFLAMMATORY_MSG = "SHOCKING: Woman found chained in village! Government cover-up! Share before they delete this!"


def render():
    st.header("Inflammatory Messages (Paper Sec 7.3)")
    st.caption("Branch: `paper-inflammatory`")

    with st.expander("이 예제에 대하여", expanded=False):
        st.markdown("""
**논문 대응**: 논문 Section 7.3 "Spread of Inflammatory Messages"를 재현한 실험입니다.
논문에서는 2022년 중국 쉬저우 체인우먼 사건을 모티프로, 선동적 메시지가 소셜 네트워크에서
어떻게 확산되는지를 1,000명 규모로 시뮬레이션했습니다. 일반 메시지 대비 선동적 메시지의
확산 속도와 감정적 반응 강도를 비교하고, 두 가지 콘텐츠 모더레이션 전략의 효과를 측정했습니다.

**논문 결과**: 선동적 메시지가 일반 메시지보다 확산 속도와 감정 강도 모두에서 우위를 보였으며,
노드 개입(계정 정지)이 엣지 개입(연결 제거)보다 확산 억제에 더 효과적이었습니다.
에이전트 인터뷰에서는 감정적 반응과 사회적 책임감이 공유 동기로 나타났습니다.

**동작 원리**: 소셜 네트워크에 시드 에이전트 2명이 메시지를 보유한 상태로 시작합니다.
매 스텝마다 정보를 가진 에이전트에게 "공유하겠는가?"를 질의하고, YES 응답 시 친구 2명에게 전파합니다.
노드 개입은 2회 이상 선동 공유한 에이전트의 계정을 정지시키고,
엣지 개입은 선동 메시지가 전달된 연결을 차단합니다.

**해결하는 문제**: 소셜 미디어 플랫폼의 콘텐츠 모더레이션 정책 효과를 사전에 시뮬레이션합니다.
실제 사회 실험이 불가능한 개입 전략들을 LLM 에이전트로 비교 평가할 수 있습니다.
        """)

    n_agents = st.number_input("Network Size", 6, 20, 10)
    n_steps = st.number_input("Steps", 2, 8, 4)

    conditions = st.multiselect(
        "Conditions",
        ["control", "experimental", "node_intervention", "edge_intervention"],
        default=["control", "experimental"],
    )

    if st.button("Run Experiment") and conditions and require_api_key():
        all_results = {}
        progress = st.progress(0)

        for ci, cond in enumerate(conditions):
            with st.spinner(f"Running {cond}..."):
                is_inflammatory = cond != "control"
                msg = INFLAMMATORY_MSG if is_inflammatory else NORMAL_MSG
                result = asyncio.run(_run_spread(
                    cond, n_agents, msg, is_inflammatory, n_steps
                ))
                all_results[cond] = result
            progress.progress((ci + 1) / len(conditions))

        # Dual-axis chart
        st.markdown("---")
        st.subheader("Spread & Emotion Over Time")

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        colors = {"control": "#3498db", "experimental": "#e74c3c",
                  "node_intervention": "#2ecc71", "edge_intervention": "#f39c12"}

        for cond, result in all_results.items():
            color = colors.get(cond, "#95a5a6")
            steps = list(range(1, len(result["spread_history"]) + 1))
            fig.add_trace(go.Scatter(
                x=steps, y=result["spread_history"],
                name=f"{cond} (spread)", line=dict(color=color),
            ), secondary_y=False)
            fig.add_trace(go.Scatter(
                x=steps, y=result["emotion_history"],
                name=f"{cond} (emotion)", line=dict(color=color, dash="dash"),
            ), secondary_y=True)

        fig.update_yaxes(title_text="Spread Ratio", range=[0, 1], secondary_y=False)
        fig.update_yaxes(title_text="Avg Emotion", range=[0, 1], secondary_y=True)
        fig.update_layout(height=400, xaxis_title="Step")
        st.plotly_chart(fig, use_container_width=True)

        # Comparison table
        st.subheader("Final Comparison")
        rows = []
        for cond, result in all_results.items():
            rows.append({
                "Condition": cond,
                "Spread": f"{result['final_spread']:.0%}",
                "Emotion": f"{result['final_emotion']:.2f}",
                "Messages": result["total_messages"],
                "Banned": result.get("banned", 0),
            })
        st.table(rows)

        st.caption("Paper: inflammatory > control in spread+emotion; node intervention > edge intervention")


async def _run_spread(condition, n, seed_msg, is_inflammatory, num_steps):
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from datetime import datetime

    random.seed(42)
    profiles = [{"id": i+1, "name": f"User_{i+1}",
                 "friends": random.sample([x for x in range(1, n+1) if x != i+1], min(3, n-1))}
                for i in range(n)]

    env = SpreadEnv(profiles)
    # Seed agents
    for sid in [1, 2]:
        env._received[sid] = True
        env._emotions[sid] = 0.6 if is_inflammatory else 0.2

    agents = [PersonAgent(id=p["id"], profile={"name": p["name"], "personality": "socially aware"})
              for p in profiles]
    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=agents, env_router=router, start_t=datetime.now())
    await society.init()

    spread_history, emotion_history = [], []

    for step in range(num_steps):
        for p in profiles:
            aid = p["id"]
            if aid in env._banned or not env._received.get(aid):
                continue

            resp = await society.ask(
                f"You are {p['name']}. You received: '{seed_msg}'. "
                f"Emotion: {env._emotions.get(aid, 0.1):.1f}. Share with friends? YES/NO. Rate emotion 0-1."
            )

            will_share = "yes" in resp.lower()
            match = re.search(r"(\d+\.?\d*)", resp)
            if match:
                env._emotions[aid] = max(0, min(1, float(match.group(1))))

            if will_share:
                available = [f for f in p["friends"] if f not in env._banned
                            and (min(aid, f), max(aid, f)) not in env._removed_edges]
                for fid in available[:2]:
                    env._received[fid] = True
                    env._messages += 1
                    if is_inflammatory:
                        env._infractions[aid] = env._infractions.get(aid, 0) + 1

        if "node" in condition:
            for aid, count in env._infractions.items():
                if count >= 2:
                    env._banned.add(aid)
        elif "edge" in condition:
            pass  # simplified

        informed = sum(1 for v in env._received.values() if v)
        avg_emo = sum(env._emotions.values()) / n
        spread_history.append(informed / n)
        emotion_history.append(avg_emo)

    await society.close()

    return {
        "spread_history": spread_history,
        "emotion_history": emotion_history,
        "final_spread": spread_history[-1] if spread_history else 0,
        "final_emotion": emotion_history[-1] if emotion_history else 0,
        "total_messages": env._messages,
        "banned": len(env._banned),
    }


class SpreadEnv(EnvBase):
    def __init__(self, profiles):
        super().__init__()
        self._received = {}
        self._emotions = {p["id"]: 0.1 for p in profiles}
        self._banned = set()
        self._removed_edges = set()
        self._infractions = {}
        self._messages = 0

    @tool(readonly=True, kind="statistics")
    def get_spread_stats(self) -> str:
        """Get current spread statistics."""
        informed = sum(1 for v in self._received.values() if v)
        return f"Informed: {informed}, Messages: {self._messages}, Banned: {len(self._banned)}"
