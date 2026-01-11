from concurrent.futures.thread import ThreadPoolExecutor
from math import floor

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from tavily import TavilyClient
from langchain_core.documents import Document
from typing import Optional
import os
from flask import session
import time
import datetime


# Import your custom classes
from Classes.Users import User
from Classes.ChromaDBHandler import ChromaDBHandler

load_dotenv()

# Initialize the LLM
llm = ChatOpenAI(model="gpt-4o")


def get_user_chroma_handler():
    """
    Get the ChromaDBHandler for the current authenticated user.
    Returns None if no user is authenticated.
    """
    try:
        username = session.get("username")
        if not username:
            print("[DEBUG] No username in session for ChromaDB handler")
            return None

        # Verify user exists in database
        user = User.get_user(username=username)
        if not user:
            print(f"[DEBUG] User {username} not found in database")
            return None

        # Create and return ChromaDB handler for this user
        return ChromaDBHandler(username=username)
    except Exception as e:
        print(f"[DEBUG] Error getting ChromaDB handler: {e}")
        return None


def get_current_user():

    try:
        username = session.get("username")
        if not username:
            return None

        return User.get_user(username=username)
    except Exception as e:
        print(f"[DEBUG] Error getting current user: {e}")
        return None


@tool
def researcher(topic: str) -> str:
    """Research a topic using Tavily and summarize key points."""
    start_time = time.time()

    # print(f"[RESEARCHER] Starting research on: {topic}")

    if not topic.strip():
        return "ERROR: No research topic provided."

    # Check if user is authenticated
    current_user = get_current_user()
    if not current_user:
        return "ERROR: User not authenticated for research."

    try:
        client = TavilyClient(os.getenv("TAVILY_API_KEY"))
        if not client:
            return "ERROR: Tavily API key not configured."

        search = client.search(query=topic)

        if not search.get('results'):
            return f"ERROR: No search results found for topic: {topic}"

        url_list = [item["url"] for item in search['results']][:3]
        print(f"[RESEARCHER] Found URLs: {url_list}")

        extract = client.extract(urls=url_list)
        if not extract.get('results'):
            return "ERROR: Failed to extract content from URLs."

        def summarize(text,url):
            prompt = f"""
            Summarize this article in 5 bullet points max. 
            Focus on key facts and insights. Skip ads and irrelevant content.

            Content:
            {text}
            """
            return f"{llm.invoke(prompt).content.strip()} (Source: {url}"

        with ThreadPoolExecutor() as pool:
            summary = list(pool.map(lambda r: summarize(r["raw_content"], r['url']), extract['results']))

        duration = time.time() - start_time
        print(f"Searched In {floor(duration)} Seconds")

        if not summary:
            return "ERROR: No valid summaries generated from research."

        result = "".join(summary)
        return result

    except Exception as e:
        print(f"[RESEARCHER] ERROR: {e}")
        return f"RESEARCHER ERROR: {e}"


@tool
def emailer(email_contents: str) -> str:
    """Draft a professional email using provided content."""
    # print("[EMAILER] Starting email draft...")

    if not email_contents.strip():
        return "ERROR: No content provided for email."

    # Check if user is authenticated
    current_user = get_current_user()
    if not current_user:
        return "ERROR: User not authenticated for email drafting."

    # Get user's name for personalization (defaulting to username if no full name available)
    user_name = getattr(current_user, 'full_name', current_user.username)
    username = current_user.username

    prompt = f'''
    Based on the content below, write a professional but human-sounding email. Avoid buzzwords and corporate speak.

    Make sure to:
    - Include a clear, specific subject line
    - Be concise and direct
    - Sound genuinely interested and personable, not robotic
    - Use proper email formatting
    - End with "Best regards, {user_name}"

    Content to base the email on:
    {email_contents}
    '''

    try:
        response = llm.invoke(prompt)
        if not response.content or not response.content.strip():
            return "ERROR: Empty response from email model."

        result = response.content.strip()
        print("[EMAILER] ✅ Email draft completed")
        return result

    except Exception as e:
        print(f"[EMAILER] ERROR: {e}")
        return f"EMAILER ERROR: {e}"


@tool
def saver(filename: str, content: str) -> str:
    """Saves content to a file in the user's personal directory."""
    print(f"[SAVER] Attempting to save file: {filename}")

    if not filename or not content:
        return "ERROR: Filename and content are required."

    # Check if user is authenticated
    current_user = get_current_user()
    if not current_user:
        return "ERROR: User not authenticated for file saving."

    try:
        # Create user-specific directory
        user_dir = f"DATA/{current_user.username}"
        os.makedirs(user_dir, exist_ok=True)

        # Ensure filename has .txt extension
        if not filename.endswith(".txt"):
            filename += ".txt"

        # Create full file path
        filepath = os.path.join(user_dir, filename)

        # Save the file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"[SAVER] ✅ Saved to {filepath}")
        return f"Document saved as {filename} in your personal directory."

    except Exception as e:
        print(f"[SAVER] ERROR: {e}")
        return f"SAVER ERROR: Failed to save file - {e}"


@tool
def retriever(question: str) -> str:
    """Query the user's personal knowledge base using ChromaDB."""
    # print(f"[RETRIEVER] Querying knowledge base: {question}")

    if not question.strip():
        return "ERROR: No question provided for knowledge base query."

    # Get user's ChromaDB handler
    chroma_handler = get_user_chroma_handler()
    if not chroma_handler:
        return "ERROR: User not authenticated or ChromaDB handler unavailable."

    try:
        # Query the user's personal knowledge base
        results = chroma_handler.query(
            query_text=question,
            k=5,  # Get top 5 relevant documents
            include_metadata=True
        )

        if not results:
            return f"No relevant information found in your knowledge base for: {question}"

        # Format the results for the agent
        formatted_response = f"Found {len(results)} relevant documents in your knowledge base:\n\n"

        for i, doc in enumerate(results, 1):
            formatted_response += f"**Result {i}:**\n{doc['content']}\n\n"

            # Include metadata if available
            if 'metadata' in doc and doc['metadata']:
                formatted_response += f"*Metadata: {doc['metadata']}*\n\n"

        print(f"[RETRIEVER] ✅ Found {len(results)} relevant documents")
        return formatted_response.strip()

    except Exception as e:
        print(f"[RETRIEVER] ERROR: {e}")
        return f"RETRIEVER ERROR: Failed to query knowledge base - {e}"


@tool
def embedder(docs: Optional[str] = None) -> str:
    """Embed documents into the user's personal knowledge base."""
    # print("[EMBEDDER] Starting document embedding process...")

    if not docs or not docs.strip():
        return "ERROR: No documents provided for embedding."

    # Get user's ChromaDB handler
    chroma_handler = get_user_chroma_handler()
    current_user = get_current_user()

    if not chroma_handler or not current_user:
        return "ERROR: User not authenticated or ChromaDB handler unavailable."

    try:
        # Process the documents using ChromaDB handler's embed_documents method
        # print(f"[EMBEDDER] Processing documents for user: {current_user.username}")

        # The ChromaDBHandler will handle the summarization and embedding
        chroma_handler.embed_documents(
            input_text=docs,
            rebuild=False  # Add to existing collection, don't rebuild
        )

        # Get total count of documents in user's collection
        total_count = chroma_handler.db._collection.count()

        # print(f"[EMBEDDER] ✅ Documents embedded successfully")
        return f"Documents successfully embedded into your personal knowledge base. Total documents: {total_count}"

    except Exception as e:
        print(f"[EMBEDDER] ERROR: {e}")
        return f"EMBEDDER ERROR: Failed to embed documents - {e}"






# if __name__ == "__main__":
