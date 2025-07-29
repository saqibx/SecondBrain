import json
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CohereRerank
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

def embed_documents():
    print("[*] Loading and chunking documents...")
    loader = TextLoader("DATA/premetadata.txt", encoding="utf-8")
    raw_docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=700)
    chunks = splitter.split_documents(raw_docs)

    print(f"[*] {len(chunks)} chunks generated. Embedding and storing...")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=CHROMA_DIR,
    )
    vectorstore.persist()
    print("[✓] Embedding complete and saved to disk.")

# ---- STEP 2: RAG PIPELINE ----

def setup_rag_chain(k_init=15, k_final=4):
    vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding_model)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})



    compressor = CohereRerank(model="rerank-english-v3.0", top_n=k_final)
    retriever = ContextualCompressionRetriever(
        base_retriever = retriever,
        base_compressor=compressor
    )

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

def run_chat():
    print("[*] Loading RAG system...")
    rag_chain = setup_rag_chain()
    print("[✓] Ready to answer questions. Type 'exit' to quit.\n")

    while True:
        question = input("Ask a question: ")
        if question.lower() in ["exit", "quit"]:
            break
        try:
            chain = setup_rag_chain(k_init=15,k_final=4)
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
