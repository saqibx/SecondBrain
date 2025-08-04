from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv


load_dotenv()

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Replace these with your actual OAuth 2.0 credentials
CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")

print(CLIENT_SECRET)
print(CLIENT_ID)

# Required scope for Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Manual client config using ID/Secret
flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uris": ["http://localhost:8090/"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    },
    SCOPES
)

creds = flow.run_local_server(port=8090)

# Now create the calendar API service
service = build('calendar', 'v3', credentials=creds)

# Example: list next 5 events
results = service.events().list(
    calendarId='primary',

    singleEvents=True,
    orderBy='startTime'
).execute()

events = results.get('items', [])
if not events:
    print("No upcoming events found.")
# for event in events:
#     start = event['start'].get('dateTime', event['start'].get('date'))
#     print(start, event['summary'])

for event in events:
    start = event['start'].get('dateTime', event['start'].get('date'))
    end = event['end'].get('dateTime', event['end'].get('date'))
    summary = event.get('summary', 'No Title')
    location = event.get('location', 'No Location')
    description = event.get('description', 'No Description')

    print(f"Summary    : {summary}")
    print(f"Start Time : {start}")
    print(f"End Time   : {end}")
    print(f"Location   : {location}")
    print(f"Description: {description}")
    print("-" * 50)

