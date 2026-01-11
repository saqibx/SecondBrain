"""RAG (Retrieval-Augmented Generation) functionality"""""""""import os



import loggingRAG (Retrieval-Augmented Generation) functionality for SecondBrain.

from langchain_openai import ChatOpenAI

from langchain_core.runnables import RunnablePassthroughHandles vector store management and LLM-based question answering.RAG (Retrieval-Augmented Generation) functionality for SecondBrain.from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate

from langchain.vectorstores import Chroma"""

from Classes.ChromaDBHandler import ChromaDBHandler

from tenacity import retry, stop_after_attempt, wait_exponentialHandles vector store management and LLM-based question answering.from langchain_openai import ChatOpenAI



logger = logging.getLogger(__name__)import os



import logging"""from langchain_core.runnables import RunnablePassthrough

class RAGManager:

    """Manages RAG chain and document retrieval"""from dotenv import load_dotenv



    def __init__(self, username: str = None):from langchain_openai import ChatOpenAIfrom langchain_core.prompts import ChatPromptTemplate

        """Initialize RAG manager for a user"""

        self.username = usernamefrom langchain_core.runnables import RunnablePassthrough

        self.db_handler = ChromaDBHandler(username) if username else None

        self._rag_chain = Nonefrom langchain_core.prompts import ChatPromptTemplateimport osfrom langchain.vectorstores import Chroma

        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

from langchain.vectorstores import Chroma

    def embed_documents_from_text(self, input_text: str, rebuild: bool = False):

        """Embed documents into the user knowledge base"""from Classes.ChromaDBHandler import ChromaDBHandlerimport loggingfrom Agents.utils import get_current_user

        if not self.db_handler:

            raise ValueError("RAGManager not initialized")from tenacity import retry, stop_after_attempt, wait_exponential

        try:

            self.db_handler.embed_documents(input_text, rebuild=rebuild)from dotenv import load_dotenvfrom Classes.ChromaDBHandler import ChromaDBHandler

            logger.info(f"Embedded documents for {self.username}")

        except Exception as e:load_dotenv()

            logger.error(f"Error embedding: {e}", exc_info=True)

            raisefrom langchain_openai import ChatOpenAIfrom google import genai



    def check_vectorstore(self) -> bool:logger = logging.getLogger(__name__)

        """Check if vector store has documents"""

        if not self.db_handler:from langchain_core.runnables import RunnablePassthrough

            return False

        try:_rag_chain = None

            vectorstore = Chroma(

                persist_directory=self.db_handler.chroma_dir,from langchain_core.prompts import ChatPromptTemplateload_dotenv()

                embedding_function=self.db_handler.embedding_model

            )

            return vectorstore._collection.count() > 0

        except Exception:class RAGManager:from langchain.vectorstores import Chroma

            return False

    """Manages RAG chain and document retrieval"""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))

    def setup_rag_chain(self):from Classes.ChromaDBHandler import ChromaDBHandler# CHROMA_DIR = "chroma_db"

        """Set up the RAG chain"""

        if self._rag_chain is not None:    def __init__(self, username: str = None):

            return self._rag_chain

        if not self.db_handler:        """Initialize RAG manager for a user"""from tenacity import retry, stop_after_attempt, wait_exponential

            raise ValueError("RAGManager not initialized")

        self.username = username

        retriever = self.db_handler.db.as_retriever(search_kwargs={"k": 6})

        prompt = ChatPromptTemplate.from_template(        self.db_handler = ChromaDBHandler(username) if username else NoneUSERNAME = get_current_user().username

            "Context: {context}\n\nQuestion: {question}\n\nAnswer based on context:"

        )        self._rag_chain = None



        def format_docs(docs):        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)load_dotenv()llm = ChatOpenAI(model="gpt-4.1-mini")

            return "\n---\n".join([f"{doc.metadata.get('title', '')}: {doc.page_content}" for doc in docs])



        self._rag_chain = (

            {"context": retriever | format_docs, "question": RunnablePassthrough()}    def embed_documents_from_text(self, input_text: str, rebuild: bool = False):

            | prompt

            | self.llm        """Embed documents into the user knowledge base"""

        )

        logger.info(f"RAG chain setup complete for {self.username}")        if not self.db_handler:logger = logging.getLogger(__name__)_rag_chain = None

        return self._rag_chain

            raise ValueError("RAGManager not properly initialized with username")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))

    def query_rag(self, question: str) -> str:db_handler = ChromaDBHandler(USERNAME)

        """Query the RAG system"""

        if not question or not question.strip():        try:

            raise ValueError("Question empty")

        try:            self.db_handler.embed_documents(input_text, rebuild=rebuild)_rag_chain = None

            rag_chain = self.setup_rag_chain()

            response = rag_chain.invoke(question)            logger.info(f"Embedded documents for user {self.username}")

            return response.content if response.content else "No response"

        except Exception as e:        except Exception as e:

            logger.error(f"RAG error: {e}", exc_info=True)

            return f"Error: {str(e)}"            logger.error(f"Error embedding documents: {e}", exc_info=True)



            raisedef embed_documents_from_text(input_text: str, rebuild: bool = False):

def embed_documents_from_text(input_text: str, username: str = None, rebuild: bool = False):

    """Backward compatibility wrapper"""

    try:

        from Agents.utils import get_current_user    def check_vectorstore(self) -> bool:class RAGManager:    db_handler.embed_documents(input_text, rebuild=rebuild)

        current_user = get_current_user()

        username = username or (current_user.username if current_user else None)        """Check if user vector store has documents"""

        if not username:

            raise ValueError("No username")        if not self.db_handler:    """Manages RAG chain and document retrieval"""

        manager = RAGManager(username)

        manager.embed_documents_from_text(input_text, rebuild=rebuild)            return False

    except Exception as e:

        logger.error(f"Error: {e}")    

        raise

        try:



def check_vectorstore(username: str = None) -> bool:            vectorstore = Chroma(    def __init__(self, username: str = None):def check_vectorstore():

    """Check vectorstore"""

    try:                persist_directory=self.db_handler.chroma_dir,

        from Agents.utils import get_current_user

        current_user = get_current_user()                embedding_function=self.db_handler.embedding_model        """    try:

        username = username or (current_user.username if current_user else None)

        if not username:            )

            return False

        manager = RAGManager(username)            count = vectorstore._collection.count()        Initialize RAG manager for a user.        vectorstore = Chroma(

        return manager.check_vectorstore()

    except Exception:            logger.debug(f"Vector store has {count} documents for user {self.username}")

        return False

            return count > 0                    persist_directory=db_handler.chroma_dir,



def setup_rag_chain(username: str = None):        except Exception as e:

    """Setup RAG chain"""

    try:            logger.warning(f"Error checking vector store: {e}")        Args:            embedding_function=db_handler.embedding_model

        from Agents.utils import get_current_user

        current_user = get_current_user()            return False

        username = username or (current_user.username if current_user else None)

        if not username:            username: Username for the ChromaDB handler        )

            raise ValueError("No username")

        manager = RAGManager(username)    @retry(

        return manager.setup_rag_chain()

    except Exception as e:        stop=stop_after_attempt(3),        """        return vectorstore._collection.count() > 0

        logger.error(f"Error: {e}")

        raise        wait=wait_exponential(multiplier=1, min=2, max=10)



    )        self.username = username    except Exception:

def query_rag(question: str, username: str = None) -> str:

    """Query RAG"""    def setup_rag_chain(self):

    try:

        from Agents.utils import get_current_user        """Set up the RAG chain for question answering"""        self.db_handler = ChromaDBHandler(username) if username else None        return False

        current_user = get_current_user()

        username = username or (current_user.username if current_user else None)        if self._rag_chain is not None:

        if not username:

            return "Error: Not authenticated"            return self._rag_chain        self._rag_chain = None

        manager = RAGManager(username)

        return manager.query_rag(question)

    except Exception as e:

        logger.error(f"Error: {e}")        if not self.db_handler:        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        return f"Error: {str(e)}"

            raise ValueError("RAGManager not properly initialized")

    def setup_rag_chain():

        try:

            retriever = self.db_handler.db.as_retriever(search_kwargs={"k": 6})    def embed_documents_from_text(self, input_text: str, rebuild: bool = False):    global _rag_chain



            prompt = ChatPromptTemplate.from_template("""        """    if _rag_chain is not None:

            You are an AI assistant answering questions based on context.

        Embed documents into the user's knowledge base.        return _rag_chain

            Context:

            {context}        



            Question: {question}        Args:    retriever = db_handler.db.as_retriever(search_kwargs={"k": 6})



            Use the context to answer. If not available, say you do not have            input_text: Text to embed

            enough information based on available documents.

            rebuild: Whether to rebuild the entire database    prompt = ChatPromptTemplate.from_template(f"""

            Answer:""")

        """    You are an AI assistant answering questions based on the provided context.

            def format_docs(docs):

                return "\n\n---\n\n".join([        if not self.db_handler:

                    f"Document {i+1}:\n"

                    f"Title: {doc.metadata.get('title', 'Unknown')}\n"            raise ValueError("RAGManager not properly initialized with username")    Use the following context to answer the question. If the answer is not clearly available in the context, say "I don't have enough information to answer that question based on the available documents."

                    f"Content: {doc.page_content}"

                    for i, doc in enumerate(docs)        

                ])

        try:   

            self._rag_chain = (

                {"context": retriever | format_docs, "question": RunnablePassthrough()}            self.db_handler.embed_documents(input_text, rebuild=rebuild)

                | prompt

                | self.llm            logger.info(f"Embedded documents for user {self.username}")    Answer:""")

            )

        except Exception as e:

            logger.info(f"RAG chain setup complete for user {self.username}")

            return self._rag_chain            logger.error(f"Error embedding documents: {e}", exc_info=True)    def format_docs(docs):



        except Exception as e:            raise        return "\n\n---\n\n".join([

            logger.error(f"Error setting up RAG chain: {e}", exc_info=True)

            raise                f"Document {i+1} (Source: {doc.metadata.get('source_file', 'Unknown')}):\n{doc.metadata.get('title', '')}\n{doc.page_content}"



    @retry(    def check_vectorstore(self) -> bool:            for i, doc in enumerate(docs)

        stop=stop_after_attempt(3),

        wait=wait_exponential(multiplier=1, min=2, max=10)        """        ])

    )

    def query_rag(self, question: str) -> str:        Check if user's vector store has documents.

        """Query the RAG system with a question"""

        if not question or not question.strip():            _rag_chain = (

            raise ValueError("Question cannot be empty")

        Returns:        {"context": retriever | format_docs, "question": RunnablePassthrough()}

        try:

            rag_chain = self.setup_rag_chain()            True if vector store has documents, False otherwise        | prompt

            response = rag_chain.invoke(question)

        """        | llm

            if not response.content:

                return "No response generated"        if not self.db_handler:    )



            logger.debug(f"RAG query successful for user {self.username}")            return False    return _rag_chain

            return response.content

        

        except Exception as e:

            logger.error(f"RAG query error: {e}", exc_info=True)        try:

            return f"Error processing query: {str(e)}"

            vectorstore = Chroma(def query_rag(question: str) -> str:



# Global functions for backward compatibility                persist_directory=self.db_handler.chroma_dir,    if not question.strip():

def embed_documents_from_text(input_text: str, username: str = None, rebuild: bool = False):

    """Embed documents (backward compatibility wrapper)"""                embedding_function=self.db_handler.embedding_model        return "ERROR: No question provided."

    try:

        from Agents.utils import get_current_user            )

        current_user = get_current_user()

        username = username or (current_user.username if current_user else None)            count = vectorstore._collection.count()    rag_chain = setup_rag_chain()



        if not username:            logger.debug(f"Vector store has {count} documents for user {self.username}")    try:

            raise ValueError("No username provided or user not authenticated")

            return count > 0        response = rag_chain.invoke(question)

        manager = RAGManager(username)

        manager.embed_documents_from_text(input_text, rebuild=rebuild)        except Exception as e:        return response.content

    except Exception as e:

        logger.error(f"Error in embed_documents_from_text: {e}")            logger.warning(f"Error checking vector store: {e}")    except Exception as e:

        raise

            return False        return f"RAG ERROR: {e}"



def check_vectorstore(username: str = None) -> bool:    

    """Check vector store (backward compatibility wrapper)"""

    try:    @retry(

        from Agents.utils import get_current_user

        current_user = get_current_user()        stop=stop_after_attempt(3),def run_llm(text):

        username = username or (current_user.username if current_user else None)

        wait=wait_exponential(multiplier=1, min=2, max=10)    prompt = f'''

        if not username:

            return False    )    Your job is to determine what category this text may be related to, Use boarder terms instead of the nichest categorization. 



        manager = RAGManager(username)    def setup_rag_chain(self):    DO NOT ADD ANYTHING TO YOUR RESPONSE BUT THE CATEGORY.

        return manager.check_vectorstore()

    except Exception:        """

        return False

        Set up the RAG chain for question answering.    {text}



def setup_rag_chain(username: str = None):        Uses caching to avoid recreating the chain.    '''

    """Setup RAG chain (backward compatibility wrapper)"""

    try:        """    try:

        from Agents.utils import get_current_user

        current_user = get_current_user()        if self._rag_chain is not None:        client = genai.Client()

        username = username or (current_user.username if current_user else None)

            return self._rag_chain        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)

        if not username:

            raise ValueError("No username provided or user not authenticated")                return response.text.strip()



        manager = RAGManager(username)        if not self.db_handler:    except Exception as e:

        return manager.setup_rag_chain()

    except Exception as e:            raise ValueError("RAGManager not properly initialized")        return "Misc"

        logger.error(f"Error in setup_rag_chain: {e}")

        raise        

        try:

            retriever = self.db_handler.db.as_retriever(search_kwargs={"k": 6})

def query_rag(question: str, username: str = None) -> str:            

    """Query RAG (backward compatibility wrapper)"""            prompt = ChatPromptTemplate.from_template("""

    try:            You are an AI assistant answering questions based on the provided context.

        from Agents.utils import get_current_user            

        current_user = get_current_user()            Context:

        username = username or (current_user.username if current_user else None)            {context}

            

        if not username:            Question: {question}

            return "Error: User not authenticated"            

            Use the following context to answer the question. If the answer is not clearly 

        manager = RAGManager(username)            available in the context, say "I don't have enough information to answer that 

        return manager.query_rag(question)            question based on the available documents."

    except Exception as e:            

        logger.error(f"Error in query_rag: {e}")            Answer:""")

        return f"Error: {str(e)}"            

            def format_docs(docs):
                return "\n\n---\n\n".join([
                    f"Document {i+1}:\n"
                    f"Title: {doc.metadata.get('title', 'Unknown')}\n"
                    f"Content: {doc.page_content}"
                    for i, doc in enumerate(docs)
                ])
            
            self._rag_chain = (
                {"context": retriever | format_docs, "question": RunnablePassthrough()}
                | prompt
                | self.llm
            )
            
            logger.info(f"RAG chain setup complete for user {self.username}")
            return self._rag_chain
            
        except Exception as e:
            logger.error(f"Error setting up RAG chain: {e}", exc_info=True)
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def query_rag(self, question: str) -> str:
        """
        Query the RAG system with a question.
        
        Args:
            question: Question to ask
            
        Returns:
            Answer from the RAG system
            
        Raises:
            ValueError: If question is empty
            Exception: If RAG query fails
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        
        try:
            rag_chain = self.setup_rag_chain()
            response = rag_chain.invoke(question)
            
            if not response.content:
                return "No response generated"
            
            logger.debug(f"RAG query successful for user {self.username}")
            return response.content
            
        except Exception as e:
            logger.error(f"RAG query error: {e}", exc_info=True)
            return f"Error processing query: {str(e)}"


# Global functions for backward compatibility
def embed_documents_from_text(input_text: str, username: str = None, rebuild: bool = False):
    """Embed documents (backward compatibility wrapper)"""
    try:
        from Agents.utils import get_current_user
        current_user = get_current_user()
        username = username or (current_user.username if current_user else None)
        
        if not username:
            raise ValueError("No username provided or user not authenticated")
        
        manager = RAGManager(username)
        manager.embed_documents_from_text(input_text, rebuild=rebuild)
    except Exception as e:
        logger.error(f"Error in embed_documents_from_text: {e}")
        raise


def check_vectorstore(username: str = None) -> bool:
    """Check vector store (backward compatibility wrapper)"""
    try:
        from Agents.utils import get_current_user
        current_user = get_current_user()
        username = username or (current_user.username if current_user else None)
        
        if not username:
            return False
        
        manager = RAGManager(username)
        return manager.check_vectorstore()
    except Exception:
        return False


def setup_rag_chain(username: str = None):
    """Setup RAG chain (backward compatibility wrapper)"""
    try:
        from Agents.utils import get_current_user
        current_user = get_current_user()
        username = username or (current_user.username if current_user else None)
        
        if not username:
            raise ValueError("No username provided or user not authenticated")
        
        manager = RAGManager(username)
        return manager.setup_rag_chain()
    except Exception as e:
        logger.error(f"Error in setup_rag_chain: {e}")
        raise


def query_rag(question: str, username: str = None) -> str:
    """Query RAG (backward compatibility wrapper)"""
    try:
        from Agents.utils import get_current_user
        current_user = get_current_user()
        username = username or (current_user.username if current_user else None)
        
        if not username:
            return "Error: User not authenticated"
        
        manager = RAGManager(username)
        return manager.query_rag(question)
    except Exception as e:
        logger.error(f"Error in query_rag: {e}")
        return f"Error: {str(e)}"
