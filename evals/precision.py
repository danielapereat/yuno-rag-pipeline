"""
Precision Evaluation for Retrieval.

Precision = (Number of relevant documents retrieved) / (Total documents retrieved)

This measures: "Of all the documents we retrieved, how many are actually relevant?"
"""

from typing import List, Dict, Tuple
from openai import OpenAI

from config import OPENAI_API_KEY, GENERATION_MODEL


class PrecisionEvaluator:
    """
    Evaluate retrieval precision.

    Precision measures the proportion of retrieved documents that are relevant.
    """

    def __init__(self):
        """Initialize precision evaluator."""
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def evaluate(
        self,
        query: str,
        retrieved_docs: List[Dict],
        use_llm: bool = True
    ) -> Dict:
        """
        Evaluate precision for a query and retrieved documents.

        Args:
            query: The search query
            retrieved_docs: List of retrieved documents
            use_llm: Whether to use LLM for relevance judgment (True) or manual labels (False)

        Returns:
            Dictionary with precision score and details
        """
        if not retrieved_docs:
            return {
                "precision": 0.0,
                "total_retrieved": 0,
                "relevant_count": 0,
                "relevance_judgments": []
            }

        if use_llm:
            relevance_judgments = self._judge_relevance_with_llm(query, retrieved_docs)
        else:
            # For manual evaluation, you would provide ground truth labels
            raise NotImplementedError("Manual evaluation requires ground truth labels")

        relevant_count = sum(1 for judgment in relevance_judgments if judgment["is_relevant"])
        total_retrieved = len(retrieved_docs)

        precision = relevant_count / total_retrieved if total_retrieved > 0 else 0.0

        return {
            "precision": precision,
            "total_retrieved": total_retrieved,
            "relevant_count": relevant_count,
            "relevance_judgments": relevance_judgments
        }

    def _judge_relevance_with_llm(
        self,
        query: str,
        retrieved_docs: List[Dict]
    ) -> List[Dict]:
        """
        Use Claude to judge relevance of each retrieved document.

        Args:
            query: The search query
            retrieved_docs: Retrieved documents

        Returns:
            List of relevance judgments
        """
        judgments = []

        for i, doc in enumerate(retrieved_docs):
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})

            prompt = f"""Evaluate whether the following document is RELEVANT to answer the user's question.

QUESTION:
{query}

DOCUMENT:
{content[:1000]}  # Truncated for efficiency

Is this document relevant to answer the question?

Respond ONLY with "RELEVANT" or "NOT RELEVANT", followed by a brief justification (maximum 1 line).

Format: [RELEVANT/NOT RELEVANT] - [justification]"""

            # Use gpt-4o-mini for faster and cheaper relevance judgments
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )

            judgment_text = response.choices[0].message.content.strip()

            is_relevant = "RELEVANT" in judgment_text.split("-")[0].upper() and "NOT RELEVANT" not in judgment_text.upper()

            judgments.append({
                "document_index": i,
                "source_id": metadata.get("source_id"),
                "is_relevant": is_relevant,
                "judgment": judgment_text,
                "similarity_score": doc.get("similarity")
            })

        return judgments

    def evaluate_batch(
        self,
        test_queries: List[Tuple[str, List[Dict]]]
    ) -> Dict:
        """
        Evaluate precision across multiple queries.

        Args:
            test_queries: List of (query, retrieved_docs) tuples

        Returns:
            Dictionary with average precision and per-query results
        """
        results = []

        for query, docs in test_queries:
            eval_result = self.evaluate(query, docs)
            results.append({
                "query": query,
                **eval_result
            })

        avg_precision = sum(r["precision"] for r in results) / len(results) if results else 0.0

        return {
            "average_precision": avg_precision,
            "num_queries": len(results),
            "per_query_results": results
        }


# Example usage
if __name__ == "__main__":
    evaluator = PrecisionEvaluator()

    # Mock example
    query = "How to configure SafetyPay?"
    retrieved_docs = [
        {
            "content": "SafetyPay requires API Key and Signature for configuration...",
            "metadata": {"source_id": "3702794", "document_type": "confluence"}
        },
        {
            "content": "This ticket describes a status mapping library implementation...",
            "metadata": {"source_id": "AP-541", "document_type": "jira"}
        }
    ]

    result = evaluator.evaluate(query, retrieved_docs)

    print(f"Precision: {result['precision']:.2%}")
    print(f"Relevant: {result['relevant_count']}/{result['total_retrieved']}")

    for judgment in result["relevance_judgments"]:
        print(f"\nDoc {judgment['document_index']} ({judgment['source_id']}): {'✓' if judgment['is_relevant'] else '✗'}")
        print(f"  {judgment['judgment']}")
