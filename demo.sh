#!/bin/bash
# Demo Script for Yuno RAG Pipeline
# Runs a complete system demonstration

PYTHON="/opt/homebrew/bin/python3.11"

echo "========================================================================"
echo "🎬 DEMO: YUNO RAG PIPELINE"
echo "========================================================================"
echo ""

# Function to pause between queries
pause_demo() {
    echo ""
    echo "Press ENTER to continue..."
    read
    echo ""
}

# 1. System Statistics
echo "========================================================================"
echo "📊 PART 1: System Statistics"
echo "========================================================================"
$PYTHON -c "
from pymongo import MongoClient
from config import MONGODB_URI, MONGODB_DATABASE, MONGODB_COLLECTION

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DATABASE]
collection = db[MONGODB_COLLECTION]

total = collection.count_documents({})
jira = collection.count_documents({'metadata.document_type': 'jira'})
confluence = collection.count_documents({'metadata.document_type': 'confluence'})
tst12 = collection.count_documents({'metadata.source_id': {'\$regex': '^TST12'}})

print(f'✓ Total documents: {total:,}')
print(f'✓ Jira tickets: {jira}')
print(f'✓ Confluence docs: {confluence}')
print(f'✓ TST12 tickets (Integrations): {tst12}')
"

pause_demo

# 2. Query: Ticket Analysis
echo "========================================================================"
echo "🎯 PART 2: TST12 Ticket Analysis"
echo "========================================================================"
echo ""
echo "Query 1: What problem does TST12-1772 describe?"
echo ""
$PYTHON main.py query "What type of problem does ticket TST12-1772 describe and which provider is involved?" --embedding-provider openai

pause_demo

# 3. Query: Provider Identification
echo "Query 2: Which provider is in TST12-1701?"
echo ""
$PYTHON main.py query "Which provider is associated with ticket TST12-1701?" --embedding-provider openai

pause_demo

# 4. Query Multi-Hop: Ticket → Confluence
echo "========================================================================"
echo "🔗 PART 3: Cross-Document Retrieval (Jira → Confluence)"
echo "========================================================================"
echo ""
echo "Query 3: Ticket → Provider → Documentation"
echo ""
$PYTHON main.py query "To resolve ticket TST12-1772, how are redirect URLs configured in Mercado Pago?" --embedding-provider openai

pause_demo

# 5. Query: Technical Documentation
echo "Query 4: Webhook configuration"
echo ""
$PYTHON main.py query "What are the technical steps to configure SafetyPay webhooks?" --embedding-provider openai

pause_demo

# 6. Query: Payment Methods
echo "========================================================================"
echo "📚 PART 4: Provider Documentation"
echo "========================================================================"
echo ""
echo "Query 5: What payment methods does Adyen support in Brazil?"
echo ""
$PYTHON main.py query "What payment methods does Adyen support in Brazil?" --embedding-provider openai

pause_demo

# 7. Query: Providers with PIX
echo "Query 6: Which providers support PIX?"
echo ""
$PYTHON main.py query "Which providers support PIX payments in Brazil?" --embedding-provider openai

pause_demo

# 8. Analytical Queries
echo "========================================================================"
echo "📈 PART 5: Analytical Queries (MongoDB Aggregations)"
echo "========================================================================"
echo ""
echo "Query 7: Ticket counting"
echo ""
$PYTHON main.py query "Which provider has the most reported tickets?" --embedding-provider openai

pause_demo

# 9. Evaluations
echo "========================================================================"
echo "🧪 PART 6: System Evaluations"
echo "========================================================================"
echo ""
$PYTHON main.py eval --embedding-provider openai

pause_demo

# End
echo ""
echo "========================================================================"
echo "✅ DEMO COMPLETED"
echo "========================================================================"
echo ""
echo "System Metrics:"
echo "  - Precision: 55% (semantic queries)"
echo "  - Groundedness: 0.85/1.0"
echo "  - MMR active for diversity"
echo "  - 42 TST12 tickets available"
echo ""
echo "Implemented features:"
echo "  ✓ Ticket classification (simple vs complex)"
echo "  ✓ Provider extraction"
echo "  ✓ Cross-document retrieval (Jira → Confluence)"
echo "  ✓ Smart router (semantic + analytical)"
echo "  ✓ MMR for result diversity"
echo ""
echo "For interactive mode:"
echo "  $PYTHON main.py interactive --embedding-provider openai"
echo ""
