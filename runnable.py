import os
import re
import json
from typing import Optional

from google import genai
from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
# If you upgrade: pip install -U langchain-chroma  and switch this import:
# from langchain_chroma import Chroma
from langchain_community.vectorstores import Chroma

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document

from langchain_text_splitters import RecursiveCharacterTextSplitter

# ✅ Use your helpers
from Helper import (
    split_into_blocks,      # returns (docs, preamble)
    rechunk_blocks,         # size-bounded re-chunk
    get_summary_fromAI      # (not used here, but available)
)

load_dotenv()

# ---- CONFIG ----
CHROMA_DIR = "./chroma_db"
DATA_FILE = "DATA/nottest.txt"

embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
llm = ChatOpenAI(model="gpt-4", temperature=0)

# Topic normalization — includes both your TechStart topics and your Academic topics
ALLOWED_TOPICS = {
    # TechStart
    "sponsorship": "sponsorship",
    "meeting": "meeting",
    "executives": "executives",
    "club history": "club_history",
    "club_history": "club_history",
    "misc": "misc",
    # Academic
    "cs": "cs",
    "geology": "geology",
    "sociology": "sociology",
    "personal": "personal",
}

def normalize_topic(s: Optional[str]) -> str:
    if not s:
        return "misc"
    key = s.strip().lower().replace("-", " ").replace("_", " ")
    return ALLOWED_TOPICS.get(key, "misc")

def norm_newlines(s: str) -> str:
    return s.replace("\r\n", "\n").replace("\r", "\n")

# ---- Block parser that extracts Topic/Guests/Year/Notes from each block ----
TOPIC_RE  = re.compile(r"^Topic:\s*(.*)$", flags=re.MULTILINE)
GUESTS_RE = re.compile(r"^Guests:\s*(.*)$", flags=re.MULTILINE)
YEAR_RE   = re.compile(r"^Year:\s*(.*)$", flags=re.MULTILINE)
NOTES_RE  = re.compile(r"^Notes:\s*(.*)$", flags=re.DOTALL | re.MULTILINE)

def extract_fields_from_block(block_doc: Document) -> Document:
    """
    Input: Document(page_content=raw block text that contains Topic/Guests/Year/Notes, metadata.title)
    Output: Document(page_content=Notes only, metadata with normalized fields)
    """
    block = norm_newlines(block_doc.page_content).strip()
    title = block_doc.metadata.get("title", "Untitled")

    topic_raw = (TOPIC_RE.search(block).group(1).strip() if TOPIC_RE.search(block) else "misc")
    topic = normalize_topic(topic_raw)

    guests_csv = (GUESTS_RE.search(block).group(1).strip() if GUESTS_RE.search(block) else "")
    year = (YEAR_RE.search(block).group(1).strip() if YEAR_RE.search(block) else "") or "Unknown"

    notes_match = NOTES_RE.search(block)
    notes = notes_match.group(1).strip() if notes_match else block

    return Document(
        page_content=notes,
        metadata={
            "title": title,
            "topic": topic,
            "guests": guests_csv,   # keep as CSV string for Chroma
            "year": year,
        }
    )

# ---- EMBED ----
def embed_documents():
    print("[*] Loading text and splitting by '--- Title ---' ...")
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(f"{DATA_FILE} not found. Make sure your summaries are saved there.")

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        full_text = f.read()

    # 1) Use your helper to split on delimiters
    block_docs, _ = split_into_blocks(full_text)
    if not block_docs:
        raise RuntimeError("No blocks found. Ensure your file uses lines like `--- Some Title ---`.")

    # 2) Extract Topic/Guests/Year/Notes per block
    doc_per_block = [extract_fields_from_block(d) for d in block_docs]

    # 3) Re-chunk Notes into size-bounded pieces (carry metadata)
    # If you prefer your helper, you can wrap it like this:
    #   rechunk_blocks takes generic Document[] and returns split Documents
    # Here we use a copy of your approach so we keep metadata and add chunk_idx:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""],
    )
    chunked_docs: list[Document] = []
    for d in doc_per_block:
        parts = splitter.split_text(d.page_content)
        for idx, piece in enumerate(parts):
            chunked_docs.append(Document(page_content=piece, metadata={**d.metadata, "chunk_idx": idx}))

    print(f"[*] {len(doc_per_block)} blocks → {len(chunked_docs)} chunks. Embedding and storing...")
    vectorstore = Chroma.from_documents(
        documents=chunked_docs,
        embedding=embedding_model,
        persist_directory=CHROMA_DIR,
    )
    vectorstore.persist()
    print("[✓] Embedding complete and saved to disk.")

# ---- RAG ----
def setup_rag_chain(topic_filter: Optional[str]):
    vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding_model)

    filt = {}
    if topic_filter:
        tnorm = normalize_topic(topic_filter)
        if tnorm in ALLOWED_TOPICS.values():
            # Only filter if it maps to a known topic; otherwise, do not filter.
            filt = {"topic": {"$eq": tnorm}}

    retriever = vectorstore.as_retriever(search_kwargs={
        "k": 6,
        "filter": filt or {},   # safe default: no filter if unrecognized
    })

    prompt = ChatPromptTemplate.from_template("""
Use the context below to answer the question. If the answer isn't in the context, say "I don't know."

Context:
{context}

Question: {question}
""")

    return (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
    )

# ---- Query category extractor (Gemini) ----
def run_llm(text: str) -> str:
    prompt = f"""
Your job is to determine what category this text belongs to.
Possible Categories (respond with EXACTLY one): Sponsorship, Meeting, Executives, Club History, Misc, CS, Geology, Sociology, Personal

Rules:
- If the text asks about money, assume Sponsorship.
- If the text is about a meeting, assume Meeting.
- If it's clearly Academic (CS/Geology/Sociology/Personal), choose that.
- Otherwise pick Misc.
- Respond with JUST the category name. No punctuation, no extra words.

{text}
"""
    client = genai.Client()
    resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return (resp.text or "").strip()

# ---- CLI ----
def run_chat():
    print("[*] Loading RAG system...")
    print("[✓] Ready to answer questions. Type 'exit' to quit.\n")

    while True:
        question = input("Ask a question: ")
        if question.lower() in ["exit", "quit"]:
            break
        try:
            topic_guess = run_llm(question)  # e.g., "Meeting" or "CS"
            chain = setup_rag_chain(topic_guess)
            response = chain.invoke(question)
            print(f"\n🧠 Answer:\n{response.content}\n")
        except Exception as e:
            print(f"[!] Error: {e}")

# ---- MAIN ----
if __name__ == "__main__":
    print("RAG CLI\n--------")
    choice = input("Do you want to (1) embed documents or (2) ask questions? Enter 1 or 2: ")

    if choice == "1":
        embed_documents()
    elif choice == "2":
        run_chat()
    else:
        print("Invalid choice.")
