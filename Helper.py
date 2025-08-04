import os
from dotenv import load_dotenv
from google import genai
import re
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI

load_dotenv()


# def get_summary_fromAI(text):
#     prompt = f'''
#     You are a summarizing assistant, when given information you will translate that information into common
#     speak / commonly used words and summarize them. I want to to make sure that you keep all of the relevant
#     information. DO NOT MAKE UP DATA OR LEAVE IMPORTANT INFORMATION OUT. DO NOT USE COMPLEX VOCABULARY.
#
#     The goal of your summary should be to make things concise and simple enough that a regular person
#     would be able to query that information using a RAG.
#
#     IMPORTANT: Some of the documents you see will be related to Tech Start UCalgary: A student org. If the documents are
#     related to Tech Start then below is how you structure them:
#     Here is how i want you to sturcture your response:
#         Topic: (choose from the following: sponsorship, meeting, club history, executives, misc
#         Guests: (if people or companies are mentioned by name put them here)
#         Year: if given a year put the year
#         Notes: (here is where your summary should be)
#
#     If the documents are school/academics related then here is how to structure them:
#         Topic: (the subject, choose from the following:
#         Year: (if the notes mention the year then put it here)
#         Notes: (Here put the summary, make sure you include all important things)
#
#     here is the text:
#     {text}
#     '''
#     client = genai.Client()
#
#     response = client.models.generate_content(
#         model="gemini-2.5-flash",
#         contents=prompt
#     )
#
#     return response.text

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

    Topic: (choose one or more from: sponsorship, meeting, club history, executives, misc)
    Guests: (list the names of any companies or individuals mentioned)
    Year: (if a specific year is mentioned, include it here)
    Notes: (summarize the content clearly and completely)
    
    🎓 If the document is related to **school or academics**, use this format:

    Topic: (name of the subject, e.g., CPSC 355, history, philosophy)
    Year: (if mentioned, include it here)
    Notes: (summarize all important academic concepts, topics, or facts mentioned)
    
    If you're unsure which category it falls into, **take your best guess** based on the content. 

    ---
    
    
    If the document is related to general queries (Researched topics, Random items, etc) that doesn't fall into one the prior categories
    use this format
    
    Topic: Researched Items, and then whatever the topic is, include both
    Notes: Word for word whatever has been passed down to you.

    Here is the document text:
    {text}
    '''

    loc_model = ChatOpenAI(model="gpt-4o-mini")
    response = loc_model.invoke(prompt)
    return response.content

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
