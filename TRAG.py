import json
import os
import glob
from pathlib import Path
from typing import Optional

from google import genai
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv
import re
from langchain_core.documents import Document
from langchain_core.tools import tool

load_dotenv()

# ---- SETUP ----

embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
llm = ChatOpenAI(model="gpt-4", temperature=0)

CHROMA_DIR = "./chroma_db"  # Default path - change this to your actual path
DATA_DIR = "./DATA"


# Configuration function to set custom directories
def set_directories(chroma_dir=None, data_dir=None):
    """Set custom directories for ChromaDB and data files"""
    global CHROMA_DIR, DATA_DIR
    if chroma_dir:
        CHROMA_DIR = chroma_dir
    if data_dir:
        DATA_DIR = data_dir
    print(f"[*] ChromaDB directory: {CHROMA_DIR}")
    print(f"[*] Data directory: {DATA_DIR}")


# Global RAG chain to avoid reloading
_rag_chain = None


# ---- STEP 1: LOAD + EMBED ----

def parse_blocks(raw_text):
    """Parse structured blocks from text file"""
    blocks = raw_text.strip().split('---')
    documents = []

    for block in blocks:
        if not block.strip():
            continue

        # Extract title
        title_match = re.match(r'\s*(.*?)\s*[\r\n]+', block)
        doc_title = title_match.group(1).strip() if title_match else "Untitled"

        # Extract fields
        topic_match = re.search(r'Topic:\s*(.*)', block)
        guests_match = re.search(r'Guests:\s*(.*)', block)
        year_match = re.search(r'Year:\s*(.*)', block)
        notes_match = re.search(r'Notes:\s*(.*)', block, re.DOTALL)

        topic = topic_match.group(1).strip() if topic_match else "misc"
        guests_raw = guests_match.group(1).strip() if guests_match else ""
        guests = [g.strip() for g in guests_raw.split(',')] if guests_raw else []
        year = year_match.group(1).strip() if year_match else "Unknown"
        notes = notes_match.group(1).strip() if notes_match else ""

        # Create Document object
        doc = Document(
            page_content=notes,
            metadata={
                "title": doc_title,
                "topic": topic,
                "guests": ", ".join(guests),
                "year": year
            }
        )
        documents.append(doc)

    return documents


def load_all_documents():
    """Load all text files from DATA directory"""
    print(f"[*] Looking for files in {DATA_DIR}...")

    # Create DATA directory if it doesn't exist
    os.makedirs(DATA_DIR, exist_ok=True)

    # Find all text files in DATA directory
    text_files = glob.glob(os.path.join(DATA_DIR, "*.txt"))

    if not text_files:
        print(f"[!] No .txt files found in {DATA_DIR}")
        return []

    print(f"[*] Found {len(text_files)} text files:")
    for file in text_files:
        print(f"    - {os.path.basename(file)}")

    all_documents = []

    for file_path in text_files:
        try:
            print(f"[*] Processing {os.path.basename(file_path)}...")
            loader = TextLoader(file_path, encoding="utf-8")
            raw_docs = loader.load()

            # Add source file to metadata
            for doc in raw_docs:
                doc.metadata["source_file"] = os.path.basename(file_path)

            # Check if file has structured blocks (contains '---')
            full_text = "\n".join([doc.page_content for doc in raw_docs])
            if '---' in full_text:
                # Parse structured blocks
                parsed_docs = parse_blocks(full_text)
                for doc in parsed_docs:
                    doc.metadata["source_file"] = os.path.basename(file_path)
                all_documents.extend(parsed_docs)
            else:
                # Treat as regular document and chunk it
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=3000,
                    chunk_overlap=700
                )
                chunks = splitter.split_documents(raw_docs)
                all_documents.extend(chunks)

        except Exception as e:
            print(f"[!] Error processing {file_path}: {e}")
            continue

    return all_documents


def embed_documents():
    """Load and embed all documents from DATA directory"""
    print("[*] Loading and processing documents...")

    # Load all documents
    all_docs = load_all_documents()

    if not all_docs:
        print("[!] No documents to embed.")
        return

    print(f"[*] Total documents/chunks to embed: {len(all_docs)}")

    # Check if vectorstore already exists
    if os.path.exists(CHROMA_DIR):
        print(f"[*] Existing vector database found at {CHROMA_DIR}")
        choice = input("Do you want to (1) clear and rebuild or (2) add to existing? Enter 1 or 2: ")

        if choice == "1":
            # Clear existing database
            import shutil
            shutil.rmtree(CHROMA_DIR)
            print("[*] Cleared existing database.")
        elif choice == "2":
            # Load existing vectorstore
            vectorstore = Chroma(
                embedding_function=embedding_model,
                persist_directory=CHROMA_DIR,
            )
            print("[*] Adding to existing database...")
            vectorstore.add_documents(all_docs)
            print("[✓] Documents added to existing database.")
            return
        else:
            print("Invalid choice. Exiting.")
            return

    # Create new vectorstore
    print("[*] Creating new vector database...")
    vectorstore = Chroma.from_documents(
        documents=all_docs,
        embedding=embedding_model,
        persist_directory=CHROMA_DIR,
    )

    print("[✓] Embedding complete and saved to disk.")
    print(f"[✓] Vector database contains {vectorstore._collection.count()} documents.")

@tool
def embedder(docs: Optional[str] = None) -> str:
    """Embed documents. Splits input string by newlines. If none provided, uses default ones."""
    print("[*] Auto-embedding documents...")

    if docs:
        doc_chunks = [chunk.strip() for chunk in docs.split("\n") if chunk.strip()]
    else:
        return "NO DOCS GIVEN"

    # Convert each chunk into a Document
    documents = [Document(page_content=chunk) for chunk in doc_chunks]

    # Embed the documents (append to existing DB)
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embedding_model,
        persist_directory=CHROMA_DIR,
        collection_name="default",  # set if you're managing multiple
    )

    print(f"[✓] Embedded {vectorstore._collection.count()} documents.")
    return "Embedding complete."


def check_vectorstore():
    """Check if vectorstore exists and has content"""
    if not os.path.exists(CHROMA_DIR):
        return False

    try:
        vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embedding_model
        )
        count = vectorstore._collection.count()
        return count > 0
    except Exception as e:
        print(f"[!] Error loading vector database: {e}")
        return False


# ---- STEP 2: RAG PIPELINE ----

def setup_rag_chain():
    """Setup RAG chain with improved context handling"""
    global _rag_chain

    if _rag_chain is not None:
        return _rag_chain

    # if not check_vectorstore():
    #     print("[*] No vector database found. Auto-embedding documents...")
    #     if not embed_documents_silent():
    #         print("[!] Failed to embed documents.")
    #         return None

    vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embedding_model
    )

    retriever = vectorstore.as_retriever(
        search_kwargs={"k": 6}
    )

    prompt = ChatPromptTemplate.from_template("""
You are an AI assistant answering questions based on the provided context.

Use the following context to answer the question. If the answer is not clearly available in the context, say "I don't have enough information to answer that question based on the available documents."

Context:
{context}

Question: {question}

Answer:""")

    def format_docs(docs):
        """Format retrieved documents with metadata"""
        formatted = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get('source_file', 'Unknown')
            title = doc.metadata.get('title', '')
            content = doc.page_content
            formatted.append(f"Document {i} (Source: {source}):\n{title}\n{content}")
        return "\n\n---\n\n".join(formatted)

    _rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
    )

    return _rag_chain


# ---- AGENT INTERFACE FUNCTIONS ----

def query_rag(question: str) -> str:
    """
    Main function for agents to query the RAG system.
    Returns the answer as a string.
    """
    if not question.strip():
        return "ERROR: No question provided."

    try:
        rag_chain = setup_rag_chain()
        if not rag_chain:
            return "ERROR: Could not initialize RAG system. Check if documents exist in DATA directory."

        response = rag_chain.invoke(question)
        return response.content

    except Exception as e:
        return f"RAG ERROR: {e}"


def get_rag_status() -> dict:
    """Get status of RAG system"""
    try:
        has_db = check_vectorstore()
        doc_count = 0

        if has_db:
            vectorstore = Chroma(
                persist_directory=CHROMA_DIR,
                embedding_function=embedding_model
            )
            doc_count = vectorstore._collection.count()

        return {
            "has_database": has_db,
            "document_count": doc_count,
            "data_directory": DATA_DIR,
            "database_directory": CHROMA_DIR
        }
    except Exception as e:
        return {"error": str(e)}


def run_llm(text):
    """Categorize query using Gemini"""
    prompt = f'''
    Your job is to determine what category this text may be related to. Here are the possible options:
    Possible Categories: Sponsorship, meeting, executives, Misc, Club History

    No other possible categories. If the text asks about money assume its related to sponsorship,
    if the text asks about anything related to meetings assume its about meeting. If anything else assume its misc.

    DO NOT ADD ANYTHING TO YOUR RESPONSE BUT THE CATEGORY. NO GREETING NO NOTHING. JUST THE ANSWER.

    {text}
    '''

    try:
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"[!] Error with categorization: {e}")
        return "Misc"


# ---- CLI Interface (kept for manual testing) ----

def run_chat():
    """Interactive chat interface"""
    print("[*] Loading RAG system...")

    rag_chain = setup_rag_chain()
    if not rag_chain:
        return

    print("[✓] Ready to answer questions. Type 'exit' to quit.\n")

    while True:
        question = input("Ask a question: ")

        if question.lower() in ["exit", "quit"]:
            break

        if not question.strip():
            continue

        try:
            # Get response from RAG
            answer = query_rag(question)
            print(f"\n🧠 Answer:\n{answer}\n")

        except Exception as e:
            print(f"[!] Error: {e}\n")


def test_retrieval():
    """Test retrieval without LLM to debug issues"""
    if not check_vectorstore():
        print("[!] No vector database found.")
        return

    vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embedding_model
    )

    test_query = input("Enter a test query: ")
    docs = vectorstore.similarity_search(test_query, k=3)

    print(f"\n[*] Retrieved {len(docs)} documents:")
    for i, doc in enumerate(docs, 1):
        print(f"\nDocument {i}:")
        print(f"Source: {doc.metadata.get('source_file', 'Unknown')}")
        print(f"Content: {doc.page_content[:200]}...")
        print(f"Metadata: {doc.metadata}")


def start():
    """Main entry point for CLI"""
    print("RAG CLI System")
    print("-" * 50)

    # Allow user to set custom directories
    custom_setup = input("Do you want to use custom directories? (y/n): ").lower()
    if custom_setup == 'y':
        chroma_path = input(f"Enter ChromaDB directory path (current: {CHROMA_DIR}): ").strip()
        data_path = input(f"Enter data directory path (current: {DATA_DIR}): ").strip()

        if chroma_path:
            set_directories(chroma_dir=chroma_path)
        if data_path:
            set_directories(data_dir=data_path)

    while True:
        print("\nOptions:")
        print("1. Embed documents")
        print("2. Ask questions (chat)")
        print("3. Test retrieval")
        print("4. Check database status")
        print("5. Change directories")
        print("6. Exit")

        choice = input("\nEnter your choice (1-6): ")

        if choice == "1":
            embed_documents()
        elif choice == "2":
            run_chat()
        elif choice == "3":
            test_retrieval()
        elif choice == "4":
            status = get_rag_status()
            print(f"Database exists: {status.get('has_database', False)}")
            print(f"Document count: {status.get('document_count', 0)}")
            print(f"Data directory: {status.get('data_directory', 'Unknown')}")
            print(f"ChromaDB directory: {status.get('database_directory', 'Unknown')}")
        elif choice == "5":
            chroma_path = input(f"Enter new ChromaDB directory path (current: {CHROMA_DIR}): ").strip()
            data_path = input(f"Enter new data directory path (current: {DATA_DIR}): ").strip()
            set_directories(chroma_path if chroma_path else None, data_path if data_path else None)
        elif choice == "6":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1-6.")


if __name__ == "__main__":
    start()