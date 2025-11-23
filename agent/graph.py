from langgraph.graph import StateGraph, START, END

from agent.state import VLMState
from agent.nodes.video_to_text import analyze_video
from agent.nodes.send_notification import send_telegram_notification
from agent.edges.handle_video_description import classify_video


builder = StateGraph(VLMState)

builder.add_node("analyze_video", analyze_video)
builder.add_node("send_telegram_notification", send_telegram_notification)


builder.add_edge(START, "analyze_video")
builder.add_conditional_edges("analyze_video", classify_video)
builder.add_edge("send_telegram_notification", END)

graph = builder.compile()