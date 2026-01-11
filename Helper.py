"""Helper functions for document processing""""""

Helper functions for document processing and AI summarization.

import logging"""

from typing import Tuple, List

from langchain_core.documents import Documentimport os

from langchain_text_splitters import RecursiveCharacterTextSplitterimport re

from langchain_openai import ChatOpenAIimport logging

from tenacity import retry, stop_after_attempt, wait_exponentialfrom dotenv import load_dotenv

from typing import Tuple, List

logger = logging.getLogger(__name__)from langchain_core.documents import Document

from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_openai import ChatOpenAI

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))from tenacity import retry, stop_after_attempt, wait_exponential

def get_summary_fromAI(text: str, model: str = "gpt-4o-mini") -> str:

    """Summarize text using OpenAI with retry logic"""load_dotenv()

    if not text or not text.strip():

        raise ValueError("Cannot summarize empty text")logger = logging.getLogger(__name__)



    prompt = f"Summarize this document clearly: {text[:1000]}"

    llm = ChatOpenAI(model=model, temperature=0)@retry(

    response = llm.invoke(prompt)    stop=stop_after_attempt(3),

    if not response.content:    wait=wait_exponential(multiplier=1, min=2, max=10)

        raise ValueError("Empty response from LLM"))

    logger.debug(f"Summarized text of length {len(text)}")def get_summary_fromAI(text: str, model: str = "gpt-4o-mini") -> str:

    return response.content    """

    Summarize text using OpenAI API with retry logic.



def split_into_blocks(text: str) -> Tuple[List[Document], str]:    Args:

    """Split text into blocks separated by --- markers"""        text: Text to summarize

    if not text:        model: Model to use for summarization

        return [], ""

    import re    Returns:

    BLOCK_RE = re.compile(r"^\s*---\s*(.*?)\s*---\s*$", flags=re.MULTILINE)        Summarized text

    parts = BLOCK_RE.split(text)    """

    docs = []    if not text or not text.strip():

    preamble = parts[0].strip()        raise ValueError("Cannot summarize empty text")

    i = 1

    while i < len(parts):    prompt = f"""You are a summarizing assistant. Your job is to extract 

        title = parts[i].strip()    information into clear language for RAG systems.

        block = parts[i + 1].strip() if i + 1 < len(parts) else ""

        if block:    Rules:

            docs.append(Document(page_content=block, metadata={"title": title}))    - Do NOT invent facts

        i += 2    - Use plain language

    logger.debug(f"Split text into {len(docs)} blocks")    - Include all relevant details

    return docs, preamble    - Follow format based on document type



    If Tech Start UCalgary related:

def rechunk_blocks(block_docs: List[Document], chunk_size: int = 1200, chunk_overlap: int = 150) -> List[Document]:    Topic: (sponsorship/meeting/club history/executives/misc)

    """Rechunk documents into smaller chunks"""    Guests: (names of companies)

    if not block_docs:    Year: (if mentioned)

        return []    Notes: (summary)

    splitter = RecursiveCharacterTextSplitter(

        chunk_size=chunk_size,    If academic:

        chunk_overlap=chunk_overlap,    Topic: (subject name)

        separators=["\n\n", "\n", " ", ""],    Year: (if mentioned)

    )    Notes: (concepts and facts)

    rechunked = splitter.split_documents(block_docs)

    logger.debug(f"Rechunked {len(block_docs)} docs into {len(rechunked)} chunks")    Otherwise:

    return rechunked    Topic: Researched Items - [topic]

    Notes: [summary]

    Document text:
    {text}"""

    try:
        llm = ChatOpenAI(model=model, temperature=0)
        response = llm.invoke(prompt)

        if not response.content:
            raise ValueError("Empty response from LLM")

        logger.debug(f"Successfully summarized text of length {len(text)}")
        return response.content

    except Exception as e:
        logger.error(f"Error in get_summary_fromAI: {e}", exc_info=True)
        raise


BLOCK_RE = re.compile(r"^\s*---\s*(.*?)\s*---\s*$", flags=re.MULTILINE)


def split_into_blocks(text: str) -> Tuple[List[Document], str]:
    """
    Split text into blocks separated by --- markers.

    Args:
        text: Text containing blocks separated by ---

    Returns:
        Tuple of (documents list, preamble text)
    """
    if not text:
        return [], ""

    parts = BLOCK_RE.split(text)
    docs = []
    preamble = parts[0].strip()

    i = 1
    while i < len(parts):
        title = parts[i].strip()
        block = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if block:
            docs.append(Document(page_content=block, metadata={"title": title}))
        i += 2

    logger.debug(f"Split text into {len(docs)} blocks")
    return docs, preamble


def rechunk_blocks(
    block_docs: List[Document],
    chunk_size: int = 1200,
    chunk_overlap: int = 150
) -> List[Document]:
    """
    Rechunk documents into smaller chunks for better retrieval.

    Args:
        block_docs: List of documents to rechunk
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks

    Returns:
        List of rechunked documents
    """
    if not block_docs:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )

    rechunked = splitter.split_documents(block_docs)
    logger.debug(f"Rechunked {len(block_docs)} docs into {len(rechunked)} chunks")
    return rechunked
