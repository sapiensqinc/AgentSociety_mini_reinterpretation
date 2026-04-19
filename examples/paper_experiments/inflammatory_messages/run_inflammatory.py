"""
Paper Reproduction: Spread of Inflammatory Messages (Section 7.3)

Reproduces the inflammatory message propagation experiment based on
the chained woman incident (Xuzhou). Tests information spread and
emotional dynamics under different intervention strategies.

Original paper findings:
  - Inflammatory messages have stronger viral potential than regular content
  - Node intervention (account suspension) > Edge intervention (connection removal)
  - Sharing driven by emotional reactions and social responsibility

Uses agentsociety2 (v2) API.
Usage: python run_inflammatory.py
"""

import asyncio
import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv
load_dotenv()

from agentsociety2 import PersonAgent
from agentsociety2.env import EnvBase, tool, CodeGenRouter
from agentsociety2.society import AgentSociety


class SocialMediaSpace(EnvBase):
    """Social media environment with content moderation capabilities."""

    def __init__(self, agent_profiles: List[Dict]):
        super().__init__()
        self._names: Dict[int, str] = {}
        self._emotions: Dict[int, float] = {}  # 0=calm, 1=highly emotional
        self._received_info: Dict[int, bool] = {}
        self._messages: List[Dict] = []
        self._banned_agents: set = set()
        self._removed_edges: set = set()
        self._friends: Dict[int, List[int]] = {}
        self._infraction_count: Dict[int, int] = {}

        for p in agent_profiles:
            aid = p["id"]
            self._names[aid] = p["name"]
            self._emotions[aid] = 0.1
            self._received_info[aid] = False
            self._friends[aid] = p.get("friends", [])
            self._infraction_count[aid] = 0

    @tool(readonly=True, kind="observe")
    def get_agent_state(self, agent_id: int) -> str:
        """Get agent emotional state and info awareness."""
        name = self._names.get(agent_id, f"Agent{agent_id}")
        emo = self._emotions.get(agent_id, 0.0)
        informed = self._received_info.get(agent_id, False)
        banned = agent_id in self._banned_agents
        return (f"{name}: emotion={emo:.2f}, informed={informed}, banned={banned}")

    @tool(readonly=False)
    def share_message(self, from_id: int, to_id: int, content: str, is_inflammatory: bool = False) -> str:
        """Share a message. Subject to moderation."""
        if from_id in self._banned_agents:
            return f"Agent {from_id} is banned and cannot send messages."
        edge = (min(from_id, to_id), max(from_id, to_id))
        if edge in self._removed_edges:
            return f"Connection between {from_id} and {to_id} has been removed."

        self._messages.append({
            "from": from_id, "to": to_id, "content": content,
            "inflammatory": is_inflammatory, "time": datetime.now().isoformat()
        })
        self._received_info[to_id] = True
        if is_inflammatory:
            self._infraction_count[from_id] = self._infraction_count.get(from_id, 0) + 1
        return f"Message delivered from {self._names[from_id]} to {self._names[to_id]}"

    @tool(readonly=False)
    def update_emotion(self, agent_id: int, emotion_level: float) -> str:
        """Update agent emotional intensity (0-1)."""
        self._emotions[agent_id] = max(0, min(1, emotion_level))
        return f"{self._names[agent_id]} emotion updated to {emotion_level:.2f}"

    @tool(readonly=True, kind="statistics")
    def get_spread_statistics(self) -> str:
        """Get information spread and emotion statistics."""
        total = len(self._names)
        informed = sum(1 for v in self._received_info.values() if v)
        avg_emotion = sum(self._emotions.values()) / total if total else 0
        return (
            f"Spread: {informed}/{total} ({100*informed/total:.0f}%), "
            f"Avg emotion: {avg_emotion:.2f}, Messages: {len(self._messages)}, "
            f"Banned: {len(self._banned_agents)}, Removed edges: {len(self._removed_edges)}"
        )

    def apply_node_intervention(self, threshold: int = 2):
        """Ban agents who shared inflammatory content above threshold."""
        for aid, count in self._infraction_count.items():
            if count >= threshold:
                self._banned_agents.add(aid)

    def apply_edge_intervention(self):
        """Remove connections where inflammatory content was shared."""
        for msg in self._messages:
            if msg.get("inflammatory"):
                edge = (min(msg["from"], msg["to"]), max(msg["from"], msg["to"]))
                self._removed_edges.add(edge)

    def get_metrics(self) -> Dict:
        total = len(self._names)
        informed = sum(1 for v in self._received_info.values() if v)
        avg_emotion = sum(self._emotions.values()) / total
        return {
            "spread_ratio": informed / total,
            "avg_emotion": avg_emotion,
            "total_messages": len(self._messages),
            "banned": len(self._banned_agents),
            "removed_edges": len(self._removed_edges),
        }


def generate_network(n: int = 15) -> List[Dict]:
    """Generate a small-world social network."""
    names = [f"User_{i}" for i in range(1, n + 1)]
    profiles = []
    all_ids = list(range(1, n + 1))
    for i in range(n):
        aid = i + 1
        friends = random.sample([x for x in all_ids if x != aid], k=min(4, n - 1))
        profiles.append({"id": aid, "name": names[i], "friends": friends})
    return profiles


async def run_experiment(
    condition: str, profiles: List[Dict], seed_agents: List[int],
    seed_message: str, is_inflammatory: bool, num_steps: int = 5,
) -> Dict:
    print(f"\n{'='*50}\n  {condition.upper()}\n{'='*50}")

    env = SocialMediaSpace(agent_profiles=profiles)

    # Seed initial information
    for sid in seed_agents:
        env._received_info[sid] = True
        env._emotions[sid] = 0.6 if is_inflammatory else 0.2

    agents = [
        PersonAgent(id=p["id"], profile={
            "name": p["name"],
            "personality": "socially aware and empathetic",
        })
        for p in profiles
    ]
    society = AgentSociety(
        agents=agents, env_router=CodeGenRouter(env_modules=[env]), start_t=datetime.now(),
    )
    await society.init()

    metrics_over_time = []

    for step in range(1, num_steps + 1):
        print(f"  Step {step}/{num_steps}...")

        for p in profiles:
            aid = p["id"]
            if aid in env._banned_agents:
                continue
            if not env._received_info[aid]:
                continue

            # Agent decides whether to share
            resp = await society.ask(
                f"You are {p['name']}. You received this news: '{seed_message}'. "
                f"Your emotional intensity is {env._emotions[aid]:.1f}/1.0. "
                f"Would you share this with friends? Reply YES or NO, "
                f"then rate your emotional intensity 0-1."
            )

            will_share = "yes" in resp.lower()
            match = re.search(r"(\d+\.?\d*)", resp)
            if match:
                new_emo = max(0, min(1, float(match.group(1))))
                env._emotions[aid] = new_emo

            if will_share:
                available_friends = [
                    f for f in p["friends"]
                    if f not in env._banned_agents
                    and (min(aid, f), max(aid, f)) not in env._removed_edges
                ]
                for fid in available_friends[:2]:
                    env.share_message(aid, fid, seed_message, is_inflammatory)

        # Apply interventions
        if "node" in condition:
            env.apply_node_intervention(threshold=2)
        elif "edge" in condition:
            env.apply_edge_intervention()

        m = env.get_metrics()
        metrics_over_time.append({"step": step, **m})
        print(f"    Spread: {m['spread_ratio']:.0%}, Emotion: {m['avg_emotion']:.2f}")

    await society.close()

    return {"condition": condition, "metrics": metrics_over_time, "final": env.get_metrics()}


async def main():
    print("INFLAMMATORY MESSAGES EXPERIMENT (Paper Section 7.3)")
    random.seed(42)

    N = 12
    profiles = generate_network(N)
    seeds = [1, 2]  # Seed agents
    normal_msg = "A woman was found in difficult circumstances in a rural village. Authorities are investigating."
    inflammatory_msg = "SHOCKING: Woman found chained in village! Government cover-up! Share before they delete this!"

    results = []

    # Control: non-inflammatory seed
    results.append(await run_experiment(
        "control", profiles, seeds, normal_msg, False, num_steps=4))

    # Experimental: inflammatory seed
    results.append(await run_experiment(
        "experimental", profiles, seeds, inflammatory_msg, True, num_steps=4))

    # Node intervention
    results.append(await run_experiment(
        "node_intervention", profiles, seeds, inflammatory_msg, True, num_steps=4))

    # Edge intervention
    results.append(await run_experiment(
        "edge_intervention", profiles, seeds, inflammatory_msg, True, num_steps=4))

    out = Path("results/inflammatory")
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'Condition':<25}{'Spread':<12}{'Emotion':<12}")
    print("-" * 49)
    for r in results:
        f = r["final"]
        print(f"{r['condition']:<25}{f['spread_ratio']:>6.0%}      {f['avg_emotion']:>6.2f}")

    print(f"\nPaper: inflammatory > control in both spread and emotion")
    print(f"Paper: node intervention > edge intervention in containment")
    print(f"Results saved to: {out / 'results.json'}")


if __name__ == "__main__":
    asyncio.run(main())
