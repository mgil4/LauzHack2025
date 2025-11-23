from langgraph.graph import StateGraph, START, END

from agents.door_monitor.state import VLMState
from agents.door_monitor.nodes.video_to_text import analyze_video
from agents.door_monitor.nodes.send_notification import send_telegram_notification
from agents.door_monitor.edges.handle_video_description import classify_video


builder = StateGraph(VLMState)

builder.add_node("analyze_video", analyze_video)
builder.add_node("send_telegram_notification", send_telegram_notification)


builder.add_edge(START, "analyze_video")
builder.add_conditional_edges("analyze_video", classify_video)
builder.add_edge("send_telegram_notification", END)

graph = builder.compile()