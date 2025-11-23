from typing import TypedDict
from langgraph.graph.message import MessagesState

class LLMState(MessagesState):
    input: str
    # event_name: str
    # description: str
    # start_time: str