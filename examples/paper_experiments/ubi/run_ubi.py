"""
Paper Reproduction: Universal Basic Income Experiment (Section 7.4)

Reproduces the UBI policy experiment from the AgentSociety paper.
Compares economic and social metrics with/without $1000/month UBI.

Original paper findings:
  - UBI increases consumption levels
  - UBI reduces depression levels
  - Agent interviews reveal concerns about interest rates, long-term benefits, savings

Uses agentsociety2 (v2) API.
Usage: python run_ubi.py
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


class EconomySpace(EnvBase):
    """Simplified economic environment for UBI experiment."""

    def __init__(self, agent_profiles: List[Dict], ubi_amount: float = 0):
        super().__init__()
        self._names: Dict[int, str] = {}
        self._income: Dict[int, float] = {}
        self._savings: Dict[int, float] = {}
        self._consumption: Dict[int, float] = {}
        self._happiness: Dict[int, float] = {}
        self._ubi = ubi_amount

        for p in agent_profiles:
            aid = p["id"]
            self._names[aid] = p["name"]
            self._income[aid] = p.get("income", 3000)
            self._savings[aid] = p.get("savings", 5000)
            self._consumption[aid] = 0
            self._happiness[aid] = p.get("happiness", 5.0)

    @tool(readonly=True, kind="observe")
    def get_economic_status(self, agent_id: int) -> str:
        """Get agent economic status."""
        name = self._names.get(agent_id, f"Agent{agent_id}")
        disposable = self._income[agent_id] + self._ubi
        return (
            f"{name}: income=${self._income[agent_id]:.0f}, "
            f"UBI=${self._ubi:.0f}, disposable=${disposable:.0f}, "
            f"savings=${self._savings[agent_id]:.0f}, happiness={self._happiness[agent_id]:.1f}/10"
        )

    @tool(readonly=False)
    def make_consumption_decision(self, agent_id: int, amount: float) -> str:
        """Agent decides to spend a certain amount."""
        disposable = self._income[agent_id] + self._ubi
        actual = min(amount, disposable + self._savings[agent_id])
        self._consumption[agent_id] += actual
        self._savings[agent_id] += (disposable - actual)
        name = self._names[agent_id]
        return f"{name} spent ${actual:.0f}. Remaining savings: ${self._savings[agent_id]:.0f}"

    @tool(readonly=False)
    def update_happiness(self, agent_id: int, score: float) -> str:
        """Update agent happiness/wellbeing score (0-10)."""
        self._happiness[agent_id] = max(0, min(10, score))
        return f"{self._names[agent_id]} happiness: {score:.1f}/10"

    @tool(readonly=True, kind="statistics")
    def get_economy_statistics(self) -> str:
        """Get aggregate economic statistics."""
        n = len(self._names)
        avg_consumption = sum(self._consumption.values()) / n
        avg_savings = sum(self._savings.values()) / n
        avg_happiness = sum(self._happiness.values()) / n
        gdp = sum(self._consumption.values())
        return (
            f"GDP: ${gdp:.0f}, Avg consumption: ${avg_consumption:.0f}, "
            f"Avg savings: ${avg_savings:.0f}, Avg happiness: {avg_happiness:.1f}/10"
        )

    def get_metrics(self) -> Dict:
        n = len(self._names)
        return {
            "avg_consumption": sum(self._consumption.values()) / n,
            "avg_savings": sum(self._savings.values()) / n,
            "avg_happiness": sum(self._happiness.values()) / n,
            "gdp": sum(self._consumption.values()),
        }


def generate_texas_profiles(n: int = 10) -> List[Dict]:
    """Generate profiles loosely based on Texas demographics."""
    occupations = ["retail worker", "teacher", "nurse", "truck driver",
                   "software engineer", "construction worker", "cashier",
                   "waiter", "office clerk", "mechanic"]
    profiles = []
    for i in range(n):
        income = random.gauss(3500, 1500)
        income = max(1200, min(8000, income))
        profiles.append({
            "id": i + 1,
            "name": f"Resident_{i+1}",
            "occupation": occupations[i % len(occupations)],
            "income": round(income),
            "savings": round(random.uniform(1000, 15000)),
            "happiness": round(random.uniform(3, 7), 1),
        })
    return profiles


async def run_simulation(profiles: List[Dict], ubi: float, num_rounds: int = 3) -> Dict:
    label = f"UBI=${ubi:.0f}" if ubi > 0 else "No UBI"
    print(f"\n{'='*50}\n  {label}\n{'='*50}")

    env = EconomySpace(agent_profiles=profiles, ubi_amount=ubi)
    agents = [
        PersonAgent(id=p["id"], profile={
            "name": p["name"],
            "personality": f"a {p['occupation']} trying to make ends meet",
            "background": f"Monthly income: ${p['income']}, Savings: ${p['savings']}",
        })
        for p in profiles
    ]
    society = AgentSociety(
        agents=agents, env_router=CodeGenRouter(env_modules=[env]), start_t=datetime.now(),
    )
    await society.init()

    metrics_timeline = []
    for rnd in range(1, num_rounds + 1):
        print(f"  Month {rnd}/{num_rounds}...")
        for p in profiles:
            disposable = p["income"] + ubi
            resp = await society.ask(
                f"You are {p['name']}, a {p['occupation']}. "
                f"Your monthly disposable income is ${disposable:.0f} "
                f"(base ${p['income']:.0f}" + (f" + UBI ${ubi:.0f}" if ubi > 0 else "") + "). "
                f"Savings: ${env._savings[p['id']]:.0f}. "
                f"How much will you spend this month? Give a dollar amount. "
                f"Also rate your happiness 0-10."
            )
            # Parse spending
            amounts = re.findall(r"\$?(\d+(?:,\d{3})*(?:\.\d+)?)", resp)
            if amounts:
                spend = float(amounts[0].replace(",", ""))
                env._consumption[p["id"]] += min(spend, disposable + env._savings[p["id"]])
                env._savings[p["id"]] = max(0, env._savings[p["id"]] + disposable - spend)
            # Parse happiness
            hap = re.findall(r"(\d+(?:\.\d+)?)\s*/?\s*10", resp)
            if hap:
                env._happiness[p["id"]] = max(0, min(10, float(hap[0])))

        m = env.get_metrics()
        metrics_timeline.append({"month": rnd, **m})
        print(f"    Avg consumption: ${m['avg_consumption']:.0f}, Happiness: {m['avg_happiness']:.1f}")

    # Interview about UBI
    interview_results = []
    if ubi > 0:
        print("  Interviewing agents about UBI...")
        for p in profiles[:3]:
            resp = await society.ask(
                f"You are {p['name']}. You have been receiving ${ubi}/month in UBI. "
                f"What is your opinion on this policy? How has it affected your life? "
                f"Be specific about spending, savings, and wellbeing."
            )
            interview_results.append({"agent": p["name"], "response": resp[:300]})

    await society.close()
    return {
        "label": label, "ubi_amount": ubi,
        "metrics": metrics_timeline, "final": env.get_metrics(),
        "interviews": interview_results,
    }


async def main():
    print("UBI EXPERIMENT (Paper Section 7.4)")
    random.seed(42)

    profiles = generate_texas_profiles(8)
    print(f"Agents: {len(profiles)}")
    for p in profiles:
        print(f"  {p['name']} ({p['occupation']}): income=${p['income']}, savings=${p['savings']}")

    r_no_ubi = await run_simulation(profiles, ubi=0, num_rounds=3)
    r_ubi = await run_simulation(profiles, ubi=1000, num_rounds=3)

    out = Path("results/ubi")
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "results.json", "w") as f:
        json.dump([r_no_ubi, r_ubi], f, indent=2)

    print(f"\n{'Metric':<25}{'No UBI':<15}{'With UBI':<15}")
    print("-" * 55)
    for key in ["avg_consumption", "avg_savings", "avg_happiness"]:
        v1 = r_no_ubi["final"][key]
        v2 = r_ubi["final"][key]
        fmt = ".1f" if "happiness" in key else ".0f"
        print(f"{key:<25}{v1:>10{fmt}}     {v2:>10{fmt}}")

    print(f"\nPaper: UBI increases consumption, reduces depression")
    print(f"Results saved to: {out / 'results.json'}")


if __name__ == "__main__":
    asyncio.run(main())
