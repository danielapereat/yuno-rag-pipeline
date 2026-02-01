"""
Configuration module for Yuno RAG Pipeline.
Manages all environment variables and settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# API KEYS
# =============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# =============================================================================
# MONGODB CONFIGURATION
# =============================================================================
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "yuno_rag")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "documents")
VECTOR_INDEX_NAME = os.getenv("VECTOR_INDEX_NAME", "vector_index")

# =============================================================================
# CHUNKING CONFIGURATION
# =============================================================================
# Optimized chunk size for better context and groundedness
# Larger chunks (1500-2000) provide more complete context
# Research shows this improves both precision and groundedness
# Reference: RAG Cookbook (Anthropic), Section 2.1 - Chunk Size Tuning
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "300"))

# =============================================================================
# RETRIEVAL CONFIGURATION
# =============================================================================
TOP_K = int(os.getenv("TOP_K", "5"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
GENERATION_MODEL = os.getenv("GENERATION_MODEL", "gpt-4o")

# =============================================================================
# TEAM CLASSIFICATION PATTERNS
# =============================================================================
TEAM_PATTERNS = {
    "TST12": "Integrations",  # TST12-XX tickets (Integrations team)
    "TST": "Integrations",     # Generic TST prefix
    "CORECM": "Core",
    "PFU": "Postmortem",
    "AP": "Feature Request",
    "DEM": "Demand"
}
