"""Paper: Hurricane External Shock Experiment (Section 7.5)."""

import asyncio
import random
import streamlit as st
import plotly.graph_objects as go
from app.config import require_api_key
from agentsociety2_lite.env import EnvBase, tool
from typing import Dict, List


WEATHER_SCHEDULE = [
    {"day": 1, "label": "Aug 28 (Before)", "weather": "partly cloudy", "temp": 88, "wind": 12, "hurricane": False},
    {"day": 2, "label": "Aug 29 (Before)", "weather": "cloudy", "temp": 84, "wind": 18, "hurricane": False},
    {"day": 3, "label": "Aug 30 (Before)", "weather": "overcast with rain", "temp": 78, "wind": 30, "hurricane": False},
    {"day": 4, "label": "Aug 31 (Landfall)", "weather": "severe storm", "temp": 72, "wind": 75, "hurricane": True},
    {"day": 5, "label": "Sep 1 (Landfall)", "weather": "hurricane conditions", "temp": 70, "wind": 95, "hurricane": True},
    {"day": 6, "label": "Sep 2 (Landfall)", "weather": "tropical storm", "temp": 74, "wind": 55, "hurricane": True},
    {"day": 7, "label": "Sep 3 (After)", "weather": "rain clearing", "temp": 80, "wind": 25, "hurricane": False},
    {"day": 8, "label": "Sep 4 (After)", "weather": "partly cloudy", "temp": 84, "wind": 15, "hurricane": False},
    {"day": 9, "label": "Sep 5 (After)", "weather": "clear skies", "temp": 87, "wind": 10, "hurricane": False},
]


DESCRIPTION = """
**Paper Section**: Section 7.5 "External Shocks of Hurricane"

**Description**: This experiment reproduces the Hurricane Dorian mobility impact study from the paper.
It simulates how agents adjust mobility behavior in response to weather events,
comparing results against real SafeGraph mobility data patterns.
The simulation uses a `WeatherMobilitySpace` environment with 3 tools:
`get_weather(agent_id)`, `decide_travel(agent_id, will_travel, destination)`,
and `get_activity_statistics()`.

**Paper Findings**: Activity level drops from 70-90% to ~30% during hurricane landfall,
with recovery to normal levels after the hurricane passes.
Simulated daily trips align with real SafeGraph data patterns.

**How It Works**: A 9-day Hurricane Dorian weather schedule is configured
(3 days before landfall, 3 days during, 3 days after).
Each day, agents receive weather information and hurricane warnings,
then decide whether to go out or stay home.
Agent occupation (healthcare worker, student, retiree, etc.) and age
influence decisions -- healthcare workers tend to go out even during
hurricanes, matching real essential-worker patterns.

**Problem Solved**: Predicting urban mobility changes during natural disasters
for disaster response planning. Evacuation order effectiveness, essential
worker movement patterns, and recovery speed can all be simulated in advance.
Comparison with real mobility data validates the realism of LLM agent simulation.
"""


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
        name = self._names.get(agent_id, f"Agent_{agent_id}")
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
        """Update current weather conditions."""
        self._weather = weather
        self._temperature = temp
        self._wind_speed = wind
        self._hurricane_active = hurricane

    def reset_daily_travel(self):
        """Reset all agents' travel status for a new day."""
        for aid in self._is_traveling:
            self._is_traveling[aid] = False

    def get_activity_level(self) -> float:
        """Calculate fraction of agents currently traveling."""
        total = len(self._names)
        active = sum(1 for v in self._is_traveling.values() if v)
        return active / total if total else 0


def render():
    st.header("Hurricane Impact (Paper Sec 7.5)")
    st.caption("Branch: `paper-hurricane`")

    with st.expander("About this experiment", expanded=False):
        st.markdown(DESCRIPTION)

    n_agents = st.number_input("Agents (Columbia SC residents)", 6, 20, 10)

    # Weather schedule display
    with st.expander("9-Day Weather Schedule"):
        st.dataframe([{
            "Day": w["day"], "Date": w["label"],
            "Weather": w["weather"],
            "Wind (mph)": w["wind"],
            "Hurricane": "YES" if w["hurricane"] else "",
        } for w in WEATHER_SCHEDULE])

    if st.button("Run Simulation") and require_api_key():
        with st.spinner(f"Simulating 9 days with {n_agents} agents..."):
            results = asyncio.run(_run_hurricane(n_agents))

        # Activity bar chart
        st.subheader("Activity Level Over 9 Days")
        days = [w["label"].split(" ")[0] + " " + w["label"].split(" ")[1] for w in WEATHER_SCHEDULE]
        levels = [r["activity"] for r in results["daily"]]

        colors = []
        for w in WEATHER_SCHEDULE:
            if w["hurricane"]:
                colors.append("#e74c3c")
            elif w["day"] <= 3:
                colors.append("#3498db")
            else:
                colors.append("#2ecc71")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=days, y=levels,
            marker_color=colors,
            text=[f"{l:.0%}" for l in levels],
            textposition="auto",
        ))

        # Wind speed overlay
        fig.add_trace(go.Scatter(
            x=days, y=[w["wind"] / 100 for w in WEATHER_SCHEDULE],
            name="Wind Speed (scaled)",
            mode="lines+markers",
            line=dict(color="#f39c12", width=2),
            yaxis="y2",
        ))

        fig.update_layout(
            yaxis=dict(title="Activity Level", range=[0, 1.1]),
            yaxis2=dict(title="Wind (mph)", overlaying="y", side="right",
                       range=[0, 1.1]),
            height=400,
            legend=dict(x=0.7, y=1),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Phase summary
        st.subheader("Phase Summary")
        before = [r["activity"] for r in results["daily"][:3]]
        during = [r["activity"] for r in results["daily"][3:6]]
        after = [r["activity"] for r in results["daily"][6:]]

        col1, col2, col3 = st.columns(3)
        avg_b = sum(before) / len(before)
        avg_d = sum(during) / len(during)
        avg_a = sum(after) / len(after)

        col1.metric("Before (d1-3)", f"{avg_b:.0%}", help="Paper: ~80%")
        col2.metric("During (d4-6)", f"{avg_d:.0%}",
                     delta=f"{avg_d - avg_b:.0%}", delta_color="inverse",
                     help="Paper: ~30%")
        col3.metric("After (d7-9)", f"{avg_a:.0%}",
                     delta=f"{avg_a - avg_d:.0%}", help="Paper: recovery")

        st.caption("Paper reference: ~80% before, ~30% during, recovery after")

        # Individual decisions for selected day
        st.markdown("---")
        day_select = st.selectbox("View Individual Decisions (Day)", range(1, 10), index=4)
        day_data = results["daily"][day_select - 1]
        for d in day_data["decisions"]:
            icon = "[OUT]" if d["go_out"] else "[HOME]"
            action = "GO OUT" if d["go_out"] else "STAY HOME"
            with st.expander(f"{icon} {d['name']} ({d['occupation']}): {action}"):
                st.write(d.get("reasoning", ""))


async def _run_hurricane(n_agents):
    from agentsociety2_lite import PersonAgent, CodeGenRouter, AgentSociety
    from datetime import datetime

    random.seed(42)
    occupations = ["office worker", "teacher", "retail worker", "healthcare worker", "student", "retiree"]
    profiles = [{
        "id": i + 1,
        "name": f"Resident_{i+1}",
        "occupation": random.choice(occupations),
        "age": random.randint(22, 70),
    } for i in range(n_agents)]

    env = WeatherMobilitySpace(agent_profiles=profiles)
    agents = [PersonAgent(id=p["id"], profile={
        "name": p["name"],
        "personality": f"a {p['age']}-year-old {p['occupation']} in Columbia, SC",
    }) for p in profiles]

    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=agents, env_router=router, start_t=datetime.now())
    await society.init()

    daily_results = []
    for day_info in WEATHER_SCHEDULE:
        env.set_weather(day_info["weather"], day_info["temp"], day_info["wind"], day_info["hurricane"])
        env.reset_daily_travel()

        decisions = []
        for p in profiles:
            weather_desc = f"Weather: {day_info['weather']}, {day_info['temp']}F, wind {day_info['wind']}mph."
            if day_info["hurricane"]:
                weather_desc += " HURRICANE WARNING!"

            resp = await society.ask(
                f"You are {p['name']}, a {p['occupation']} in Columbia, SC. "
                f"Today is {day_info['label']}. {weather_desc} "
                f"Will you go out today? Reply YES or NO and briefly explain."
            )
            go_out = "yes" in resp.lower() and "no" not in resp.lower()[:10]

            # Update environment state to match original script behavior
            env._is_traveling[p["id"]] = go_out
            if go_out:
                env._trip_count[p["id"]] += 1

            decisions.append({
                "name": p["name"], "occupation": p["occupation"],
                "go_out": go_out, "reasoning": resp[:200],
            })

        activity = env.get_activity_level()
        daily_results.append({"day": day_info["day"], "activity": activity, "decisions": decisions})

    await society.close()
    return {"daily": daily_results}
