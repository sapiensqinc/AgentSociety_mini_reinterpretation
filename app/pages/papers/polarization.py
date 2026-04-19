"""Paper: Polarization Experiment (Section 7.2).

Two execution modes:
  1. peer-to-peer (default)   — direct 1-hop dialogue pairs, fast
  2. broadcast + propagation  — persuader agents (Agree/Disagree) push
     messages into citizen inboxes with a propagation_count; citizens LLM-
     decide whether to forward; messages with count > 5 are dropped. This
     mirrors the original `message_agent.py` mechanism in the paper's code.

Paper §7.2:
- 3 conditions: control / homophilic / heterogeneous
- Result: control (39%/33%), homophilic (52% polarized), heterogeneous (89%/11%)
"""

import asyncio
import re
import random
from dataclasses import dataclass, field
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from app.config import require_api_key
from app.security import ready_to_run, cap, show_safe_error
from agentsociety2_lite.env import EnvBase, tool


# Paper mechanism: broadcast messages carry a hop counter; drop after 5 hops.
# See original examples/polarization/message_agent.py.
MAX_PROPAGATION_COUNT = 5


@dataclass
class Message:
    """A persuasion message travelling the social graph."""
    content: str
    side: str                         # "pro" or "con" (supports or opposes gun control)
    propagation_count: int = 1
    origin_persuader: str = ""        # "Agree" or "Disagree"


NAMES = ["Alex", "Jordan", "Taylor", "Morgan", "Casey",
         "Riley", "Quinn", "Avery", "Cameron", "Dakota"]

DESCRIPTION = """
**논문 대응**: 논문 Section 7.2 "Polarization"을 직접 재현한 실험입니다.
논문에서는 1,000명의 에이전트로 미국 총기규제에 대한 의견 양극화를 시뮬레이션했습니다.
3가지 사회적 조건(통제/동질적 상호작용/이질적 상호작용)에서 의견이 어떻게 변화하는지 관찰하여,
에코 챔버 효과(동질적 집단에서 극화 심화)와 교차 노출 효과(이질적 집단에서 의견 완화)를 검증했습니다.

**논문 결과**: 통제 조건에서 39% 극화/33% 완화, 동질적 조건에서 52% 극화(에코 챔버),
이질적 조건에서 89% 완화/11% 반대 의견 수용이라는 결과를 보고했습니다.

**동작 원리**: 에이전트들에게 0-10 척도의 초기 의견을 부여합니다(0=반대, 10=찬성).
통제 조건에서는 자연스러운 토론을, 동질적 조건에서는 같은 편끼리,
이질적 조건에서는 반대편과 대화하도록 유도합니다.
대화 후 응답에서 숫자를 추출하여 의견을 업데이트하고,
중심(5)으로부터의 거리 변화로 극화/완화/불변을 판정합니다.

**해결하는 문제**: 소셜 미디어의 에코 챔버가 사회 양극화를 심화시킨다는 가설을 계산 실험으로 검증합니다.
소규모(10명)로도 논문의 대규모(1,000명) 실험과 유사한 경향을 재현할 수 있는지 확인합니다.
"""


# ── Environment (faithful to original PolarizationSocialSpace) ──

class PolarizationSocialSpace(EnvBase):
    """Social environment that tracks agent opinions and messaging."""

    def __init__(self, agent_profiles: list[dict]):
        super().__init__()
        self._opinions: dict[int, float] = {}
        self._chat_log: list[dict] = []
        self._agent_names: dict[int, str] = {}
        self._friends: dict[int, list[int]] = {}
        # Broadcast mechanism state
        self._inbox: dict[int, list[Message]] = {}
        self._message_log: list[Message] = []
        self._dropped_count: int = 0
        for p in agent_profiles:
            aid = p["id"]
            self._agent_names[aid] = p["name"]
            self._opinions[aid] = p.get("initial_opinion", 5.0)
            self._friends[aid] = p.get("friends", [])
            self._inbox[aid] = []

    @tool(readonly=True, kind="observe")
    def get_agent_opinion(self, agent_id: int) -> str:
        """Get an agent's current opinion on gun control (0-10 scale)."""
        opinion = self._opinions.get(agent_id, 5.0)
        name = self._agent_names.get(agent_id, f"Agent{agent_id}")
        stance = "supports" if opinion > 5 else "opposes" if opinion < 5 else "is neutral on"
        return f"{name} {stance} gun control (score: {opinion:.1f}/10)"

    @tool(readonly=True, kind="observe")
    def get_all_opinions(self) -> str:
        """Get all agents' opinions on gun control."""
        lines = [f"{self._agent_names.get(aid, f'Agent{aid}')}: {op:.1f}/10"
                 for aid, op in sorted(self._opinions.items())]
        return "Gun control opinions:\n" + "\n".join(lines)

    @tool(readonly=False)
    def update_opinion(self, agent_id: int, new_opinion: float) -> str:
        """Update an agent's opinion on gun control (0-10 scale)."""
        old = self._opinions.get(agent_id, 5.0)
        self._opinions[agent_id] = max(0, min(10, new_opinion))
        name = self._agent_names.get(agent_id, f"Agent{agent_id}")
        return f"{name} opinion updated: {old:.1f} -> {new_opinion:.1f}"

    @tool(readonly=False)
    def send_message(self, from_id: int, to_id: int, message: str) -> str:
        """Send a message from one agent to another."""
        self._chat_log.append({"from": from_id, "to": to_id, "message": message})
        return f"Message sent from {self._agent_names.get(from_id)} to {self._agent_names.get(to_id)}"

    @tool(readonly=True, kind="statistics")
    def get_opinion_statistics(self) -> str:
        """Get statistics about opinion distribution."""
        opinions = list(self._opinions.values())
        avg = sum(opinions) / len(opinions)
        support = sum(1 for o in opinions if o > 6)
        oppose = sum(1 for o in opinions if o < 4)
        neutral = len(opinions) - support - oppose
        return (f"Opinion Stats: avg={avg:.1f}, support={support}, oppose={oppose}, "
                f"neutral={neutral}, messages={len(self._chat_log)}")

    def get_opinions_snapshot(self) -> dict[int, float]:
        return dict(self._opinions)

    # ── Broadcast + propagation mechanism (paper §7.2 message_agent.py) ──

    def deliver(self, to_id: int, message: Message) -> bool:
        """Push a message into the recipient's inbox.

        Returns True if delivered, False if dropped for exceeding the hop cap.
        Recording drops lets the UI surface how many messages were filtered.
        """
        if message.propagation_count > MAX_PROPAGATION_COUNT:
            self._dropped_count += 1
            return False
        self._inbox[to_id].append(message)
        self._message_log.append(message)
        return True

    def drain_inbox(self, agent_id: int) -> list[Message]:
        msgs = self._inbox.get(agent_id, [])
        self._inbox[agent_id] = []
        return msgs

    def broadcast_from_persuader(
        self,
        persuader: str,        # "Agree" | "Disagree"
        side: str,             # "pro" | "con"
        content: str,
        citizen_ids: list[int],
        condition: str,        # "homophilic" | "heterogeneous" | "control"
    ) -> int:
        """Seed messages into citizen inboxes based on the experimental condition.

        - control        : every citizen receives the message
        - homophilic     : only citizens on the same side as the persuader
        - heterogeneous  : only citizens on the opposing side
        """
        delivered = 0
        for aid in citizen_ids:
            op = self._opinions.get(aid, 5.0)
            citizen_side = "pro" if op > 5 else "con" if op < 5 else None
            if condition == "homophilic" and citizen_side != side:
                continue
            if condition == "heterogeneous" and citizen_side == side:
                continue
            if self.deliver(aid, Message(
                content=content, side=side,
                propagation_count=1, origin_persuader=persuader,
            )):
                delivered += 1
        return delivered

    def get_propagation_stats(self) -> dict:
        total = len(self._message_log)
        by_hop: dict[int, int] = {}
        for m in self._message_log:
            by_hop[m.propagation_count] = by_hop.get(m.propagation_count, 0) + 1
        return {
            "total_delivered": total,
            "dropped_over_cap": self._dropped_count,
            "by_hop_count": by_hop,
        }


# ── Profile generation (faithful to original) ──

def _generate_profiles(n=10, seed=42):
    random.seed(seed)
    personalities = [
        "conservative and values traditional rights",
        "liberal and values public safety",
        "libertarian who prioritizes individual freedom",
        "moderate who weighs both sides carefully",
        "progressive who advocates for stricter regulations",
    ]
    profiles = []
    all_ids = list(range(1, n + 1))
    for i in range(n):
        aid = i + 1
        opinion = random.uniform(1.0, 4.0) if random.random() < 0.5 else random.uniform(6.0, 9.0)
        friends = random.sample([x for x in all_ids if x != aid], k=min(3, n - 1))
        profiles.append({
            "id": aid,
            "name": NAMES[i % len(NAMES)],
            "personality": random.choice(personalities),
            "initial_opinion": round(opinion, 1),
            "friends": friends,
        })
    return profiles


# ── UI ──

def render():
    st.header("Polarization Experiment (Paper Sec 7.2)")
    st.caption("Branch: `paper-polarization`")

    with st.expander("이 예제에 대하여", expanded=False):
        st.markdown(DESCRIPTION)

    col_a, col_b, col_c = st.columns(3)
    n_agents = cap("agents", col_a.number_input("Agents", 4, 20, 10))
    n_rounds = cap("rounds", col_b.number_input("Rounds", 1, 5, 2))
    seed = col_c.number_input("Random Seed", 0, 100, 42)

    mode = st.radio(
        "Execution mode",
        ["peer-to-peer (default)", "broadcast + propagation (paper §7.2)"],
        horizontal=True,
        help=(
            "peer-to-peer: 각 라운드마다 1쌍 대화 (빠름, 낮은 비용). "
            "broadcast: Agree/Disagree 설득자가 inbox에 메시지 주입, "
            "시민은 LLM으로 forward 결정, propagation_count>5면 drop (논문 구조)."
        ),
    )
    use_broadcast = mode.startswith("broadcast")

    conditions = st.multiselect(
        "Conditions",
        ["control", "homophilic", "heterogeneous"],
        default=["control", "homophilic", "heterogeneous"],
    )

    if st.button("Run Experiment") and conditions and ready_to_run(tag="polarization"):
        profiles = _generate_profiles(n_agents, seed)
        all_results = {}
        progress = st.progress(0)

        runner = _run_broadcast if use_broadcast else _run_condition

        for ci, cond in enumerate(conditions):
            st.subheader(f"Condition: {cond.upper()}")
            with st.spinner(f"Running {cond}..."):
                try:
                    result = asyncio.run(runner(cond, profiles, n_rounds))
                except Exception as e:
                    show_safe_error(e, context=f"Failed to run {cond}")
                    return
                all_results[cond] = result
            progress.progress((ci + 1) / len(conditions))

        # Visualization
        st.markdown("---")
        st.subheader("Opinion Distribution (Before vs After)")

        tabs = st.tabs([c.capitalize() for c in all_results.keys()])
        for tab, (cond, result) in zip(tabs, all_results.items()):
            with tab:
                fig = go.Figure()
                initial = list(result["initial"].values())
                final = list(result["final"].values())

                fig.add_trace(go.Scatter(
                    x=initial, y=[1]*len(initial), mode="markers",
                    name="Before", marker=dict(size=12, color="#3498db"),
                ))
                fig.add_trace(go.Scatter(
                    x=final, y=[0]*len(final), mode="markers",
                    name="After", marker=dict(size=12, color="#e74c3c"),
                ))
                for ini, fin in zip(initial, final):
                    fig.add_annotation(
                        x=fin, y=0, ax=ini, ay=1, xref="x", yref="y",
                        axref="x", ayref="y", showarrow=True,
                        arrowhead=2, arrowsize=1, arrowcolor="#95a5a6", opacity=0.5,
                    )
                fig.update_layout(
                    xaxis=dict(title="Opinion (0=Oppose, 10=Support)", range=[-0.5, 10.5]),
                    yaxis=dict(visible=False, range=[-0.5, 1.5]),
                    height=250,
                )
                st.plotly_chart(fig, use_container_width=True)

                st.write(f"Polarized: **{result['polarized_pct']}%** | "
                         f"Moderated: **{result['moderated_pct']}%** | "
                         f"Unchanged: **{result['unchanged']}**")

        st.markdown("---")
        st.subheader("Comparison with Paper")
        paper = {"control": (39, 33), "homophilic": (52, None), "heterogeneous": (None, 89)}
        rows = []
        for cond in all_results:
            r = all_results[cond]
            pp, pm = paper.get(cond, (None, None))
            rows.append({
                "Condition": cond,
                "Polarized (%)": r["polarized_pct"],
                "Paper Polarized": pp or "-",
                "Moderated (%)": r["moderated_pct"],
                "Paper Moderated": pm or "-",
            })
        st.table(rows)

        # Broadcast mode — show propagation statistics (paper §7.2 message_agent)
        if use_broadcast:
            st.markdown("---")
            st.subheader("Propagation Statistics")
            for cond, r in all_results.items():
                stats = r.get("propagation_stats")
                if not stats:
                    continue
                with st.expander(f"{cond}: delivered={stats['total_delivered']}, "
                                 f"dropped (hop>5)={stats['dropped_over_cap']}"):
                    hops = sorted(stats["by_hop_count"].items())
                    st.table([{"hop": h, "message count": c} for h, c in hops])


# ── Experiment logic (faithful to original run_condition) ──

async def _run_condition(condition, profiles, num_rounds):
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from datetime import datetime

    env = PolarizationSocialSpace(agent_profiles=profiles)
    agents = [PersonAgent(id=p["id"], profile={
        "name": p["name"], "personality": p["personality"],
        "background": f"Opinion on gun control: {p['initial_opinion']:.1f}/10 (0=oppose, 10=support)",
    }) for p in profiles]

    society = AgentSociety(agents=agents, env_router=CodeGenRouter(env_modules=[env]),
                           start_t=datetime.now())
    await society.init()
    initial = env.get_opinions_snapshot()

    for rnd in range(num_rounds):
        for p in profiles:
            aid = p["id"]

            if condition == "homophilic":
                # Select peer with same-side opinion (faithful to original)
                same = [pr["id"] for pr in profiles if pr["id"] != aid
                        and (initial[pr["id"]] > 5) == (initial[aid] > 5)]
                peer_id = random.choice(same) if same else random.choice(p["friends"])
                peer_name = env._agent_names.get(peer_id, f"Agent{peer_id}")
                msg = (f"You are {p['name']}. Your opinion on gun control: {initial[aid]:.1f}/10. "
                       f"You are talking with {peer_name} who AGREES with you on gun control. "
                       f"After discussion, state your updated opinion as a number 0-10.")

            elif condition == "heterogeneous":
                # Select peer with opposing opinion (faithful to original)
                opp = [pr["id"] for pr in profiles if pr["id"] != aid
                       and (initial[pr["id"]] > 5) != (initial[aid] > 5)]
                peer_id = random.choice(opp) if opp else random.choice(p["friends"])
                peer_name = env._agent_names.get(peer_id, f"Agent{peer_id}")
                msg = (f"You are {p['name']}. Your opinion on gun control: {initial[aid]:.1f}/10. "
                       f"You are talking with {peer_name} who DISAGREES with you on gun control. "
                       f"Listen carefully to their perspective. State your updated opinion as a number 0-10.")

            else:  # control
                msg = (f"You are {p['name']}. Your opinion on gun control: {initial[aid]:.1f}/10. "
                       f"Discuss gun control naturally. State your updated opinion as a number 0-10.")

            resp = await society.ask(msg)
            match = re.search(r"(\d+(?:\.\d+)?)", resp)
            if match:
                env._opinions[aid] = max(0, min(10, float(match.group(1))))

    final = env.get_opinions_snapshot()
    await society.close()

    polarized = moderated = unchanged = 0
    for aid in initial:
        d_init = abs(initial[aid] - 5)
        d_final = abs(final[aid] - 5)
        if d_final > d_init + 0.5:
            polarized += 1
        elif d_final < d_init - 0.5:
            moderated += 1
        else:
            unchanged += 1

    total = len(initial)
    return {
        "condition": condition,
        "polarized_pct": round(100 * polarized / total, 1),
        "moderated_pct": round(100 * moderated / total, 1),
        "unchanged": unchanged,
        "initial": {env._agent_names[k]: v for k, v in initial.items()},
        "final": {env._agent_names[k]: v for k, v in final.items()},
    }


# ── Broadcast + propagation runner (paper message_agent.py equivalent) ──

AGREE_PROMPT = (
    "You think stronger gun control is a good idea. "
    "In one sentence, persuade a friend to support it."
)
DISAGREE_PROMPT = (
    "You think stronger gun control is a bad idea. "
    "In one sentence, persuade a friend to oppose it."
)


async def _run_broadcast(condition, profiles, num_rounds):
    """Broadcast variant: persuader agents inject messages, citizens forward with hop cap."""
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from datetime import datetime

    env = PolarizationSocialSpace(agent_profiles=profiles)
    citizen_ids = [p["id"] for p in profiles]

    agents = [PersonAgent(id=p["id"], profile={
        "name": p["name"], "personality": p["personality"],
        "background": f"Opinion on gun control: {p['initial_opinion']:.1f}/10 (0=oppose, 10=support)",
    }) for p in profiles]

    society = AgentSociety(agents=agents, env_router=CodeGenRouter(env_modules=[env]),
                           start_t=datetime.now())
    await society.init()
    initial = env.get_opinions_snapshot()

    # Generate persuader messages once per run (offline prompt; no per-round LLM cost)
    agree_msg = "Background checks save lives. Reasonable rules won't take your rights away."
    disagree_msg = "Gun rights are foundational. More regulation won't stop crime, only law-abiding owners."

    for rnd in range(num_rounds):
        # Step 1: persuaders broadcast this round
        env.broadcast_from_persuader(
            persuader="Agree", side="pro", content=agree_msg,
            citizen_ids=citizen_ids, condition=condition,
        )
        env.broadcast_from_persuader(
            persuader="Disagree", side="con", content=disagree_msg,
            citizen_ids=citizen_ids, condition=condition,
        )

        # Step 2: each citizen processes inbox → LLM decides forward + updated opinion
        for p in profiles:
            aid = p["id"]
            msgs = env.drain_inbox(aid)
            if not msgs:
                continue
            # Aggregate incoming messages into a single prompt to save tokens.
            incoming = "\n".join(
                f"- [{m.origin_persuader} says]: {m.content} (hop {m.propagation_count})"
                for m in msgs
            )
            resp = await society.ask(
                f"You are {p['name']}. Your opinion on gun control: {env._opinions[aid]:.1f}/10. "
                f"Received messages:\n{incoming}\n"
                "Decide: (1) state your updated opinion 0-10, "
                "(2) reply FORWARD or KEEP — should you pass these along to your friends?"
            )
            m_num = re.search(r"(\d+(?:\.\d+)?)", resp)
            if m_num:
                env._opinions[aid] = max(0, min(10, float(m_num.group(1))))

            if "forward" in resp.lower():
                # Propagate each message to this citizen's friends with hop++.
                # Split the hop budget across messages; deliver() drops hop > 5.
                for m in msgs:
                    forwarded = Message(
                        content=m.content, side=m.side,
                        propagation_count=m.propagation_count + 1,
                        origin_persuader=m.origin_persuader,
                    )
                    for fid in p["friends"]:
                        env.deliver(fid, forwarded)

    final = env.get_opinions_snapshot()
    await society.close()

    polarized = moderated = unchanged = 0
    for aid in initial:
        d_init = abs(initial[aid] - 5)
        d_final = abs(final[aid] - 5)
        if d_final > d_init + 0.5:
            polarized += 1
        elif d_final < d_init - 0.5:
            moderated += 1
        else:
            unchanged += 1

    total = len(initial)
    return {
        "condition": condition,
        "polarized_pct": round(100 * polarized / total, 1),
        "moderated_pct": round(100 * moderated / total, 1),
        "unchanged": unchanged,
        "initial": {env._agent_names[k]: v for k, v in initial.items()},
        "final": {env._agent_names[k]: v for k, v in final.items()},
        "propagation_stats": env.get_propagation_stats(),
    }
