"""
Paper Reproduction: External Shocks of Hurricane (Section 7.5)

Reproduces the Hurricane Dorian mobility impact experiment from the paper.
Simulates how agents adjust mobility behavior in response to weather events.

Original paper findings:
  - Activity level drops from 70-90% to ~30% during hurricane landfall
  - Recovery to normal levels after hurricane passes
  - Simulated daily trips align with real SafeGraph data patterns

Uses agentsociety2 (v2) API.
Usage: python run_hurricane.py
"""

import asyncio
import json
import random
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
load_dotenv()

from agentsociety2 import PersonAgent
from agentsociety2.env import EnvBase, tool, CodeGenRouter
from agentsociety2.society import AgentSociety


class WeatherMobilitySpace(EnvBase):
    """Environment simulating weather conditions and mobility tracking."""

    def __init__(self, agent_profiles: List[Dict]):
        super().__init__()
        self._names: Dict[int, str] = {}
        self._is_traveling: Dict[int, bool] = {}
        self._trip_count: Dict[int, int] = {}
        self._weather = "clear"
        self._temperature = 85  # Fahrenheit
        self._wind_speed = 10
        self._hurricane_active = False

        for p in agent_profiles:
            aid = p["id"]
            self._names[aid] = p["name"]
            self._is_traveling[aid] = False
            self._trip_count[aid] = 0

    @tool(readonly=True, kind="observe")
    def get_weather(self, agent_id: int = 0) -> str:
        """Get current weather conditions."""
        status = "HURRICANE WARNING - Stay indoors!" if self._hurricane_active else "Normal conditions"
        return (
            f"Weather: {self._weather}, Temp: {self._temperature}F, "
            f"Wind: {self._wind_speed}mph. Status: {status}"
        )

    @tool(readonly=False)
    def decide_travel(self, agent_id: int, will_travel: bool, destination: str = "") -> str:
        """Agent decides whether to travel today."""
        self._is_traveling[agent_id] = will_travel
        if will_travel:
            self._trip_count[agent_id] += 1
        name = self._names[agent_id]
        if will_travel:
            return f"{name} decided to travel to {destination}"
        return f"{name} decided to stay home"

    @tool(readonly=True, kind="statistics")
    def get_activity_statistics(self) -> str:
        """Get mobility activity statistics."""
        total = len(self._names)
        active = sum(1 for v in self._is_traveling.values() if v)
        level = active / total if total else 0
        return (
            f"Activity level: {level:.0%} ({active}/{total} traveling), "
            f"Weather: {self._weather}, Hurricane: {self._hurricane_active}"
        )

    def set_weather(self, weather: str, temp: int, wind: int, hurricane: bool):
        self._weather = weather
        self._temperature = temp
        self._wind_speed = wind
        self._hurricane_active = hurricane

    def reset_daily_travel(self):
        for aid in self._is_traveling:
            self._is_traveling[aid] = False

    def get_activity_level(self) -> float:
        total = len(self._names)
        active = sum(1 for v in self._is_traveling.values() if v)
        return active / total if total else 0


def generate_columbia_profiles(n: int = 15) -> List[Dict]:
    """Generate profiles for Columbia, SC residents."""
    profiles = []
    for i in range(n):
        profiles.append({
            "id": i + 1,
            "name": f"Resident_{i+1}",
            "occupation": random.choice([
                "office worker", "teacher", "retail worker",
                "healthcare worker", "student", "retiree",
            ]),
            "age": random.randint(22, 70),
        })
    return profiles


# Weather schedule: 9-day Hurricane Dorian simulation
WEATHER_SCHEDULE = [
    # Day 1-3: Before landfall (Aug 28-30)
    {"day": 1, "label": "Aug 28 (Before)", "weather": "partly cloudy", "temp": 88, "wind": 12, "hurricane": False},
    {"day": 2, "label": "Aug 29 (Before)", "weather": "cloudy", "temp": 84, "wind": 18, "hurricane": False},
    {"day": 3, "label": "Aug 30 (Before)", "weather": "overcast with rain", "temp": 78, "wind": 30, "hurricane": False},
    # Day 4-6: Landfall (Aug 31 - Sep 2)
    {"day": 4, "label": "Aug 31 (Landfall)", "weather": "severe storm", "temp": 72, "wind": 75, "hurricane": True},
    {"day": 5, "label": "Sep 1 (Landfall)", "weather": "hurricane conditions", "temp": 70, "wind": 95, "hurricane": True},
    {"day": 6, "label": "Sep 2 (Landfall)", "weather": "tropical storm", "temp": 74, "wind": 55, "hurricane": True},
    # Day 7-9: After landfall (Sep 3-5)
    {"day": 7, "label": "Sep 3 (After)", "weather": "rain clearing", "temp": 80, "wind": 25, "hurricane": False},
    {"day": 8, "label": "Sep 4 (After)", "weather": "partly cloudy", "temp": 84, "wind": 15, "hurricane": False},
    {"day": 9, "label": "Sep 5 (After)", "weather": "clear skies", "temp": 87, "wind": 10, "hurricane": False},
]


async def main():
    print("HURRICANE EXPERIMENT (Paper Section 7.5)")
    print("Simulating Hurricane Dorian impact on Columbia, SC mobility\n")
    random.seed(42)

    profiles = generate_columbia_profiles(12)
    env = WeatherMobilitySpace(agent_profiles=profiles)
    agents = [
        PersonAgent(id=p["id"], profile={
            "name": p["name"],
            "personality": f"a {p['age']}-year-old {p['occupation']} in Columbia, SC",
        })
        for p in profiles
    ]
    society = AgentSociety(
        agents=agents, env_router=CodeGenRouter(env_modules=[env]), start_t=datetime.now(),
    )
    await society.init()

    daily_metrics = []

    for day_info in WEATHER_SCHEDULE:
        day = day_info["day"]
        env.set_weather(day_info["weather"], day_info["temp"], day_info["wind"], day_info["hurricane"])
        env.reset_daily_travel()

        print(f"Day {day}: {day_info['label']} - {day_info['weather']} (wind: {day_info['wind']}mph)")

        for p in profiles:
            weather_desc = (
                f"Weather: {day_info['weather']}, {day_info['temp']}F, wind {day_info['wind']}mph."
            )
            if day_info["hurricane"]:
                weather_desc += " HURRICANE WARNING in effect!"

            resp = await society.ask(
                f"You are {p['name']}, a {p['occupation']} in Columbia, SC. "
                f"Today is {day_info['label']}. {weather_desc} "
                f"Will you go out today or stay home? Reply YES to go out or NO to stay home."
            )
            will_travel = "yes" in resp.lower() and "no" not in resp.lower()[:10]
            env._is_traveling[p["id"]] = will_travel
            if will_travel:
                env._trip_count[p["id"]] += 1

        level = env.get_activity_level()
        daily_metrics.append({
            "day": day, "label": day_info["label"],
            "activity_level": round(level, 2),
            "hurricane": day_info["hurricane"],
        })
        bar = "#" * int(level * 40)
        print(f"  Activity: {level:.0%} |{bar}|")

    await society.close()

    # Save results
    out = Path("results/hurricane")
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "results.json", "w") as f:
        json.dump(daily_metrics, f, indent=2)

    # Summary
    before = [m["activity_level"] for m in daily_metrics if m["day"] <= 3]
    during = [m["activity_level"] for m in daily_metrics if 4 <= m["day"] <= 6]
    after = [m["activity_level"] for m in daily_metrics if m["day"] >= 7]

    print(f"\n{'Phase':<20}{'Avg Activity':<15}")
    print("-" * 35)
    print(f"{'Before (d1-3)':<20}{sum(before)/len(before):>8.0%}")
    print(f"{'During (d4-6)':<20}{sum(during)/len(during):>8.0%}")
    print(f"{'After  (d7-9)':<20}{sum(after)/len(after):>8.0%}")

    print(f"\nPaper: ~80% before, ~30% during, recovery after")
    print(f"Results saved to: {out / 'results.json'}")


if __name__ == "__main__":
    asyncio.run(main())
