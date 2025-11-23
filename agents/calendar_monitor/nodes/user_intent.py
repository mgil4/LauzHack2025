from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()


from agents.calendar_monitor.nodes.create_event import tools
from agents.calendar_monitor.state import LLMState

llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools(tools, parallel_tool_calls=False)


from datetime import datetime

def detect_user_intent(state: LLMState):
    # Get the current date in ISO format
    today_str = datetime.now().strftime("%Y-%m-%d")

    sys_msg = f"""
    You are a smart assistant that can understand user voice transcripts and decide whether to create a Google Calendar event, respond directly or ignore.
    You have access to the following tool:

    Tool: create_event(event_name: str, description: str, start_time: str)
    - Purpose: Schedule a calendar event for a person leaving, arriving, returning, picking up, calling or meeting someone.
    - Inputs:
        - event_name: short descriptive title
        - description: short explanation
        - start_time: ISO 8601 format (YYYY-MM-DDTHH:MM)
    - Output: The Google Calendar event object (you do NOT need to process it)

    Instructions:
    1. ALWAYS extract from the transcript:
        - event_name
        - description
        - start_time
        if a scheduled action is mentioned.

    2. WHEN to call create_event:
        - Transcript mentions leaving, arriving, returning, meeting someone, or anything scheduled at a specific time.
        - Examples:
            - "I'll be back at 10."
            - "She arrives home at 18:30."
            - "I'm leaving at 7 AM."
            - "We will meet tomorrow at 9."

    3. WHEN a time is partially mentioned (e.g., "at 9" or "tomorrow morning"), REASON about the missing information:
        - If only a time is mentioned, assume today ({today_str}) if the time hasn’t passed yet; otherwise, schedule for tomorrow.
        - If a day is mentioned without a time, assume 09:00 by default.
        - Always return the start_time in ISO 8601 format.

    4. WHEN NOT to call create_event:
        - No event or time is mentioned.
        - Casual conversation without scheduled actions.

    5. Always be concise and clear.
    """

    return {
        "messages": [llm_with_tools.invoke([sys_msg] + [state["input"]])]
    }
