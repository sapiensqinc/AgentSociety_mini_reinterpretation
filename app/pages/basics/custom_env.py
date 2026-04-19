"""02. Custom Environment Module — environment state + tool interaction."""

import asyncio
import streamlit as st
from app.config import require_api_key
from app.security import ready_to_run, sanitize_user_input, show_safe_error
from agentsociety2_lite.env import EnvBase, tool, CodeGenRouter


# Defined at module scope (not inside render()) so that instances can be
# pickled by Streamlit's session-state serialization check. A class defined
# inside render() has __qualname__ = "render.<locals>.WeatherEnvironment",
# which pickle cannot resolve on deserialization — it throws
# UnserializableSessionStateError when the user navigates to another page.
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


def render():
    st.header("02. Custom Environment Module")
    st.caption("Source: paper §4 · code `agentsociety2/env/env_base.py` (`EnvBase` + `@tool`) · mini `agentsociety2_lite/env/`")

    st.info(
        "**Purpose.** `@tool` 데코레이터로 환경 도구를 정의하는 패턴 시연. "
        "`readonly=True` 도구는 **Ask**에서만, `readonly=False` 도구는 **Intervene**에서만 호출됩니다.\n\n"
        "**Expected result.** Ask 모드 질의 → `get_weather` 만 호출되고 환경 상태 그대로. "
        "Intervene 모드 명령 → `change_weather`/`set_agent_location`이 호출되어 State 패널에 반영."
    )

    with st.expander("이 예제에 대하여 — 상세", expanded=False):
        st.markdown("""
**논문 대응**: 논문 Section 4 "Real-world Societal Environment"에서 다루는 환경 모듈 설계를 시연합니다.
논문에서는 도시 공간(Urban Space, Section 4.2), 사회 공간(Social Space, Section 4.3),
경제 공간(Economic Space, Section 4.4)을 별도 시뮬레이터로 구현했지만,
v2 코드에서는 `EnvBase` 클래스를 상속하고 `@tool` 데코레이터로 메서드를 등록하는 패턴으로 단순화했습니다.

**원본 코드 위치**: `agentsociety2/env/env_base.py`의 `EnvBase` 클래스와 `@tool` 데코레이터가 핵심입니다.
원본에서는 `SimpleSocialSpace`, `EconomySpace`, `MobilitySpace` 등이 이 패턴으로 구현되어 있습니다.

**동작 원리**: `@tool(readonly=True)` 데코레이터가 붙은 메서드는 LLM이 호출 가능한 함수로 자동 등록됩니다.
메서드의 이름, docstring, 타입 힌트가 JSON Schema로 변환되어 Gemini의 Function Calling에 전달됩니다.
`readonly=True`인 도구는 `ask()`(조회)에서만, `readonly=False`인 도구는 `intervene()`(개입)에서 호출됩니다.
이 읽기/쓰기 분리는 실험 중 의도치 않은 환경 변경을 방지하기 위한 안전장치입니다.

**해결하는 문제**: 연구자가 자신만의 실험 환경을 빠르게 정의할 수 있게 합니다.
Python 클래스 하나로 날씨, 경제, 소셜 네트워크 등 어떤 환경이든 만들 수 있고,
LLM이 자연어 질의를 자동으로 적절한 도구 호출로 변환합니다.
        """)

    # Initialize environment in session state
    if "weather_env" not in st.session_state or not isinstance(
        st.session_state.get("weather_env"), WeatherEnvironment
    ):
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

        if st.button("Execute") and query and ready_to_run(tag="custom_env"):
            try:
                query = sanitize_user_input(query)
            except ValueError as e:
                st.error(str(e))
                return

            with st.spinner("Processing..."):
                from agentsociety2_lite import PersonAgent, AgentSociety
                from datetime import datetime

                agents = [PersonAgent(id=i, profile={"name": f"Agent{i}"}) for i in range(1, 3)]
                router = CodeGenRouter(env_modules=[env])
                society = AgentSociety(agents=agents, env_router=router, start_t=datetime.now())

                try:
                    if mode.startswith("Ask"):
                        response = asyncio.run(_query(society, query, readonly=True))
                    else:
                        response = asyncio.run(_query(society, query, readonly=False))
                except Exception as e:
                    show_safe_error(e, context="Failed to process request")
                    return

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
