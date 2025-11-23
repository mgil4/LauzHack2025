from typing import Literal
from langgraph.graph import END

from agents.door_monitor.state import VLMState


def classify_video(state: VLMState):
    if state['person'] is True:
        return "detect_family_members"
    else:
        return END