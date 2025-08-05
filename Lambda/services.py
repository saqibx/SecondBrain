import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from docx import Document
from dotenv import load_dotenv
from Helper import get_summary_fromAI
from langchain_openai import ChatOpenAI

import os
from datetime import datetime, timedelta

load_dotenv()


SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")

print("Client ID:", CLIENT_ID)
print("Client Secret:", CLIENT_SECRET)

# Authentication
client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:8090/"]
    }
}

flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
creds = flow.run_local_server(port=8090)

drive_service = build("drive", "v3", credentials=creds)
docs_service = build("docs", "v1", credentials=creds)

# --- Helper Functions ---

def get_summary_fromAI(text):
    prompt = f'''
    You are a summarizing assistant. When given a document, your job is to extract and translate the information into clear, simple language for use in a Retrieval-Augmented Generation (RAG) system. 

    Your output must be structured and useful for downstream querying. 

    Rules:
    - Do **not** invent facts or leave out important information.
    - Use **plain language** that’s easy for a non-technical person to understand.
    - Include all relevant details.
    - Follow the correct format based on document type.
    - **Metadata fields like Topic and Guests can include multiple comma-separated values.**

    ---

    📘 If the document is related to **Tech Start UCalgary** (a student startup incubator), use this format:

    Title: Name of Document
    Topic: (choose one or more from: sponsorship, meeting, club history, executives, misc)
    Guests: (list the names of any companies or individuals mentioned)
    Year: (if a specific year is mentioned, include it here)
    Notes: (summarize the content clearly and completely)

    🎓 If the document is related to **school or academics**, use this format:

    Title: Name of document
    Topic: (name of the subject, e.g., CPSC 355, history, philosophy)
    Year: (if mentioned, include it here)
    Notes: (summarize all important academic concepts, topics, or facts mentioned)

    If you're unsure which category it falls into, **take your best guess** based on the content. 

    ---


    If the document is related to general queries (Researched topics, Random items, etc) that doesn't fall into one the prior categories
    use this format

    Topic: Researched Items, and then whatever the topic is, include both
    Notes: Word for word whatever has been passed down to you.

    -----
    MAKE SURE ALL THE DATA IS IN JSON FORMAT. NO OTHER FORMAT
    Here is the document text:
    {text}
    '''

    loc_model = ChatOpenAI(model="gpt-4o-mini")
    response = loc_model.invoke(prompt)
    return response.content


def extract_text_from_gdoc(docs_service, file_id):
    try:
        doc = docs_service.documents().get(documentId=file_id).execute()
        text = ""
        for content in doc.get("body", {}).get("content", []):
            if "paragraph" in content:
                for elem in content["paragraph"].get("elements", []):
                    text += elem.get("textRun", {}).get("content", "")
        return text
    except HttpError as e:
        return f"[Error fetching Google Doc: {e}]"

# --- Main Script ---

# Get timestamp for 3 days ago
three_days_ago = datetime.utcnow() - timedelta(days=3)
three_days_ago_str = three_days_ago.isoformat("T") + "Z"  # RFC 3339 format

# Filter: only Google Docs modified in the last 3 days
query = f"""
    mimeType='application/vnd.google-apps.document'
    and modifiedTime > '{three_days_ago_str}'
"""

results = drive_service.files().list(
    q=query,
    pageSize=1000,
    fields="files(id, name, mimeType, modifiedTime)"
).execute()

files = results.get("files", [])
combined_text = ""

print(f"Found {len(files)} recent Google Docs...\n")

for file in files:
    file_id = file["id"]
    name = file["name"]
    mime = file["mimeType"]
    mod_time = file.get("modifiedTime")

    # print(f"Processing: {name} — Last Modified: {mod_time}")

    try:
        text = extract_text_from_gdoc(docs_service, file_id)
        summary = get_summary_fromAI(text.strip())




    except Exception as e:
        print(f"Failed to process {name}: {e}")

def send_to_endpoint(data: str, endpoint_url: str):
    try:
        response = requests.post(
            endpoint_url,
            json={"content": data}
        )
        if response.status_code == 200:
            print("✅ Successfully sent data to endpoint.")
        else:
            print(f"❌ Failed to send data. Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"🔥 Error sending data to endpoint: {e}")



send_to_endpoint(summary,"")