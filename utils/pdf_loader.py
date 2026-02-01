"""
PDF loading utilities.
"""

from typing import Dict, List
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema import Document
import os


def load_pdf_with_metadata(file_path: str) -> List[Document]:
    """
    Load PDF and extract text content.

    Args:
        file_path: Path to PDF file

    Returns:
        List of Document objects with page content and metadata
    """
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    # Add filename to metadata
    filename = os.path.basename(file_path)
    for doc in documents:
        doc.metadata["filename"] = filename
        doc.metadata["file_path"] = file_path

    return documents


def merge_pages(documents: List[Document]) -> str:
    """
    Merge all pages into a single text string.

    Args:
        documents: List of Document objects

    Returns:
        Merged text content
    """
    return "\n\n".join([doc.page_content for doc in documents])
