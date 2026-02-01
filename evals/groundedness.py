"""
Groundedness Evaluation for Generated Responses.

Groundedness measures: "Is the generated answer supported by the retrieved context?"

This prevents hallucinations and ensures the model only uses provided information.
"""

from typing import List, Dict
from openai import OpenAI

from config import OPENAI_API_KEY, GENERATION_MODEL


class GroundednessEvaluator:
    """
    Evaluate if generated responses are grounded in retrieved context.

    A response is "grounded" if all claims can be traced back to the context.
    """

    def __init__(self):
        """Initialize groundedness evaluator."""
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def evaluate(
        self,
        query: str,
        generated_answer: str,
        context_docs: List[Dict]
    ) -> Dict:
        """
        Evaluate groundedness of a generated answer.

        Args:
            query: The user query
            generated_answer: The generated response
            context_docs: Documents that were used as context

        Returns:
            Dictionary with groundedness score and analysis
        """
        # Build context string
        context_text = "\n\n".join([
            f"[Documento {i+1}]\n{doc['content']}"
            for i, doc in enumerate(context_docs)
        ])

        # Prompt for groundedness evaluation
        prompt = f"""Evaluate whether the GENERATED RESPONSE is completely grounded in the provided CONTEXT.

ORIGINAL QUESTION:
{query}

PROVIDED CONTEXT:
{context_text[:3000]}  # Truncate for efficiency

GENERATED RESPONSE:
{generated_answer}

TASK:
Analyze whether each statement in the generated response can be verified in the context.

Respond in the following format:
1. VERDICT: [GROUNDED/PARTIALLY_GROUNDED/NOT_GROUNDED]
2. SCORE: [0.0 to 1.0, where 1.0 = completely grounded]
3. ANALYSIS: [Brief explanation of which parts are grounded and which are not]

VERDICT:"""

        # Use gpt-4o-mini for faster and cheaper groundedness evaluation
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        evaluation_text = response.choices[0].message.content.strip()

        # Parse the response
        score, verdict, analysis = self._parse_evaluation(evaluation_text)

        return {
            "groundedness_score": score,
            "verdict": verdict,
            "analysis": analysis,
            "query": query,
            "answer": generated_answer,
            "context_docs_count": len(context_docs)
        }

    def _parse_evaluation(self, evaluation_text: str) -> tuple:
        """
        Parse evaluation response into score, verdict, and analysis.

        Args:
            evaluation_text: Raw evaluation text from LLM

        Returns:
            Tuple of (score, verdict, analysis)
        """
        lines = evaluation_text.split("\n")

        verdict = "UNKNOWN"
        score = None
        analysis = ""

        for line in lines:
            line = line.strip()

            if line.startswith("1.") or "VEREDICTO:" in line:
                if "GROUNDED" in line.upper():
                    if "PARTIALLY" in line.upper():
                        verdict = "PARTIALLY_GROUNDED"
                    elif "NOT" in line.upper():
                        verdict = "NOT_GROUNDED"
                    else:
                        verdict = "GROUNDED"

            elif line.startswith("2.") or "SCORE:" in line:
                # Extract score - look specifically after "SCORE:" or number prefix
                import re

                # First, try to find score after "SCORE:" keyword
                if "SCORE:" in line.upper():
                    score_part = line.split(":", 1)[-1].strip()
                    # Match decimal numbers like 0.95, 1.0, 0.5
                    match = re.search(r'(\d+\.?\d*)', score_part)
                    if match:
                        parsed_score = float(match.group(1))
                        # Validate score is in valid range [0.0, 1.0]
                        if 0.0 <= parsed_score <= 1.0:
                            score = parsed_score

                # If not found, try pattern like "2. 0.95" (number followed by score)
                if score is None:
                    # Match pattern: optional prefix, then decimal number
                    match = re.search(r'^\d+\.\s*(\d+\.?\d*)', line)
                    if match:
                        parsed_score = float(match.group(1))
                        # Validate score is in valid range [0.0, 1.0]
                        if 0.0 <= parsed_score <= 1.0:
                            score = parsed_score

            elif line.startswith("3.") or "ANÁLISIS:" in line or "ANALISIS:" in line:
                # Extract analysis (may span multiple lines)
                analysis = line.split(":", 1)[-1].strip()

        # If score not found or invalid, infer from verdict
        if score is None:
            score_map = {
                "GROUNDED": 1.0,
                "PARTIALLY_GROUNDED": 0.5,
                "NOT_GROUNDED": 0.0,
                "UNKNOWN": 0.0
            }
            score = score_map.get(verdict, 0.0)

        return score, verdict, analysis

    def evaluate_batch(
        self,
        test_cases: List[Dict]
    ) -> Dict:
        """
        Evaluate groundedness across multiple test cases.

        Args:
            test_cases: List of dicts with 'query', 'answer', 'context_docs'

        Returns:
            Dictionary with average groundedness and per-case results
        """
        results = []

        for test_case in test_cases:
            eval_result = self.evaluate(
                query=test_case["query"],
                generated_answer=test_case["answer"],
                context_docs=test_case["context_docs"]
            )
            results.append(eval_result)

        avg_score = sum(r["groundedness_score"] for r in results) / len(results) if results else 0.0

        # Count verdicts
        verdict_counts = {}
        for result in results:
            verdict = result["verdict"]
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

        return {
            "average_groundedness": avg_score,
            "num_cases": len(results),
            "verdict_distribution": verdict_counts,
            "per_case_results": results
        }


# Example usage
if __name__ == "__main__":
    evaluator = GroundednessEvaluator()

    # Mock example
    query = "What is SafetyPay?"
    generated_answer = "SafetyPay is a non-card payment method that operates in 16 countries in Latin America with 380 associated banks."
    context_docs = [
        {
            "content": "SafetyPay is a non-card payment method with the largest bank network... operates in 16 countries with 380 bank partners...",
            "metadata": {"source_id": "3702794"}
        }
    ]

    result = evaluator.evaluate(query, generated_answer, context_docs)

    print(f"Groundedness Score: {result['groundedness_score']:.2f}")
    print(f"Verdict: {result['verdict']}")
    print(f"Analysis: {result['analysis']}")
