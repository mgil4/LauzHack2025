from typing import Literal
from langgraph.graph import END

from agent.state import VLMState


def classify_video(state: VLMState):
    if state['description'] != 'other':
        return 'send_telegram_notification'
    else:
        return END