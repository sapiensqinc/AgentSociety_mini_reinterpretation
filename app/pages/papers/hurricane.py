"""Paper: Hurricane External Shock Experiment (Section 7.5)."""

import asyncio
import random
import streamlit as st
import plotly.graph_objects as go
from app.config import require_api_key
from agentsociety2_lite.env import EnvBase, tool


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


def render():
    st.header("Hurricane Impact (Paper Sec 7.5)")
    st.caption("Branch: `paper-hurricane` | \ud5c8\ub9ac\ucf00\uc778 \ub3c4\ub9ac\uc548 \uc774\ub3d9\uc131 \ucda9\uaca9")

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
            icon = "\ud83d\udfe2" if d["go_out"] else "\ud83d\udd34"
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

    env = HurricaneEnv()
    agents = [PersonAgent(id=p["id"], profile={
        "name": p["name"],
        "personality": f"a {p['age']}-year-old {p['occupation']} in Columbia, SC",
    }) for p in profiles]

    router = CodeGenRouter(env_modules=[env])
    society = AgentSociety(agents=agents, env_router=router, start_t=datetime.now())
    await society.init()

    daily_results = []
    for day_info in WEATHER_SCHEDULE:
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
            decisions.append({
                "name": p["name"], "occupation": p["occupation"],
                "go_out": go_out, "reasoning": resp[:200],
            })

        activity = sum(1 for d in decisions if d["go_out"]) / len(decisions)
        daily_results.append({"day": day_info["day"], "activity": activity, "decisions": decisions})

    await society.close()
    return {"daily": daily_results}


class HurricaneEnv(EnvBase):
    def __init__(self):
        super().__init__()

    @tool(readonly=True, kind="observe")
    def get_weather_advisory(self) -> str:
        """Get current weather advisory status."""
        return "Check current weather conditions before going out."
