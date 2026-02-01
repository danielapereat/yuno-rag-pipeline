# Yuno RAG Pipeline - Step by Step Guide 🚀

A hands-on guide for running the Yuno RAG Pipeline from ingestion to evaluation.

---

## Quick Start

```bash
# 1. Setup environment
python3.11 -m pip install -r requirements.txt

# 2. Configure API keys (create .env file)
cp .env.sample .env
# Edit .env with your keys

# 3. Verify MongoDB connection
python3.11 -c "from pymongo import MongoClient; from config import MONGODB_URI; client = MongoClient(MONGODB_URI); print('✓ MongoDB connected'); print(f'✓ Databases: {client.list_database_names()}')"

# 4. Ingest documents
python3.11 main.py ingest ../rag-knowledge-base/data --clear --embedding-provider openai

# 5. Run a test query
python3.11 main.py query "What is SafetyPay?" --embedding-provider openai

# 6. Run evaluations
python3.11 main.py eval --embedding-provider openai

# 7. Interactive mode
python3.11 main.py interactive --embedding-provider openai
```

---

## Prerequisites

### 1. Check Python version

```bash
python3.11 --version
# Expected: Python 3.11.x
```

If not installed:
```bash
# macOS
brew install python@3.11

# Linux
sudo apt install python3.11
```

### 2. Check OpenSSL version

```bash
python3.11 -c "import ssl; print(ssl.OPENSSL_VERSION)"
# Expected: OpenSSL 3.x or higher (required for MongoDB Atlas)
```

### 3. Verify dependencies

```bash
python3.11 -m pip install -r requirements.txt
```

---

## Step 1: Configuration

### Create .env file

```bash
cp .env.sample .env
```

Edit `.env` with your credentials:

```env
# Required
OPENAI_API_KEY=sk-xxxxx
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/

# Optional
MONGODB_DATABASE=yuno_rag
MONGODB_COLLECTION=documents
VECTOR_INDEX_NAME=vector_index
CHUNK_SIZE=1500
CHUNK_OVERLAP=300
TOP_K=5
```

### Test MongoDB connection

```bash
python3.11 -c "
from pymongo import MongoClient
from config import MONGODB_URI, MONGODB_DATABASE

client = MongoClient(MONGODB_URI)
print('✓ MongoDB connected')
print(f'✓ Database: {MONGODB_DATABASE}')
print(f'✓ Collections: {client[MONGODB_DATABASE].list_collection_names()}')
"
```

Expected output:
```
✓ MongoDB connected
✓ Database: yuno_rag
✓ Collections: ['documents']
```

---

## Step 2: Ingestion

### Ingest all documents

```bash
python3.11 main.py ingest ../rag-knowledge-base/data --embedding-provider openai
```

Expected output:
```
============================================================
INGESTING DOCUMENTS
============================================================

Initialized OpenAI embeddings with model: text-embedding-3-small
📂 Processing documents from: ../rag-knowledge-base/data
Found 120 PDF files to process
Processing PDFs: 100%|██████████| 120/120 [16:50<00:00,  8.42s/it]

Successfully processed 120/120 documents

📊 Collection Statistics:
{
  "total_documents": 3228,
  "jira_documents": 257,
  "confluence_documents": 2971,
  "teams": {
    "Integraciones": 65,
    "Core": 39,
    "Postmortem": 111,
    "Feature Request": 29,
    "Demand": 13
  },
  "providers": {
    "SafetyPay": 58,
    "Stripe": 599,
    "Adyen": 118,
    "MercadoPago": 148,
    ...
  }
}
```

### Clear and re-ingest

```bash
python3.11 main.py ingest ../rag-knowledge-base/data --clear --embedding-provider openai
```

### Check database statistics

```bash
python3.11 -c "
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
print(f'✓ TST12 tickets (Integraciones): {tst12}')
"
```

---

## Step 3: Queries

### Simple semantic queries

```bash
# Query 1: Provider information
python3.11 main.py query "What is SafetyPay?" --embedding-provider openai

# Query 2: Technical documentation
python3.11 main.py query "How to configure SafetyPay webhooks?" --embedding-provider openai

# Query 3: Payment methods
python3.11 main.py query "What payment methods does Adyen support in Brazil?" --embedding-provider openai

# Query 4: Provider capabilities
python3.11 main.py query "Which providers support PIX in Brazil?" --embedding-provider openai
```

### Ticket-specific queries (TST12)

```bash
# Query 5: Ticket analysis
python3.11 main.py query "What type of problem does ticket TST12-1772 describe and which provider is involved?" --embedding-provider openai

# Query 6: Provider identification
python3.11 main.py query "Which provider is associated with ticket TST12-1701?" --embedding-provider openai
```

### Multi-hop queries (Ticket → Confluence)

```bash
# Query 7: Cross-document retrieval
python3.11 main.py query "To resolve ticket TST12-1772, how are redirect URLs configured in Mercado Pago?" --embedding-provider openai
```

### Analytical queries (MongoDB aggregations)

```bash
# Query 8: Count tickets by team
python3.11 main.py query "How many integration tickets are there?" --embedding-provider openai

# Query 9: Group by provider
python3.11 main.py query "Which provider has the most reported tickets?" --embedding-provider openai
```

### Expected query output

```
============================================================
QUERY
============================================================

❓ Query: What is SafetyPay?

📝 Answer:
------------------------------------------------------------
SafetyPay is a non-card payment method that operates the largest
bank network in Latin America. It has presence in 16 countries
with 380 banking partners and 180,000 payment points...
------------------------------------------------------------

📚 Retrieved documents: 5
  - Source: 3702794 (confluence) - SafetyPay
  - Source: AP-541 (jira) - Feature Request

💰 Token usage: 2451 input + 187 output
```

---

## Step 4: Evaluations

### Run full evaluation suite

```bash
python3.11 main.py eval --embedding-provider openai
```

Expected output:
```
============================================================
RUNNING EVALUATIONS
============================================================

Test Queries:
  1. What is SafetyPay?
  2. How to configure SafetyPay webhooks?
  3. What payment methods does Adyen support in Brazil?
  4. Which providers support PIX in Brazil?
  5. How many integration tickets are there?

------------------------------------------------------------
[1/5] Query: What is SafetyPay?
------------------------------------------------------------
✓ Precision: 80.00% (4/5 relevant)
✓ Groundedness: 0.95 (GROUNDED)

[2/5] Query: How to configure SafetyPay webhooks?
------------------------------------------------------------
✓ Precision: 100.00% (5/5 relevant)
✓ Groundedness: 1.00 (GROUNDED)

...

============================================================
EVALUATION SUMMARY
============================================================

📊 Average Precision: 55.00%
📊 Average Groundedness: 0.85/1.0

Target metrics (production):
  - Precision: 60-70%
  - Groundedness: >0.80
```

### Run individual evaluations

```bash
# Precision only
python3.11 -c "
from evals.precision import PrecisionEvaluator
from retrieval.retriever import Retriever

retriever = Retriever(embedding_provider='openai')
evaluator = PrecisionEvaluator()

query = 'What is SafetyPay?'
docs = retriever.semantic_search(query, top_k=5)

result = evaluator.evaluate(query, docs)
print(f'Precision: {result[\"precision\"]:.2%}')
print(f'Relevant: {result[\"relevant_count\"]}/{result[\"total_count\"]}')
"

# Groundedness only
python3.11 -c "
from evals.groundedness import GroundednessEvaluator
from retrieval.retriever import Retriever
from generation.generator import Generator

retriever = Retriever(embedding_provider='openai')
generator = Generator()
evaluator = GroundednessEvaluator()

query = 'What is SafetyPay?'
result = generator.query(query, top_k=5)

groundedness = evaluator.evaluate(
    query=query,
    generated_answer=result['answer'],
    context_docs=result['retrieved_docs']
)
print(f'Groundedness: {groundedness[\"groundedness_score\"]:.2f}')
print(f'Verdict: {groundedness[\"verdict\"]}')
"
```

---

## Step 5: Interactive Mode

### Start interactive session

```bash
python3.11 main.py interactive --embedding-provider openai
```

Example session:
```
============================================================
INTERACTIVE MODE
============================================================

Type your questions (or 'quit' to exit)

❓ You: Which providers support PIX?

🤖 Assistant:
------------------------------------------------------------
According to the documentation, the following providers support PIX:
1. SafetyPay (PIX_SAFETYPAY)
2. MercadoPago
3. Stripe
4. Adyen
------------------------------------------------------------

📚 Sources: 3702794, 3702815, AP-541

❓ You: How to configure SafetyPay webhooks?

🤖 Assistant:
------------------------------------------------------------
To configure SafetyPay webhooks:

1. Create endpoint on your server: POST /webhooks/safetypay
2. Configure URL in SafetyPay dashboard
3. Validate HMAC-SHA256 signature with secret key
4. Process events: payment.success, payment.failed, refund.completed
------------------------------------------------------------

📚 Sources: 3702794, AP-541

❓ You: quit

👋 Goodbye!
```

---

## Step 6: Demo Script

### Run automated demo

```bash
chmod +x demo.sh
./demo.sh
```

The demo script includes:
1. **System Statistics** - Document counts by team and provider
2. **Ticket Analysis** - TST12 ticket queries
3. **Cross-Document Retrieval** - Jira → Confluence linking
4. **Technical Documentation** - Provider configuration queries
5. **Analytical Queries** - MongoDB aggregations
6. **Evaluations** - Full evaluation suite

### Manual demo commands

```bash
# Part 1: Statistics
python3.11 -c "
from pymongo import MongoClient
from config import MONGODB_URI, MONGODB_DATABASE, MONGODB_COLLECTION

client = MongoClient(MONGODB_URI)
collection = client[MONGODB_DATABASE][MONGODB_COLLECTION]

print(f'Total documents: {collection.count_documents({}):,}')
print(f'Jira tickets: {collection.count_documents({\"metadata.document_type\": \"jira\"})}')
print(f'TST12 tickets: {collection.count_documents({\"metadata.source_id\": {\"\$regex\": \"^TST12\"}})}')
"

# Part 2: Ticket analysis
python3.11 main.py query "What type of problem does ticket TST12-1772 describe?" --embedding-provider openai

# Part 3: Provider documentation
python3.11 main.py query "How are redirect URLs configured in Mercado Pago?" --embedding-provider openai

# Part 4: Analytical query
python3.11 main.py query "Which provider has the most reported tickets?" --embedding-provider openai

# Part 5: Evaluations
python3.11 main.py eval --embedding-provider openai
```

---

## Troubleshooting

### SSL/TLS Error

```bash
# Check OpenSSL version
python3.11 -c "import ssl; print(ssl.OPENSSL_VERSION)"

# If LibreSSL 2.8.3, upgrade Python to 3.11+
brew install python@3.11
```

### MongoDB Connection Error

```bash
# Test connection
python3.11 -c "
from pymongo import MongoClient
from config import MONGODB_URI

try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    client.server_info()
    print('✓ Connected')
except Exception as e:
    print(f'✗ Error: {e}')
"

# Common fixes:
# 1. Check IP whitelist in MongoDB Atlas
# 2. Verify MONGODB_URI in .env
# 3. Test network connectivity
```

### httpx Version Conflict

```bash
# Fix httpx version
pip3.11 install httpx==0.27.2
```

### No documents in database

```bash
# Check if ingestion completed
python3.11 -c "
from pymongo import MongoClient
from config import MONGODB_URI, MONGODB_DATABASE, MONGODB_COLLECTION

client = MongoClient(MONGODB_URI)
count = client[MONGODB_DATABASE][MONGODB_COLLECTION].count_documents({})

if count == 0:
    print('⚠️  No documents found - run ingestion')
    print('python3.11 main.py ingest ../rag-knowledge-base/data --embedding-provider openai')
else:
    print(f'✓ Found {count:,} documents')
"
```

---

## System Metrics

Current performance (as of latest evaluation):

| Metric | Value | Target |
|--------|-------|--------|
| **Precision** | 55% | 60-70% |
| **Groundedness** | 0.85/1.0 | >0.80 |
| **Total Documents** | 3,228 | - |
| **TST12 Tickets** | 65 | - |
| **Providers** | 40+ | - |
| **Avg Query Time** | ~2-3s | <5s |

Features implemented:
- ✅ Ticket classification (simple vs complex)
- ✅ Provider extraction from documents
- ✅ Cross-document retrieval (Jira → Confluence)
- ✅ Query routing (semantic + analytical)
- ✅ MMR for result diversity (lambda=0.7)
- ✅ Metadata-filtered search
- ✅ Precision & Groundedness evaluation

---

## Next Steps

To improve precision from 55% to 60-70%:

1. **Implement Hybrid Search** (BM25 + Vector + RRF)
   ```bash
   # Reference: rag-cookbook/03-hybrid-search/
   # Combines keyword search with semantic search
   ```

2. **Add reranking** with cross-encoder
   ```bash
   # Post-retrieval reranking for better relevance
   ```

3. **Query expansion** with synonyms/paraphrasing
   ```bash
   # Generate multiple query variations
   ```

4. **Contextual chunking** with document structure
   ```bash
   # Preserve heading context in chunks
   ```

---

## Project Structure

```
yuno-rag-pipeline/
├── STEP_BY_STEP.md         # This guide
├── README.md               # Project overview
├── demo.sh                 # Automated demo script
├── main.py                 # CLI entry point
├── config.py               # Configuration
├── requirements.txt        # Dependencies
│
├── ingestion/             # Document processing
│   ├── document_processor.py
│   └── embeddings.py
│
├── retrieval/             # Search & filtering
│   └── retriever.py
│
├── generation/            # Answer generation
│   └── generator.py
│
├── evals/                 # Evaluation metrics
│   ├── precision.py
│   └── groundedness.py
│
└── utils/                 # Utilities
    ├── metadata_extractor.py
    └── pdf_loader.py
```

---

## Resources

- [RAG Cookbook](https://github.com/anthropics/rag-cookbook) - Pattern reference
- [MongoDB Vector Search](https://www.mongodb.com/docs/atlas/atlas-vector-search/) - Setup guide
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings) - API docs

---

