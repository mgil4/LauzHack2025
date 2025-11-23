from typing import TypedDict
from langgraph.graph.message import MessagesState

class LLMState(MessagesState):
    video_path: str
    transcript: str
    # event_name: str
    # description: str
    # start_time: str