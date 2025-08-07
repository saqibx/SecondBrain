import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain.vectorstores import Chroma
from Agents.utils import get_current_user
from Classes.ChromaDBHandler import ChromaDBHandler
from google import genai

load_dotenv()

# CHROMA_DIR = "chroma_db"

USERNAME = get_current_user().username
llm = ChatOpenAI(model="gpt-4.1-mini")

_rag_chain = None
db_handler = ChromaDBHandler(USERNAME)


def embed_documents_from_text(input_text: str, rebuild: bool = False):
    db_handler.embed_documents(input_text, rebuild=rebuild)


def check_vectorstore():
    try:
        vectorstore = Chroma(
            persist_directory=db_handler.chroma_dir,
            embedding_function=db_handler.embedding_model
        )
        return vectorstore._collection.count() > 0
    except Exception:
        return False


def setup_rag_chain():
    global _rag_chain
    if _rag_chain is not None:
        return _rag_chain

    retriever = db_handler.db.as_retriever(search_kwargs={"k": 6})

    prompt = ChatPromptTemplate.from_template("""
You are an AI assistant answering questions based on the provided context.

Use the following context to answer the question. If the answer is not clearly available in the context, say "I don't have enough information to answer that question based on the available documents."

Context:
{context}

Question: {question}

Answer:""")

    def format_docs(docs):
        return "\n\n---\n\n".join([
            f"Document {i+1} (Source: {doc.metadata.get('source_file', 'Unknown')}):\n{doc.metadata.get('title', '')}\n{doc.page_content}"
            for i, doc in enumerate(docs)
        ])

    _rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
    )
    return _rag_chain


def query_rag(question: str) -> str:
    if not question.strip():
        return "ERROR: No question provided."

    rag_chain = setup_rag_chain()
    try:
        response = rag_chain.invoke(question)
        return response.content
    except Exception as e:
        return f"RAG ERROR: {e}"


def run_llm(text):
    prompt = f'''
    Your job is to determine what category this text may be related to, Use boarder terms instead of the nichest categorization. 
    DO NOT ADD ANYTHING TO YOUR RESPONSE BUT THE CATEGORY.

    {text}
    '''
    try:
        client = genai.Client()
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return response.text.strip()
    except Exception as e:
        return "Misc"
