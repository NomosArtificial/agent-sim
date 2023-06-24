import random
from typing import List, Optional

from langchain.callbacks.manager import tracing_v2_enabled

from agent_sim.player import Player


def simulation(
    agents: List[Player], seed_message: str, simulation_name: Optional[str] = None
):
    """
    Simulates a conversation between two agents.

    This is just a placeholder implementation to show the interface with the agents, please change.
    """
    if not simulation_name:
        simulation_name = "Simulation #" + str(random.randint(0, 99999))

    current_message = seed_message

    with tracing_v2_enabled(simulation_name):
        for agent in agents:
            current_message = agent.respond(seed_message)
            agent.add_to_memory(agent.role_name, current_message)

    return current_message
