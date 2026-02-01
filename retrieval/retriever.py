"""
Hybrid Retrieval Module with Metadata Filtering.

This retriever supports:
1. Semantic search with vector embeddings
2. Metadata filtering (team, provider, document type)
3. Analytical queries (count, aggregation)
4. Cross-document retrieval (Jira + Confluence)
"""

from typing import List, Dict, Optional, Any
from pymongo import MongoClient
import numpy as np

from config import MONGODB_URI, MONGODB_DATABASE, MONGODB_COLLECTION, TOP_K, SIMILARITY_THRESHOLD
from ingestion.embeddings import EmbeddingGenerator


class HybridRetriever:
    """Hybrid retrieval with vector search and metadata filtering."""

    def __init__(self, embedding_provider: str = "openai"):
        """
        Initialize retriever.

        Args:
            embedding_provider: Embedding provider to use ('openai', 'voyage', 'local')
        """
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[MONGODB_DATABASE]
        self.collection = self.db[MONGODB_COLLECTION]
        self.embedding_generator = EmbeddingGenerator(provider=embedding_provider)

    def semantic_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = None,
        use_mmr: bool = True,
        lambda_param: float = 0.7
    ) -> List[Dict]:
        """
        Perform semantic search with optional MMR re-ranking and metadata filtering.

        MMR (Maximal Marginal Relevance) balances relevance with diversity to avoid
        redundant results. Based on Carbonell & Goldstein (1998).

        Args:
            query: Search query text
            filters: MongoDB-style filters (e.g., {"metadata.team": "Integraciones"})
            top_k: Number of results to return
            use_mmr: Whether to apply MMR re-ranking for diversity (default: True)
            lambda_param: MMR balance parameter (default: 0.7)
                         1.0 = only relevance, 0.0 = only diversity
                         Recommended: 0.7 (70% relevance, 30% diversity)

        Returns:
            List of documents with content and metadata
        """
        if top_k is None:
            top_k = TOP_K

        # Generate query embedding
        query_embedding = self.embedding_generator.generate_embedding(query)

        # Fetch more candidates for MMR to select from
        # Standard practice: fetch 2-3x more candidates than needed
        fetch_limit = top_k * 3 if use_mmr else top_k

        # Build MongoDB Atlas Vector Search pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": 100,
                    "limit": fetch_limit
                }
            },
            {
                "$project": {
                    "content": 1,
                    "metadata": 1,
                    "embedding": 1,  # Include embedding for MMR calculation
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]

        # Add metadata filters if provided
        if filters:
            # Add $match stage after $vectorSearch for metadata filtering
            pipeline.append({"$match": filters})

        # Execute vector search
        candidates = []
        for doc in self.collection.aggregate(pipeline):
            candidates.append({
                "content": doc["content"],
                "metadata": doc["metadata"],
                "embedding": doc.get("embedding"),
                "similarity": doc.get("score", 0.0),
                "_id": str(doc["_id"])
            })

        # Apply MMR re-ranking if enabled
        if use_mmr and len(candidates) > 0:
            results = self._mmr_rerank(
                query_embedding=query_embedding,
                candidates=candidates,
                top_k=top_k,
                lambda_param=lambda_param
            )
        else:
            results = candidates[:top_k]

        # Remove embeddings from final results (not needed in downstream processing)
        for result in results:
            result.pop("embedding", None)

        return results

    def get_by_ticket_id(self, ticket_id: str) -> List[Dict]:
        """
        Get all chunks for a specific Jira ticket.

        Args:
            ticket_id: Jira ticket ID (e.g., "AP-541")

        Returns:
            List of document chunks
        """
        documents = list(self.collection.find({"metadata.source_id": ticket_id}))

        return [
            {
                "content": doc["content"],
                "metadata": doc["metadata"],
                "_id": str(doc["_id"])
            }
            for doc in documents
        ]

    def get_by_provider(self, provider_name: str, doc_type: Optional[str] = None) -> List[Dict]:
        """
        Get all documents for a specific provider.

        Args:
            provider_name: Provider name (e.g., "SafetyPay")
            doc_type: Optional filter by document type ("jira" or "confluence")

        Returns:
            List of documents
        """
        filters = {"metadata.provider_name": provider_name}

        if doc_type:
            filters["metadata.document_type"] = doc_type

        documents = list(self.collection.find(filters))

        return [
            {
                "content": doc["content"],
                "metadata": doc["metadata"],
                "_id": str(doc["_id"])
            }
            for doc in documents
        ]

    def count_by_team(self) -> Dict[str, int]:
        """
        Count tickets by team.

        Returns:
            Dictionary with team counts
        """
        pipeline = [
            {"$match": {"metadata.document_type": "jira"}},
            {"$group": {
                "_id": "$metadata.team",
                "count": {"$sum": 1}
            }}
        ]

        results = self.collection.aggregate(pipeline)
        return {item["_id"]: item["count"] for item in results if item["_id"]}

    def count_by_provider(self) -> Dict[str, int]:
        """
        Count tickets by provider.

        Returns:
            Dictionary with provider counts
        """
        pipeline = [
            {"$match": {
                "metadata.document_type": "jira",
                "metadata.provider_name": {"$ne": None}
            }},
            {"$group": {
                "_id": "$metadata.provider_name",
                "count": {"$sum": 1}
            }}
        ]

        results = self.collection.aggregate(pipeline)
        return {item["_id"]: item["count"] for item in results}

    def get_providers_with_capability(self, capability: str) -> List[str]:
        """
        Find providers that support a specific capability (e.g., "PIX").

        Args:
            capability: Payment method or capability name

        Returns:
            List of provider names
        """
        # Search in Confluence documents for the capability
        results = self.semantic_search(
            query=capability,
            filters={"metadata.document_type": "confluence"},
            top_k=20
        )

        # Extract unique providers
        providers = set()
        for result in results:
            provider = result["metadata"].get("provider_name")
            if provider:
                providers.add(provider)

        return list(providers)

    def get_ticket_with_provider_docs(self, ticket_id: str) -> Dict:
        """
        Get ticket information along with provider documentation.

        Args:
            ticket_id: Jira ticket ID

        Returns:
            Dictionary with ticket chunks and related provider documentation
        """
        # Get ticket chunks
        ticket_chunks = self.get_by_ticket_id(ticket_id)

        if not ticket_chunks:
            return {
                "ticket": None,
                "provider_docs": [],
                "error": "Ticket not found"
            }

        # Extract provider from ticket metadata
        provider_name = ticket_chunks[0]["metadata"].get("provider_name")

        provider_docs = []
        if provider_name:
            # Get Confluence docs for this provider
            provider_docs = self.get_by_provider(provider_name, doc_type="confluence")

        return {
            "ticket_id": ticket_id,
            "ticket": ticket_chunks,
            "provider_name": provider_name,
            "provider_docs": provider_docs
        }

    def _mmr_rerank(
        self,
        query_embedding: List[float],
        candidates: List[Dict],
        top_k: int,
        lambda_param: float
    ) -> List[Dict]:
        """
        Re-rank candidates using Maximal Marginal Relevance (MMR).

        MMR iteratively selects documents that are:
        1. Relevant to the query (high similarity to query)
        2. Diverse from already selected documents (low similarity to selected)

        Formula: MMR = λ * sim(q, d) - (1-λ) * max(sim(d, s) for s in selected)

        Reference: Carbonell & Goldstein (1998) "The Use of MMR, Diversity-Based
        Reranking for Reordering Documents and Producing Summaries"

        Args:
            query_embedding: Query vector
            candidates: Candidate documents with embeddings
            top_k: Number of documents to select
            lambda_param: Balance between relevance and diversity (0 to 1)

        Returns:
            Re-ranked list of top_k documents
        """
        if not candidates:
            return []

        # Start with empty selected set
        selected = []
        remaining = candidates.copy()

        # Iteratively select top_k documents
        for _ in range(min(top_k, len(candidates))):
            if not remaining:
                break

            # Calculate MMR score for each remaining document
            mmr_scores = []
            for doc in remaining:
                # Relevance: similarity to query
                relevance = self._cosine_similarity(query_embedding, doc["embedding"])

                # Diversity: max similarity to already selected documents
                if selected:
                    diversity_penalty = max(
                        self._cosine_similarity(doc["embedding"], sel["embedding"])
                        for sel in selected
                    )
                else:
                    diversity_penalty = 0.0

                # MMR score
                mmr_score = lambda_param * relevance - (1 - lambda_param) * diversity_penalty
                mmr_scores.append((doc, mmr_score))

            # Select document with highest MMR score
            best_doc, best_score = max(mmr_scores, key=lambda x: x[1])
            selected.append(best_doc)
            remaining.remove(best_doc)

        return selected

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0 to 1)
        """
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))


# Example usage
if __name__ == "__main__":
    retriever = HybridRetriever(embedding_provider="local")

    # Test semantic search
    results = retriever.semantic_search("SafetyPay payment integration", top_k=3)
    print(f"Found {len(results)} results")

    # Test analytics
    team_counts = retriever.count_by_team()
    print(f"Tickets by team: {team_counts}")

    provider_counts = retriever.count_by_provider()
    print(f"Tickets by provider: {provider_counts}")
