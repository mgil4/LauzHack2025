from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from agents.calendar_monitor.state import LLMState
from agents.calendar_monitor.nodes.audio_to_text import transcript_audio_to_text
from agents.calendar_monitor.nodes.user_intent import detect_user_intent
from agents.calendar_monitor.nodes.create_event import create_google_calendar_event


builder = StateGraph(LLMState)

builder.add_node("transcript_audio_to_text", transcript_audio_to_text)
builder.add_node("detect_user_intent", detect_user_intent)
builder.add_node("tools", create_google_calendar_event)

builder.add_edge(START, "transcript_audio_to_text")
builder.add_edge("transcript_audio_to_text", "detect_user_intent")
builder.add_conditional_edges(
    "detect_user_intent",
    tools_condition,
)
builder.add_edge("tools", END)

graph = builder.compile()

# print(graph.invoke({"video_path": "video/downtownabbey.mp4"}))
