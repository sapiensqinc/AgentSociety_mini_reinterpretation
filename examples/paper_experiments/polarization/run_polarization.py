"""
Paper Reproduction: Polarization Experiment (Section 7.2)

Reproduces the gun control opinion polarization experiment from the AgentSociety paper.
Three conditions: control, homophilic (echo chamber), heterogeneous interaction.

Original paper findings:
  - Control: 39% polarized, 33% moderated
  - Homophilic: 52% polarized (echo chamber effect)
  - Heterogeneous: 89% moderated, 11% adopted opposing views

This version uses agentsociety2 (v2) API.
Usage: python run_polarization.py
"""

import asyncio
import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
load_dotenv()

from agentsociety2 import PersonAgent
from agentsociety2.env import EnvBase, tool, CodeGenRouter
from agentsociety2.society import AgentSociety


class PolarizationSocialSpace(EnvBase):
    """Social environment that tracks agent opinions and messaging."""

    def __init__(self, agent_profiles: List[Dict]):
        super().__init__()
        self._opinions: Dict[int, float] = {}
        self._chat_log: List[Dict] = []
        self._agent_names: Dict[int, str] = {}

        for p in agent_profiles:
            aid = p["id"]
            self._agent_names[aid] = p["name"]
            self._opinions[aid] = p.get("initial_opinion", 5.0)

    @tool(readonly=True, kind="observe")
    def get_agent_opinion(self, agent_id: int) -> str:
        """Get an agent current opinion on gun control (0-10 scale)."""
        opinion = self._opinions.get(agent_id, 5.0)
        name = self._agent_names.get(agent_id, f"Agent{agent_id}")
        stance = "supports" if opinion > 5 else "opposes" if opinion < 5 else "is neutral on"
        return f"{name} {stance} gun control (score: {opinion:.1f}/10)"

    @tool(readonly=True, kind="observe")
    def get_all_opinions(self) -> str:
        """Get all agents opinions on gun control."""
        lines = []
        for aid, opinion in sorted(self._opinions.items()):
            name = self._agent_names.get(aid, f"Agent{aid}")
            lines.append(f"{name}: {opinion:.1f}/10")
        return "Gun control opinions:\n" + "\n".join(lines)

    @tool(readonly=False)
    def update_opinion(self, agent_id: int, new_opinion: float) -> str:
        """Update an agent opinion on gun control (0-10 scale)."""
        old = self._opinions.get(agent_id, 5.0)
        self._opinions[agent_id] = max(0, min(10, new_opinion))
        name = self._agent_names.get(agent_id, f"Agent{agent_id}")
        return f"{name} opinion updated: {old:.1f} -> {new_opinion:.1f}"

    @tool(readonly=False)
    def send_message(self, from_id: int, to_id: int, message: str) -> str:
        """Send a message from one agent to another."""
        self._chat_log.append({
            "from": from_id, "to": to_id,
            "message": message, "time": datetime.now().isoformat()
        })
        return f"Message sent from {self._agent_names.get(from_id)} to {self._agent_names.get(to_id)}"

    @tool(readonly=True, kind="statistics")
    def get_opinion_statistics(self) -> str:
        """Get statistics about opinion distribution."""
        opinions = list(self._opinions.values())
        avg = sum(opinions) / len(opinions)
        support = sum(1 for o in opinions if o > 6)
        oppose = sum(1 for o in opinions if o < 4)
        neutral = len(opinions) - support - oppose
        return (
            f"Opinion Stats: avg={avg:.1f}, support={support}, oppose={oppose}, "
            f"neutral={neutral}, messages={len(self._chat_log)}"
        )

    def get_opinions_snapshot(self) -> Dict[int, float]:
        return dict(self._opinions)


def generate_profiles(n: int = 10) -> List[Dict]:
    names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey",
             "Riley", "Quinn", "Avery", "Cameron", "Dakota"]
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
            "name": names[i % len(names)],
            "personality": random.choice(personalities),
            "initial_opinion": round(opinion, 1),
            "friends": friends,
        })
    return profiles


async def run_condition(condition: str, profiles: List[Dict], num_rounds: int = 2) -> Dict:
    print(f"\n{'='*50}\n  Condition: {condition.upper()}\n{'='*50}")

    env = PolarizationSocialSpace(agent_profiles=profiles)
    agents = [
        PersonAgent(id=p["id"], profile={
            "name": p["name"],
            "personality": p["personality"],
            "background": f"Opinion on gun control: {p['initial_opinion']:.1f}/10 (0=oppose, 10=support)",
        })
        for p in profiles
    ]

    society = AgentSociety(
        agents=agents, env_router=CodeGenRouter(env_modules=[env]), start_t=datetime.now(),
    )
    await society.init()
    initial = env.get_opinions_snapshot()

    for rnd in range(1, num_rounds + 1):
        print(f"  Round {rnd}/{num_rounds}...")
        for p in profiles:
            aid = p["id"]
            if condition == "homophilic":
                same = [pr["id"] for pr in profiles if pr["id"] != aid
                        and (initial[pr["id"]] > 5) == (initial[aid] > 5)]
                peer = random.choice(same) if same else random.choice(p["friends"])
                msg = (f"You are {p['name']}. Opinion: {initial[aid]:.1f}/10. "
                       f"Talk with someone who AGREES with you on gun control. "
                       f"After discussion, state your updated opinion as a number 0-10.")
            elif condition == "heterogeneous":
                opp = [pr["id"] for pr in profiles if pr["id"] != aid
                       and (initial[pr["id"]] > 5) != (initial[aid] > 5)]
                peer = random.choice(opp) if opp else random.choice(p["friends"])
                msg = (f"You are {p['name']}. Opinion: {initial[aid]:.1f}/10. "
                       f"Talk with someone who DISAGREES with you on gun control. "
                       f"Listen carefully. State your updated opinion as a number 0-10.")
            else:
                msg = (f"You are {p['name']}. Opinion: {initial[aid]:.1f}/10. "
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
    result = {
        "condition": condition, "polarized_pct": round(100 * polarized / total, 1),
        "moderated_pct": round(100 * moderated / total, 1), "unchanged": unchanged,
        "initial": {str(k): v for k, v in initial.items()},
        "final": {str(k): v for k, v in final.items()},
    }
    print(f"  -> Polarized: {result['polarized_pct']}%, Moderated: {result['moderated_pct']}%")
    return result


async def main():
    print("POLARIZATION EXPERIMENT (Paper Section 7.2)")
    random.seed(42)
    profiles = generate_profiles(10)

    results = []
    for cond in ["control", "homophilic", "heterogeneous"]:
        results.append(await run_condition(cond, profiles, num_rounds=2))

    out = Path("results/polarization")
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'Condition':<20}{'Polarized':<15}{'Moderated':<15}")
    print("-" * 50)
    for r in results:
        print(f"{r['condition']:<20}{r['polarized_pct']:>6.1f}%       {r['moderated_pct']:>6.1f}%")
    print(f"\nPaper: Control=39%/33%, Homophilic=52%/-, Heterogeneous=-/89%")
    print(f"Results saved to: {out / 'results.json'}")


if __name__ == "__main__":
    asyncio.run(main())
