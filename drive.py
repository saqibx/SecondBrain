from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google import genai
from google.oauth2.credentials import Credentials
from docx import Document
import os
from dotenv import load_dotenv
load_dotenv()


SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")

#auth
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



#helper methods
def download_docx(service, file_id, filename):
    os.makedirs("downloads", exist_ok=True)
    filepath = os.path.join("downloads", filename)
    with open(filepath, "wb") as f:
        f.write(service.files().get_media(fileId=file_id).execute())
    return filepath

def extract_text_docx(filepath):
    doc = Document(filepath)
    return "\n".join([p.text for p in doc.paragraphs])


def get_summary_fromAI(text):
    prompt = f'''
    You are a summarizing assistant, when given information you will translate that information into common
    speak / commonly used words and summarize them. I want to to make sure that you keep all of the relevant
    information. DO NOT MAKE UP DATA OR LEAVE IMPORTANT INFORMATION OUT. DO NOT USE COMPLEX VOCABULARY.
    
    The goal of your summary should be to make things concise and simple enough that a regular person 
    would be able to query that information using a RAG.
    
    Here is how i want you to sturcture your response:
        Topic: (choose from the following: sponsorship, meeting, club history, executives, misc
        Guests: (if people or companies are mentioned by name put them here)
        Year: if given a year put the year 
        Notes: (here is where your summary should be)
    
    here is the text:
    {text}
    '''
    client = genai.Client()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text


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




#loop
results = drive_service.files().list(
    pageSize=1000,
    fields="files(id, name, mimeType)"
).execute()

files = results.get("files", [])
combined_text = ""

for file in files:
    file_id = file["id"]
    name = file["name"]
    mime = file["mimeType"]

    print(f"Processing: {name} ({mime})")
    try:
        if name.endswith(".docx"):
            path = download_docx(drive_service, file_id, name)
            text = extract_text_docx(path)

        elif mime == "application/vnd.google-apps.document":
            text = extract_text_from_gdoc(docs_service, file_id)

        else:
            print(f"Skipped unsupported file: {name}")
            continue

        xword = text.strip()
        phrase = get_summary_fromAI(xword)
        combined_text += f"\n--- {name} ---\n{phrase}\n"

    except Exception as e:
        print(f"Failed to process {name}: {e}")


with open("DATA/premetadata.txt", "w", encoding="utf-8") as f:
    f.write(combined_text)

print("Confirmed: premetadata.txt")