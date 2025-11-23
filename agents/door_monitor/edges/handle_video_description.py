from typing import Literal
from langgraph.graph import END

from agents.door_monitor.state import VLMState


def classify_video(state: VLMState):
    person_detected = state.get('person', False)
    if person_detected:
        return "detect_family_members"
    else:
        return END