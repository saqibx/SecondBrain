from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from tavily import TavilyClient
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from typing import Optional  # Add this line
import os

import os
import time
import TRAG as RAG
from TRAG import *
# Set your custom ChromaDB directory here
CHROMA_DIR = r"C:\Users\saqib\PycharmProjects\SecondBrain\chroma_db"  # Default path - change this to your actual path
DATA_DIR = r"C:\Users\saqib\PycharmProjects\SecondBrain\DATA"


embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")


# Initialize custom directories
RAG.set_directories(CHROMA_DIR, DATA_DIR)

load_dotenv()


@tool
def researcher(topic: str) -> str:
    """Research a topic using Tavily and summarize key points."""
    start_time = time.time()

    print(topic)
    if not topic.strip():
        return "ERROR: No research topic provided."

    try:
        client = TavilyClient(os.getenv("TAVILY_API_KEY"))
        search = client.search(query=topic)
        url_list = [item["url"] for item in search['results']][:3]
        print(url_list)
        extract = client.extract(urls=url_list)

        summarized = []
        for raw in extract['results']:
            text = raw.get("raw_content", "")
            url = raw.get("url", "")
            if not text:
                continue

            prompt = f"Summarize this article in 5 bullet points max. Skip ads. Content:\n{text}"
            print(f"\n== RESEARCHING: {url} ==")

            time.sleep(2.5)  # Avoid rate limits
            response = llm.invoke(prompt)
            summary = f"- {response.content.strip()}\n(Source: {url})"
            summarized.append(summary)

            duration = time.time() - start_time
            print(f"Time taken: {duration}")
        result = "\n\n".join(summarized) or "ERROR: No valid summaries generated."
        print(f"✅ Research completed for: {topic}")
        print(result)
        return result

    except Exception as e:
        return f"RESEARCHER ERROR: {e}"


@tool
def emailer(email_contents: str) -> str:
    """Draft a professional email using provided content."""
    if not email_contents.strip():
        return "ERROR: No content provided for email."

    prompt = f'''
    You are Saqib Mazhar, Co-VP External of Tech Start UCalgary, a student-led startup incubator.
    Based on the content below, write a professional but human-sounding email. Avoid buzzwords.

    Make sure to:
    - Include a clear subject line
    - Be concise and direct
    - Sound genuinely interested, not robotic
    - End with "Best regards, Saqib Mazhar"

    Content:
    {email_contents}
    '''

    try:

        response = llm.invoke(prompt)
        if not response.content.strip():
            return "ERROR: Empty response from model."

        result = response.content
        print("✅ Email draft completed")
        return result
    except Exception as e:
        return f"EMAILER ERROR: {e}"


@tool
def saver(filename: str, content: str) -> str:
    """Saves content to a file."""
    if not filename.endswith(".txt"):
        filename += ".txt"
    try:
        with open(filename, 'w') as f:
            f.write(content)
        print(f"✅ Saved to {filename}")
        return f"Document saved as {filename}"
    except Exception as e:
        return f"Failed to save: {e}"


@tool
def retriever(question: str) -> str:
    """Query the RAG system to get information from personal knowledge base."""
    if not question.strip():
        return "ERROR: No question provided for RAG query."

    try:
        # Use the new query_rag function instead of start()
        print("about to print")
        answer = RAG.query_rag(question)
        print("just printed")
        return answer
    except Exception as e:
        return f"RAG ERROR: {e}"

@tool
def embedder(docs: Optional[str] = None) -> str:
    """Embed documents. Splits input string by newlines. If none provided, uses default ones."""
    print("[*] Auto-embedding documents...")

    if not docs or not docs.strip():
        return "NO DOCS GIVEN"

    try:
        # Format the input into a tagging prompt for GPT
        doc_prompt = f'''
        You are a tagging assistant.
        
        For each chunk of the text below, summarize it in the following format:
        Topic: Researched Items, [then specify what the topic is]
        Notes: Copy the content word for word
        
        Separate each new entry with a newline.
        
        Text:
        {docs}
        '''


        response = llm.invoke([HumanMessage(content=doc_prompt)])
        clean_text = response.content if response.content else None

        if not clean_text:
            return "NO DOCS GIVEN"

        # Split the response into chunks
        doc_chunks = [chunk.strip() for chunk in clean_text.split("\n") if chunk.strip()]
        documents = [Document(page_content=chunk) for chunk in doc_chunks]

        # Check if vectorstore exists, if not create it
        if os.path.exists(CHROMA_DIR):
            # Load existing vectorstore and add documents
            vectorstore = Chroma(
                embedding_function=embedding_model,
                persist_directory=CHROMA_DIR,
            )
            vectorstore.add_documents(documents)
            print(f"[✓] Added {len(documents)} documents to existing vectorstore.")
        else:
            # Create new vectorstore
            vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=embedding_model,
                persist_directory=CHROMA_DIR,
            )
            print(f"[✓] Created new vectorstore with {len(documents)} documents.")

        total_count = vectorstore._collection.count()
        print(f"[✓] Total documents in vectorstore: {total_count}")
        return f"Embedding complete. Added {len(documents)} documents. Total: {total_count}"

    except Exception as e:
        print(f"[ERROR] Failed to embed: {e}")
        return f"EMBEDDING ERROR: {e}"
# if __name__ == "__main__":