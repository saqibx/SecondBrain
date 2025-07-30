import json

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

load_dotenv()

# ---- SETUP ----

embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
llm = ChatOpenAI(model="gpt-4", temperature=0)

CHROMA_DIR = "./chroma_db"

# ---- STEP 1: LOAD + EMBED ----

def parse_blocks(raw_text):
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
                "guests": ", ".join(guests),  # ← this is the key fix
                "year": year
            }
        )
        documents.append(doc)

    return documents

def embed_documents():
    print("[*] Loading and chunking documents...")
    loader = TextLoader("DATA/premetadata.txt", encoding="utf-8")
    raw_docs = loader.load()


    splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=700)
    chunks = splitter.split_documents(raw_docs)

    full_text = "\n".join([doc.page_content for doc in raw_docs])
    docs = parse_blocks(full_text)

    print(f"[*] {len(chunks)} chunks generated. Embedding and storing...")
    vectorstore = Chroma(
        embedding_function=embedding_model,
        persist_directory=CHROMA_DIR,
    )
    vectorstore.add_documents(docs)

    print("[✓] Embedding complete and saved to disk.")

# ---- STEP 2: RAG PIPELINE ----

def setup_rag_chain(answer):
    print(answer)
    vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding_model)



    retriever = vectorstore.as_retriever(search_kwargs={"k": 4,

                                                        })

    prompt = ChatPromptTemplate.from_template("""
You are an AI assistant answering questions based only on the context below.
If you do not know the answer based on the context, say "I don't know."

Context:
{context}

Question: {question}
""")

    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
    )
    return rag_chain

# ---- CLI Interface ----

def run_llm(text):
    prompt = f'''
    Your job is to determine what category this text may be related to. Here are the possible options 
    Possible Categories : Sponsorship, meeting, executives, Misc, Club History
    
    No other possible categories. If the text asks about money assume its related to sponsorship,
    if the text asks about anything related to meetings assume its about meeting. If anything else assume its 
    misc
    
    DO NOT ADD ANYTHING TO YOUR RESPONSE BUT THE CATEGORY. NO GREETING NO NOTHING. JUST THE ANSWER.
    
    {text}
    '''
    client = genai.Client()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text

def run_chat():
    print("[*] Loading RAG system...")

    print("[✓] Ready to answer questions. Type 'exit' to quit.\n")

    while True:
        question = input("Ask a question: ")
        answer = run_llm(question)
        rag_chain = setup_rag_chain(answer)

        if question.lower() in ["exit", "quit"]:
            break
        try:
            response = rag_chain.invoke(question)
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
