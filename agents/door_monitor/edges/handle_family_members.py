from typing import Literal
from langgraph.graph import END

from agents.door_monitor.state import VLMState


def classify_person(state: VLMState):
    if state['family'] is True:
        return 'send_telegram_notification'
    else:
        return 'detect_mailman_or_suspicious'