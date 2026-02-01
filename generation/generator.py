"""
Response generation using OpenAI GPT-4.

This module generates answers based on retrieved context.
"""

from typing import List, Dict, Optional
from openai import OpenAI

from config import OPENAI_API_KEY, GENERATION_MODEL
from retrieval.retriever import HybridRetriever


class ResponseGenerator:
    """Generate responses using OpenAI GPT-4 with retrieved context."""

    def __init__(self, embedding_provider: str = "openai"):
        """
        Initialize response generator.

        Args:
            embedding_provider: Embedding provider for retriever
        """
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.retriever = HybridRetriever(embedding_provider=embedding_provider)

    def generate_response(
        self,
        query: str,
        context_docs: List[Dict],
        max_tokens: int = 2048
    ) -> Dict:
        """
        Generate response using OpenAI GPT-4 based on retrieved context.

        Args:
            query: User query
            context_docs: Retrieved documents with content and metadata
            max_tokens: Maximum tokens in response

        Returns:
            Dictionary with response and metadata
        """
        # Build context from retrieved documents
        context_text = self._build_context(context_docs)

        # Build prompt
        prompt = self._build_prompt(query, context_text)

        # Generate response
        response = self.openai_client.chat.completions.create(
            model=GENERATION_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "answer": response.choices[0].message.content,
            "sources": self._extract_sources(context_docs),
            "model": GENERATION_MODEL,
            "usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            }
        }

    def query(
        self,
        query: str,
        filters: Optional[Dict] = None,
        top_k: int = None
    ) -> Dict:
        """
        Complete query pipeline: retrieve + generate.

        Args:
            query: User query
            filters: Optional metadata filters
            top_k: Number of documents to retrieve

        Returns:
            Dictionary with answer and metadata
        """
        # Step 1: Retrieve relevant documents
        context_docs = self.retriever.semantic_search(
            query=query,
            filters=filters,
            top_k=top_k
        )

        # Step 2: Generate response
        if not context_docs:
            return {
                "answer": "I couldn't find relevant documents to answer your question.",
                "sources": [],
                "retrieved_docs": 0
            }

        result = self.generate_response(query, context_docs)
        result["retrieved_docs"] = len(context_docs)

        return result

    def query_with_analytics(self, query: str) -> Dict:
        """
        Handle analytical queries (counts, aggregations).

        Args:
            query: User query

        Returns:
            Dictionary with answer
        """
        import unicodedata
        # Normalize query (remove accents and lowercase)
        query_normalized = unicodedata.normalize('NFD', query.lower())
        query_normalized = ''.join(c for c in query_normalized if not unicodedata.combining(c))

        # Detect analytical queries
        if "cuantos" in query_normalized and "integraciones" in query_normalized:
            team_counts = self.retriever.count_by_team()
            integrations_count = team_counts.get("Integrations", 0)

            return {
                "answer": f"There are {integrations_count} tickets from the Integrations team in the database.",
                "analytics": team_counts,
                "query_type": "analytical"
            }

        elif "cuantos" in query_normalized or "contar" in query_normalized:
            team_counts = self.retriever.count_by_team()
            provider_counts = self.retriever.count_by_provider()

            answer = "Ticket statistics:\n\n"
            answer += "By team:\n"
            for team, count in team_counts.items():
                answer += f"- {team}: {count} tickets\n"

            answer += "\nBy provider:\n"
            for provider, count in sorted(provider_counts.items(), key=lambda x: x[1], reverse=True):
                answer += f"- {provider}: {count} tickets\n"

            return {
                "answer": answer,
                "analytics": {
                    "teams": team_counts,
                    "providers": provider_counts
                },
                "query_type": "analytical"
            }

        elif "mas tickets" in query_normalized:
            provider_counts = self.retriever.count_by_provider()

            if not provider_counts:
                return {
                    "answer": "I couldn't find tickets associated with providers.",
                    "query_type": "analytical"
                }

            top_provider = max(provider_counts.items(), key=lambda x: x[1])

            answer = f"The provider with the most reported tickets is **{top_provider[0]}** with {top_provider[1]} tickets.\n\n"
            answer += "Complete ranking:\n"
            for provider, count in sorted(provider_counts.items(), key=lambda x: x[1], reverse=True):
                answer += f"- {provider}: {count} tickets\n"

            return {
                "answer": answer,
                "analytics": provider_counts,
                "query_type": "analytical"
            }

        elif "ticket" in query_normalized and any(prefix in query.upper() for prefix in ["AP-", "CORECM-", "PFU-", "TST", "DEM-"]):
            # Extract ticket ID
            ticket_id = self._extract_ticket_id(query)

            if ticket_id:
                ticket_data = self.retriever.get_ticket_with_provider_docs(ticket_id)

                if ticket_data["ticket"]:
                    # Generate comprehensive response
                    context_docs = ticket_data["ticket"] + ticket_data["provider_docs"][:3]
                    result = self.generate_response(query, context_docs)

                    result["ticket_id"] = ticket_id
                    result["provider_name"] = ticket_data["provider_name"]
                    result["has_provider_docs"] = len(ticket_data["provider_docs"]) > 0

                    return result
                else:
                    return {
                        "answer": f"I couldn't find ticket {ticket_id} in the database.",
                        "query_type": "ticket_lookup"
                    }

        # Default: semantic search
        return self.query(query)

    def _build_context(self, context_docs: List[Dict]) -> str:
        """Build context string from retrieved documents."""
        context_parts = []

        for i, doc in enumerate(context_docs, 1):
            metadata = doc.get("metadata", {})
            doc_type = metadata.get("document_type") or "unknown"
            source_id = metadata.get("source_id") or "unknown"

            context_parts.append(f"[Documento {i} - {doc_type.upper()}: {source_id}]")
            context_parts.append(doc["content"])
            context_parts.append("")  # Empty line

        return "\n".join(context_parts)

    def _build_prompt(self, query: str, context: str) -> str:
        """Build prompt for Claude."""
        return f"""You are an expert assistant in Yuno technical documentation, a fintech payments platform.

Your task is to answer questions based ONLY on the context provided below.

IMPORTANT RULES:
1. Only use information present in the context
2. If the information is not in the context, say you don't have it
3. Cite sources when relevant (mention the document ID)
4. Respond in English clearly and concisely
5. If you mention a payment provider, include relevant technical details (API, credentials, supported countries, etc.)

CONTEXT:
{context}

USER QUESTION:
{query}

RESPONSE:"""

    def _extract_sources(self, context_docs: List[Dict]) -> List[Dict]:
        """Extract source information from context documents."""
        sources = []
        seen = set()

        for doc in context_docs:
            metadata = doc["metadata"]
            source_id = metadata.get("source_id")

            if source_id and source_id not in seen:
                sources.append({
                    "id": source_id,
                    "type": metadata.get("document_type"),
                    "provider": metadata.get("provider_name"),
                    "file": metadata.get("source_file")
                })
                seen.add(source_id)

        return sources

    def _extract_ticket_id(self, text: str) -> Optional[str]:
        """Extract Jira ticket ID from text."""
        import re

        patterns = [
            r'(AP-\d+)',
            r'(CORECM-\d+)',
            r'(PFU-\d+)',
            r'(TST\d+-\d+)',
            r'(DEM-\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text.upper())
            if match:
                return match.group(1)

        return None


# Example usage
if __name__ == "__main__":
    generator = ResponseGenerator(embedding_provider="local")

    # Test query
    result = generator.query("How to configure SafetyPay?")

    print("Answer:", result["answer"])
    print("\nSources:", result["sources"])
    print("\nRetrieved docs:", result["retrieved_docs"])
