from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from tavily import TavilyClient
import os
import time
import TRAG as RAG

# Set your custom ChromaDB directory here
CUSTOM_CHROMA_DIR = r"C:\Users\saqib\PycharmProjects\SecondBrain\chroma_db"
CUSTOM_DATA_DIR = None  # Keep default DATA directory

# Initialize custom directories
RAG.set_directories(CUSTOM_CHROMA_DIR, CUSTOM_DATA_DIR)

load_dotenv()


@tool
def researcher(topic: str) -> str:
    """Research a topic using Tavily and summarize key points."""
    if not topic.strip():
        return "ERROR: No research topic provided."

    try:
        client = TavilyClient(os.getenv("TAVILY_API_KEY"))
        search = client.search(query=topic)
        url_list = [item["url"] for item in search['results']][:3]
        extract = client.extract(urls=url_list)

        summarized = []
        for raw in extract['results']:
            text = raw.get("raw_content", "")
            url = raw.get("url", "")
            if not text:
                continue

            prompt = f"Summarize this article in 5 bullet points max. Skip ads. Content:\n{text}"
            print(f"\n== RESEARCHING: {url} ==")

            time.sleep(2)  # Avoid rate limits
            local_model = ChatOpenAI(model="gpt-4o")
            response = local_model.invoke(prompt)
            summary = f"- {response.content.strip()}\n(Source: {url})"
            summarized.append(summary)

        result = "\n\n".join(summarized) or "ERROR: No valid summaries generated."
        print(f"✅ Research completed for: {topic}")
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
        local_model = ChatOpenAI(model="gpt-4o")
        response = local_model.invoke(prompt)
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


# if __name__ == "__main__":

