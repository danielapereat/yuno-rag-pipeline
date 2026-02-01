"""
Main script for Yuno RAG Pipeline.

This script provides a simple interface to:
1. Ingest documents
2. Query the system
3. Run evaluations
"""

import argparse
import json
from pathlib import Path

from ingestion.document_processor import DocumentProcessor
from generation.generator import ResponseGenerator
from evals.precision import PrecisionEvaluator
from evals.groundedness import GroundednessEvaluator


def ingest_documents(data_dir: str, clear: bool = False, embedding_provider: str = "openai"):
    """
    Ingest documents from directory.

    Args:
        data_dir: Directory containing PDF files
        clear: Whether to clear collection before ingesting
        embedding_provider: Embedding provider to use
    """
    print(f"\n{'='*60}")
    print("INGESTING DOCUMENTS")
    print(f"{'='*60}\n")

    processor = DocumentProcessor(embedding_provider=embedding_provider)

    if clear:
        print("⚠️  Clearing existing collection...")
        processor.clear_collection()

    print(f"📂 Processing documents from: {data_dir}")
    processor.process_directory(data_dir)

    print("\n📊 Collection Statistics:")
    stats = processor.get_stats()
    print(json.dumps(stats, indent=2))


def query_system(query: str, embedding_provider: str = "openai"):
    """
    Query the RAG system.

    Args:
        query: User question
        embedding_provider: Embedding provider to use
    """
    print(f"\n{'='*60}")
    print("QUERYING SYSTEM")
    print(f"{'='*60}\n")

    print(f"❓ Query: {query}\n")

    generator = ResponseGenerator(embedding_provider=embedding_provider)

    # Use smart query routing
    result = generator.query_with_analytics(query)

    print("📝 Answer:")
    print("-" * 60)
    print(result["answer"])
    print("-" * 60)

    if "sources" in result and result["sources"]:
        print("\n📚 Sources:")
        for source in result["sources"]:
            print(f"  - {source['id']} ({source['type']}) - {source.get('provider', 'N/A')}")

    if "retrieved_docs" in result:
        print(f"\n🔍 Retrieved documents: {result['retrieved_docs']}")

    if "usage" in result:
        print(f"\n💰 Token usage: {result['usage']['input_tokens']} input + {result['usage']['output_tokens']} output")


def run_evaluation(embedding_provider: str = "openai"):
    """
    Run evaluation on test queries.

    Args:
        embedding_provider: Embedding provider to use
    """
    print(f"\n{'='*60}")
    print("RUNNING EVALUATIONS")
    print(f"{'='*60}\n")

    generator = ResponseGenerator(embedding_provider=embedding_provider)
    precision_eval = PrecisionEvaluator()
    groundedness_eval = GroundednessEvaluator()

    # Define test queries for RAG evaluation
    # Following RAG Cookbook best practices:
    # - Use semantic queries that require document understanding
    # - Avoid analytical queries (counts, aggregations)
    # - Focus on factual, how-to, and comparison queries
    test_queries = [
        "What is SafetyPay?",
        "How to configure SafetyPay webhooks?",
        "Which providers support PIX in Brazil?",
        "What are the available payment methods with Adyen?"
    ]

    print("Running evaluations on test queries...\n")

    all_precision_scores = []
    all_groundedness_scores = []

    for i, query in enumerate(test_queries, 1):
        print(f"\n[{i}/{len(test_queries)}] Query: {query}")
        print("-" * 60)

        # Get response using smart routing (handles both semantic and analytical queries)
        result = generator.query_with_analytics(query)

        # Check if it's an analytical query (no semantic search needed)
        if result.get("query_type") == "analytical":
            print("ℹ️  Analytical query - skipping precision/groundedness evaluation")
            print(f"   Answer: {result['answer'][:100]}...")
            continue

        if result.get("retrieved_docs", 0) == 0:
            print("⚠️  No documents retrieved, skipping evaluation")
            continue

        # Retrieve context docs for semantic queries
        context_docs = generator.retriever.semantic_search(query, top_k=5)

        # Evaluate Precision
        precision_result = precision_eval.evaluate(query, context_docs)
        all_precision_scores.append(precision_result["precision"])

        print(f"✓ Precision: {precision_result['precision']:.2%} ({precision_result['relevant_count']}/{precision_result['total_retrieved']} relevant)")

        # Evaluate Groundedness
        groundedness_result = groundedness_eval.evaluate(
            query=query,
            generated_answer=result["answer"],
            context_docs=context_docs[:3]  # Use top 3 for efficiency
        )
        all_groundedness_scores.append(groundedness_result["groundedness_score"])

        print(f"✓ Groundedness: {groundedness_result['groundedness_score']:.2f} ({groundedness_result['verdict']})")

    # Print summary
    print(f"\n{'='*60}")
    print("EVALUATION SUMMARY")
    print(f"{'='*60}")

    if all_precision_scores:
        avg_precision = sum(all_precision_scores) / len(all_precision_scores)
        print(f"\n📊 Average Precision: {avg_precision:.2%}")

    if all_groundedness_scores:
        avg_groundedness = sum(all_groundedness_scores) / len(all_groundedness_scores)
        print(f"📊 Average Groundedness: {avg_groundedness:.2f}/1.0")

    print()


def interactive_mode(embedding_provider: str = "openai"):
    """
    Interactive query mode.

    Args:
        embedding_provider: Embedding provider to use
    """
    print(f"\n{'='*60}")
    print("INTERACTIVE MODE")
    print(f"{'='*60}\n")

    print("Type your questions (or 'quit' to exit)\n")

    generator = ResponseGenerator(embedding_provider=embedding_provider)

    while True:
        try:
            query = input("❓ You: ").strip()

            if not query:
                continue

            if query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break

            result = generator.query_with_analytics(query)

            print(f"\n🤖 Assistant:\n{result['answer']}\n")

            if "sources" in result and result["sources"]:
                print("📚 Sources:", ", ".join([s['id'] for s in result['sources']]))
                print()

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Yuno RAG Pipeline - Retrieve and generate answers from company documentation"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest documents into the system")
    ingest_parser.add_argument("data_dir", help="Directory containing PDF files")
    ingest_parser.add_argument("--clear", action="store_true", help="Clear collection before ingesting")
    ingest_parser.add_argument("--embedding-provider", default="openai", choices=["local", "openai", "voyage"],
                              help="Embedding provider to use")

    # Query command
    query_parser = subparsers.add_parser("query", help="Query the system")
    query_parser.add_argument("query", help="Query string")
    query_parser.add_argument("--embedding-provider", default="openai", choices=["local", "openai", "voyage"],
                             help="Embedding provider to use")

    # Eval command
    eval_parser = subparsers.add_parser("eval", help="Run evaluations")
    eval_parser.add_argument("--embedding-provider", default="openai", choices=["local", "openai", "voyage"],
                            help="Embedding provider to use")

    # Interactive command
    interactive_parser = subparsers.add_parser("interactive", help="Interactive query mode")
    interactive_parser.add_argument("--embedding-provider", default="openai", choices=["local", "openai", "voyage"],
                                   help="Embedding provider to use")

    args = parser.parse_args()

    if args.command == "ingest":
        ingest_documents(args.data_dir, args.clear, args.embedding_provider)

    elif args.command == "query":
        query_system(args.query, args.embedding_provider)

    elif args.command == "eval":
        run_evaluation(args.embedding_provider)

    elif args.command == "interactive":
        interactive_mode(args.embedding_provider)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
