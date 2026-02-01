#!/usr/bin/env python3.11
"""
Demo script to show groundedness evaluation on a single query.
"""

from evals.groundedness import GroundednessEvaluator
from generation.generator import ResponseGenerator

# Initialize
generator = ResponseGenerator(embedding_provider='openai')
evaluator = GroundednessEvaluator()

# Run query
query = 'What is SafetyPay?'
print(f'Query: {query}\n')

# Step 1: Retrieve documents
print('Retrieving documents...\n')
context_docs = generator.retriever.semantic_search(query, top_k=5)
print(f'Retrieved {len(context_docs)} documents')

# Step 2: Generate response
print('Generating answer...\n')
result = generator.generate_response(query, context_docs)

# Show answer
print('='*60)
print('ANSWER:')
print('='*60)
print(result['answer'])
print('='*60)

# Step 3: Evaluate groundedness
print('\nEvaluating groundedness...\n')
groundedness = evaluator.evaluate(
    query=query,
    generated_answer=result['answer'],
    context_docs=context_docs
)

# Show results
print('='*60)
print(f'Groundedness Score: {groundedness["groundedness_score"]:.2f}')
print(f'Verdict: {groundedness["verdict"]}')
print('\nAnalysis:')
print(groundedness["analysis"])
