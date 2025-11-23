import datetime
import os.path
import zoneinfo

from langgraph.prebuilt import ToolNode
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta


# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]



def create_event(event_name, description, start_time):
    """
    Creates a Google Calendar event from information extracted from a voice transcript.

    When the LLM should call this tool:
    - Call this tool whenever the transcript mentions a person leaving, arriving,
      returning, meeting someone, or doing anything scheduled at a specific time.
    - Examples:
        - "I'll be back at 10."
        - "She arrives home at 18:30."
        - "I'm leaving at 7 AM."
        - "We will meet tomorrow at 9."

    When NOT to call this tool:
    - If no time is mentioned.
    - If the transcript is just casual conversation with no scheduled action.

    Required input fields the LLM must provide:
    - event_name: A short descriptive title for the event.
    - description: A short explanation of what is happening.
    - start_time: The start time in ISO format (YYYY-MM-DDTHH:MM).

    What the tool does:
    - Converts start_time into the Europe/Madrid timezone.
    - Sets the end time to 30 minutes after the start.
    - Creates a Google Calendar event in the user's primary calendar.

    Output:
    - The tool returns the Google Calendar event object, but the LLM does not
      need to process it.

    Summary for the LLM:
    - Extract event_name, description, and start_time from the transcript.
    - Only call this tool when a specific time and an action like leaving,
      arriving, or meeting is mentioned.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        # Call the Calendar API
        # now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()

        tz = zoneinfo.ZoneInfo("Europe/Madrid")

        start_dt = datetime.fromisoformat(start_time)
        start_dt = start_dt.replace(tzinfo=tz)
        end_dt = start_dt + timedelta(minutes=30)

        event = {
            'summary': event_name,
            'location': 'Home',
            'description': description,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': "Europe/Madrid",
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': "Europe/Madrid",
            }
            }

        event = service.events().insert(calendarId='primary', body=event).execute()
    except HttpError as error:
        print(f"An error occurred: {error}")


tools = [create_event]

create_google_calendar_event = ToolNode(tools)