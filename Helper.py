import os
from dotenv import load_dotenv
from google import genai
import re
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()


def get_summary_fromAI(text):
    prompt = f'''
    You are a summarizing assistant, when given information you will translate that information into common
    speak / commonly used words and summarize them. I want to to make sure that you keep all of the relevant
    information. DO NOT MAKE UP DATA OR LEAVE IMPORTANT INFORMATION OUT. DO NOT USE COMPLEX VOCABULARY.

    The goal of your summary should be to make things concise and simple enough that a regular person 
    would be able to query that information using a RAG.

    IMPORTANT: Some of the documents you see will be related to Tech Start UCalgary: A student org. If the documents are
    related to Tech Start then below is how you structure them:
    Here is how i want you to sturcture your response:
        Topic: (choose from the following: sponsorship, meeting, club history, executives, misc
        Guests: (if people or companies are mentioned by name put them here)
        Year: if given a year put the year 
        Notes: (here is where your summary should be)
        
    If the documents are school/academics related then here is how to structure them:
        Topic: (the subject, choose from the following: (CS, Geology, Sociology, Personal, Misc)
        Year: (if the notes mention the year then put it here)
        Notes: (Here put the summary, make sure you include all important things)

    here is the text:
    {text}
    '''
    client = genai.Client()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text


BLOCK_RE = re.compile(r"^\s*---\s*(.*?)\s*---\s*$", flags=re.MULTILINE)

def split_into_blocks(text: str):
    parts = BLOCK_RE.split(text)
    # parts = [preamble, title1, block1, title2, block2, ...]
    docs = []
    preamble = parts[0].strip()
    i = 1
    while i < len(parts):
        title = parts[i].strip()
        block = parts[i+1].strip()
        docs.append(Document(page_content=block, metadata={"title": title}))
        i += 2
    return docs, preamble

def rechunk_blocks(block_docs, chunk_size=1200, chunk_overlap=150):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],  # fallback cascade
    )
    return splitter.split_documents(block_docs)
