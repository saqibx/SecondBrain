import os
import re
import shutil
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()
model = ChatOpenAI(model="gpt-4o")

class ChromaDBHandler:
    def __init__(self, username: str):
        self.username = username
        self.chroma_dir = "Classes/chroma_db"
        self.embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
        self.db = Chroma(
            persist_directory=self.chroma_dir,
            collection_name=self.username,
            embedding_function=self.embedding_model
        )

    def parse_structured_blocks(self, text):
        blocks = re.split(r"---+", text)
        return [Document(page_content=block.strip()) for block in blocks if block.strip()]

    def load_all_documents(self, input_text):
        if "---" in input_text:
            return self.parse_structured_blocks(input_text)
        else:
            splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=700)
            return splitter.split_documents([Document(page_content=input_text)])

    def embed_documents(self, input_text: str, rebuild: bool = False):
        #print("[*] Loading and processing documents...")
        summarized_docs = get_summary_fromAI(input_text)
        all_docs = self.load_all_documents(summarized_docs)

        if not all_docs:
            print("[!] No documents to embed.")
            return

        print(f"[*] Total documents/chunks to embed: {len(all_docs)}")

        if rebuild:
            print("[*] Rebuilding vector database...")
            if os.path.exists(self.chroma_dir):
                shutil.rmtree(self.chroma_dir)
                print("[*] Existing database cleared.")
            self.db = Chroma.from_documents(
                documents=all_docs,
                embedding=self.embedding_model,
                persist_directory=self.chroma_dir,
                collection_name=self.username
            )
        else:
            print("[*] Adding to existing vector database...")
            self.db.add_documents(all_docs)

        print(f"[✓] Done. Total documents: {self.db._collection.count()}")

    def query(self, query_text: str, k: int = 5, include_metadata: bool = False):
        """Query the user's Chroma DB and return the top-k matching documents."""
        if not query_text.strip():
            print("[!] Query is empty.")
            return []

        print(f"[*] Querying for: \"{query_text}\" (top {k})")
        results = self.db.similarity_search(
            query=query_text,
            k=k
        )

        if not results:
            print("[!] No matching documents found.")
            return []

        print(f"[✓] Found {len(results)} results.")
        formatted_results = []

        for i, doc in enumerate(results):
            entry = {
                "rank": i + 1,
                "content": doc.page_content.strip()
            }
            if include_metadata and doc.metadata:
                entry["metadata"] = doc.metadata
            formatted_results.append(entry)

        return formatted_results

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
        response = model.invoke(prompt)
        return response.content



