#!/usr/bin/env python3.11
"""
Demo script to show precision evaluation on a single query.
"""

from evals.precision import PrecisionEvaluator
from retrieval.retriever import HybridRetriever

# Initialize
retriever = HybridRetriever(embedding_provider='openai')
evaluator = PrecisionEvaluator()

# Run query
query = 'What is SafetyPay?'
print(f'Query: {query}\n')

# Retrieve documents
docs = retriever.semantic_search(query, top_k=5)
print(f'Retrieved {len(docs)} documents')
print('='*60)

# Evaluate precision
print('\nEvaluating relevance...\n')
result = evaluator.evaluate(query, docs)

# Show results
print('='*60)
print(f'Precision: {result["precision"]:.2%}')
print(f'Relevant: {result["relevant_count"]}/{result["total_retrieved"]}')
print('\nRelevance breakdown:')
for i, judgment in enumerate(result['relevance_judgments'], 1):
    status = '✓ Relevant' if judgment['is_relevant'] else '✗ Not relevant'
    print(f'  Doc {i}: {status}')
