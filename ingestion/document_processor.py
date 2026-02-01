"""
Document processing and ingestion module.
This module handles loading, chunking, metadata extraction, and storage.
"""

import os
from typing import List, Dict
from pathlib import Path
from tqdm import tqdm

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from pymongo import MongoClient

from config import MONGODB_URI, MONGODB_DATABASE, MONGODB_COLLECTION, CHUNK_SIZE, CHUNK_OVERLAP, TEAM_PATTERNS
from utils.pdf_loader import load_pdf_with_metadata, merge_pages
from utils.metadata_extractor import (
    extract_metadata_from_filename,
    extract_provider_name,
    extract_jira_metadata,
    extract_confluence_metadata
)
from ingestion.embeddings import EmbeddingGenerator


class DocumentProcessor:
    """Handles document ingestion pipeline."""

    def __init__(self, embedding_provider: str = "openai"):
        """Initialize document processor with MongoDB and OpenAI clients."""
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[MONGODB_DATABASE]
        self.collection = self.db[MONGODB_COLLECTION]

        # Initialize embedding generator
        self.embedding_generator = EmbeddingGenerator(provider=embedding_provider)

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def process_directory(self, directory_path: str) -> int:
        """
        Process all PDFs in a directory (including subdirectories).

        Args:
            directory_path: Path to directory containing PDFs

        Returns:
            Number of documents processed
        """
        pdf_files = list(Path(directory_path).rglob("*.pdf"))
        print(f"Found {len(pdf_files)} PDF files to process")

        processed_count = 0

        for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
            try:
                self.process_document(str(pdf_path))
                processed_count += 1
            except Exception as e:
                print(f"\nError processing {pdf_path}: {e}")

        print(f"\nSuccessfully processed {processed_count}/{len(pdf_files)} documents")
        return processed_count

    def process_document(self, file_path: str) -> List[str]:
        """
        Process a single document: load, extract metadata, chunk, embed, store.

        Args:
            file_path: Path to PDF file

        Returns:
            List of inserted document IDs
        """
        filename = os.path.basename(file_path)

        # Step 1: Load PDF
        documents = load_pdf_with_metadata(file_path)
        full_content = merge_pages(documents)

        # Step 2: Extract base metadata from filename
        base_metadata = extract_metadata_from_filename(filename)

        # Step 3: Extract provider name using Claude
        provider_name = extract_provider_name(full_content, filename)
        if provider_name:
            base_metadata["provider_name"] = provider_name

        # Step 4: Extract document-type specific metadata
        if base_metadata["document_type"] == "jira":
            jira_meta = extract_jira_metadata(full_content)
            base_metadata.update(jira_meta)
        elif base_metadata["document_type"] == "confluence":
            confluence_meta = extract_confluence_metadata(full_content)
            base_metadata.update(confluence_meta)

        # Step 5: Chunk the document
        chunks = self.text_splitter.split_text(full_content)

        # Step 6: Generate embeddings and store
        inserted_ids = []
        for i, chunk in enumerate(chunks):
            # Generate embedding
            embedding = self.embedding_generator.generate_embedding(chunk)

            doc_metadata = base_metadata.copy()
            doc_metadata["chunk_index"] = i
            doc_metadata["total_chunks"] = len(chunks)

            doc_to_insert = {
                "content": chunk,
                "metadata": doc_metadata,
                "embedding": embedding
            }

            result = self.collection.insert_one(doc_to_insert)
            inserted_ids.append(str(result.inserted_id))

        return inserted_ids

    def clear_collection(self):
        """Clear all documents from the collection."""
        result = self.collection.delete_many({})
        print(f"Deleted {result.deleted_count} documents from collection")

    def get_stats(self) -> Dict:
        """
        Get statistics about the document collection.

        Returns:
            Dictionary with collection statistics
        """
        total_docs = self.collection.count_documents({})

        # Count by document type
        jira_count = self.collection.count_documents({"metadata.document_type": "jira"})
        confluence_count = self.collection.count_documents({"metadata.document_type": "confluence"})

        # Count by team
        team_counts = {}
        for team in TEAM_PATTERNS.values():
            count = self.collection.count_documents({"metadata.team": team})
            if count > 0:
                team_counts[team] = count

        # Count by provider
        providers = self.collection.distinct("metadata.provider_name")
        provider_counts = {}
        for provider in providers:
            if provider:
                count = self.collection.count_documents({"metadata.provider_name": provider})
                provider_counts[provider] = count

        return {
            "total_documents": total_docs,
            "jira_documents": jira_count,
            "confluence_documents": confluence_count,
            "teams": team_counts,
            "providers": provider_counts
        }


def main():
    """Main function for standalone execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Process and ingest documents into MongoDB")
    parser.add_argument("directory", help="Directory containing PDF files")
    parser.add_argument("--clear", action="store_true", help="Clear collection before processing")

    args = parser.parse_args()

    processor = DocumentProcessor()

    if args.clear:
        print("Clearing existing collection...")
        processor.clear_collection()

    print(f"Processing documents from: {args.directory}")
    processor.process_directory(args.directory)

    print("\nCollection Statistics:")
    stats = processor.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
