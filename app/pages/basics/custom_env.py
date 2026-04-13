"""02. Custom Environment Module — environment state + tool interaction."""

import asyncio
import streamlit as st
from app.config import require_api_key


def render():
    st.header("02. Custom Environment Module")
    st.caption("Branch: `examples-basics` | \ucee4\uc2a4\ud140 \ud658\uacbd \ubaa8\ub4c8 + @tool \ub370\ucf54\ub808\uc774\ud130")

    from agentsociety2_lite.env import EnvBase, tool, CodeGenRouter

    # Define the weather environment inline (same as original script)
    class WeatherEnvironment(EnvBase):
        def __init__(self):
            super().__init__()
            self._weather = "sunny"
            self._temperature = 25
            self._agent_locations = {}

        @tool(readonly=True, kind="observe")
        def get_weather(self, agent_id: int) -> str:
            """Get the current weather for an agent's location."""
            location = self._agent_locations.get(agent_id, "unknown location")
            return f"The weather in {location} is {self._weather} with {self._temperature}\u00b0C."

        @tool(readonly=False)
        def change_weather(self, weather: str, temperature: int) -> str:
            """Change the weather conditions."""
            self._weather = weather
            self._temperature = temperature
            return f"Weather changed to {weather} at {temperature}\u00b0C."

        @tool(readonly=False)
        def set_agent_location(self, agent_id: int, location: str) -> str:
            """Set an agent's location."""
            self._agent_locations[agent_id] = location
            return f"Agent {agent_id} is now in {location}."

        @tool(readonly=True, kind="statistics")
        def get_average_temperature(self) -> str:
            """Get the current average temperature."""
            return f"The current temperature is {self._temperature}\u00b0C."

    # Initialize environment in session state
    if "weather_env" not in st.session_state:
        st.session_state.weather_env = WeatherEnvironment()
        st.session_state.env_log = []

    env = st.session_state.weather_env

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Environment State")
        st.metric("Weather", env._weather)
        st.metric("Temperature", f"{env._temperature}\u00b0C")
        if env._agent_locations:
            st.json(env._agent_locations)
        else:
            st.caption("No agent locations set")

        st.markdown("---")
        st.subheader("Manual Controls")
        new_weather = st.selectbox("Weather", ["sunny", "rainy", "cloudy", "snowy", "stormy"])
        new_temp = st.number_input("Temperature (\u00b0C)", -30, 50, env._temperature)
        if st.button("Apply Change"):
            result = env.call_tool("change_weather", {"weather": new_weather, "temperature": new_temp})
            st.session_state.env_log.append(f"Manual: {result}")
            st.rerun()

        st.markdown("---")
        st.subheader("Registered Tools")
        for t in env.get_tools():
            ro = "R" if t["_readonly"] else "W"
            st.code(f"[{ro}] {t['name']}({', '.join(t['parameters']['properties'].keys())})")

    with col2:
        st.subheader("Action Log")
        for entry in st.session_state.env_log:
            st.text(entry)

        st.markdown("---")
        st.subheader("Natural Language Query")
        query = st.text_input("Ask or command the environment...")
        mode = st.radio("Mode", ["Ask (readonly)", "Intervene (write)"], horizontal=True)

        if st.button("Execute") and query and require_api_key():
            with st.spinner("Processing..."):
                from agentsociety2_lite import PersonAgent, AgentSociety
                from datetime import datetime

                agents = [PersonAgent(id=i, profile={"name": f"Agent{i}"}) for i in range(1, 3)]
                router = CodeGenRouter(env_modules=[env])
                society = AgentSociety(agents=agents, env_router=router, start_t=datetime.now())

                if mode.startswith("Ask"):
                    response = asyncio.run(_query(society, query, readonly=True))
                else:
                    response = asyncio.run(_query(society, query, readonly=False))

                st.session_state.env_log.append(f"{'Ask' if mode.startswith('Ask') else 'Intervene'}: {query}")
                st.session_state.env_log.append(f"  \u2192 {response[:200]}")
                st.success(response)

    if st.button("Reset Environment"):
        st.session_state.weather_env = WeatherEnvironment()
        st.session_state.env_log = []
        st.rerun()


async def _query(society, question, readonly):
    await society.init()
    if readonly:
        r = await society.ask(question)
    else:
        r = await society.intervene(question)
    await society.close()
    return r
