"""Paper: Hurricane External Shock Experiment (Section 7.5)."""

import asyncio
import random
import streamlit as st
import plotly.graph_objects as go
from app.config import require_api_key
from app.security import ready_to_run, cap, show_safe_error, sanitize_llm_output
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
**논문 대응**: 논문 Section 7.5 "External Shocks of Hurricane"를 재현한 실험입니다.
논문에서는 2019년 허리케인 도리안이 사우스캐롤라이나주 콜럼비아 시의 주민 이동성에
미친 영향을 시뮬레이션하고, 실제 SafeGraph 모빌리티 데이터와 비교 검증했습니다.
이 실험은 논문 Section 3.3 "Mobility Behaviors"의 이동성 모델과 Section 4.2 "Urban Space"의 도시 환경을 활용합니다.

**논문 결과**: 상륙 전 활동량 70-90%, 상륙 중 약 30%로 급감, 상륙 후 정상 수준으로 회복되었습니다.
시뮬레이션된 일일 이동 횟수가 실제 SafeGraph 데이터 패턴과 높은 일치도를 보였습니다.

**동작 원리**: 9일간의 허리케인 도리안 날씨 스케줄(상륙 전 3일, 상륙 3일, 상륙 후 3일)을 설정합니다.
매일 각 에이전트에게 날씨 정보와 허리케인 경보를 알려주고 외출 여부를 결정하게 합니다.
에이전트의 직업(의료종사자, 학생, 은퇴자 등)과 나이에 따라 같은 악천후에도 다른 결정을 내립니다.
의료종사자는 허리케인 중에도 출근하는 경향이 있어 실제 essential worker 패턴과 유사합니다.

**해결하는 문제**: 자연재해 시 도시 이동성 변화를 예측하여 재난 대응 계획에 활용합니다.
대피 명령의 효과, 필수 인력의 이동 패턴, 회복 속도 등을 사전에 시뮬레이션할 수 있습니다.
실제 모빌리티 데이터와의 비교를 통해 LLM 에이전트 시뮬레이션의 현실 반영도를 검증합니다.
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

    with st.expander("이 예제에 대하여", expanded=False):
        st.markdown(DESCRIPTION)

    n_agents = cap("agents", st.number_input("Agents (Columbia SC residents)", 6, 20, 10))

    # Weather schedule display
    with st.expander("9-Day Weather Schedule"):
        st.dataframe([{
            "Day": w["day"], "Date": w["label"],
            "Weather": w["weather"],
            "Wind (mph)": w["wind"],
            "Hurricane": "YES" if w["hurricane"] else "",
        } for w in WEATHER_SCHEDULE])

    if st.button("Run Simulation") and ready_to_run(tag="hurricane"):
        with st.spinner(f"Simulating 9 days with {n_agents} agents..."):
            try:
                results = asyncio.run(_run_hurricane(n_agents))
            except Exception as e:
                show_safe_error(e, context="Failed to run simulation")
                return

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

        # Total Daily Trips (Paper Fig 23) — normalized 9-day time-series
        st.subheader("Total Daily Trips (Paper Fig 23)")
        daily_trips = [r["trips"] for r in results["daily"]]
        max_trips = max(daily_trips) if daily_trips else 1
        normalized = [t / max_trips for t in daily_trips] if max_trips > 0 else daily_trips

        trip_fig = go.Figure()
        trip_fig.add_trace(go.Scatter(
            x=days, y=normalized, mode="lines+markers",
            name="Simulated (normalized)",
            line=dict(color="#2E86AB", width=3),
            marker=dict(size=9),
        ))
        trip_fig.add_trace(go.Bar(
            x=days, y=[t / max_trips for t in daily_trips] if max_trips > 0 else daily_trips,
            name="Trips (raw, scaled)", marker_color="rgba(46, 134, 171, 0.25)",
            hovertemplate="%{x}<br>Trips: %{customdata}<extra></extra>",
            customdata=daily_trips,
        ))
        trip_fig.update_layout(
            yaxis=dict(title="Normalized Daily Trips (max=1.0)", range=[0, 1.1]),
            height=350, legend=dict(x=0.72, y=1),
        )
        st.plotly_chart(trip_fig, use_container_width=True)

        # Phase summary
        st.subheader("Phase Summary")
        before = [r["activity"] for r in results["daily"][:3]]
        during = [r["activity"] for r in results["daily"][3:6]]
        after = [r["activity"] for r in results["daily"][6:]]
        trips_b = sum(r["trips"] for r in results["daily"][:3])
        trips_d = sum(r["trips"] for r in results["daily"][3:6])
        trips_a = sum(r["trips"] for r in results["daily"][6:])

        col1, col2, col3 = st.columns(3)
        avg_b = sum(before) / len(before)
        avg_d = sum(during) / len(during)
        avg_a = sum(after) / len(after)

        col1.metric("Before (d1-3)", f"{avg_b:.0%}",
                    help=f"Paper: ~80%. Total trips: {trips_b}")
        col2.metric("During (d4-6)", f"{avg_d:.0%}",
                    delta=f"{avg_d - avg_b:.0%}", delta_color="inverse",
                    help=f"Paper: ~30%. Total trips: {trips_d}")
        col3.metric("After (d7-9)", f"{avg_a:.0%}",
                    delta=f"{avg_a - avg_d:.0%}",
                    help=f"Paper: recovery. Total trips: {trips_a}")

        st.caption(
            "Paper §7.5 reference: Activity Level ~80% before, ~30% during, recovery after. "
            "Total Daily Trips follows a similar U-shape (Fig 23)."
        )

        # Individual decisions for selected day
        st.markdown("---")
        day_select = st.selectbox("View Individual Decisions (Day)", range(1, 10), index=4)
        day_data = results["daily"][day_select - 1]
        for d in day_data["decisions"]:
            icon = "[OUT]" if d["go_out"] else "[HOME]"
            action = "GO OUT" if d["go_out"] else "STAY HOME"
            with st.expander(f"{icon} {d['name']} ({d['occupation']}): {action}"):
                st.write(sanitize_llm_output(d.get("reasoning", "")))


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
        daily_trips = sum(1 for going in env._is_traveling.values() if going)
        daily_results.append({
            "day": day_info["day"],
            "activity": activity,
            "trips": daily_trips,
            "decisions": decisions,
        })

    await society.close()
    return {"daily": daily_results}
