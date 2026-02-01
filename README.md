# Yuno RAG Pipeline 🚀

RAG (Retrieval-Augmented Generation) pipeline specialized for Yuno technical documentation, a fintech payments platform in Latin America.

## 📋 Table of Contents

- [Description](#description)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Evaluations](#evaluations)
- [Project Structure](#project-structure)

---

## 📖 Description

This system enables:

1. **Document ingestion** from Jira and Confluence (PDFs)
2. **Intelligent metadata extraction**:
   - Document type (Jira/Confluence)
   - Responsible team (Integrations, Core, Postmortem, Feature Request)
   - Mentioned payment provider (SafetyPay, etc.)
   - Specific metadata (status, priority, dates, etc.)
3. **Hybrid search**:
   - Semantic search with vector embeddings
   - Metadata filtering (team, provider, type)
   - Analytical queries (count tickets, group by provider)
4. **Response generation** using Claude Sonnet 4.5
5. **Automatic evaluation** of Precision and Groundedness

### Use Cases

- "How many integration tickets are there?"
- "Which provider has the most reported tickets?"
- "Give me information about ticket AP-541"
- "Which providers support PIX?"
- "How to configure SafetyPay?"

---

## 🏗️ Architecture

### RAG Pattern: Metadata-Filtered RAG

**Advantages:**
- Efficient filtering by document type, team, provider
- Semantic search + structured filters
- Analytical queries (aggregations)
- Cross-document retrieval (relates Jira with Confluence)

### Components

```
┌─────────────────┐
│   PDF Files     │ (Jira + Confluence)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   INGESTION     │
│  - PDF Loading  │
│  - Metadata     │ ← Claude extracts provider name
│    Extraction   │
│  - Chunking     │
│  - Embeddings   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  MongoDB Atlas  │ (Vector Store + Metadata)
│  Vector Search  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   RETRIEVAL     │
│  - Semantic     │
│  - Filters      │
│  - Analytics    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   GENERATION    │ ← Claude Sonnet 4.5
│  (Anthropic)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   EVALUATION    │
│  - Precision    │
│  - Groundedness │
└─────────────────┘
```

### Extracted Metadata

**Jira Tickets:**
```json
{
  "document_type": "jira",
  "source_id": "AP-541",
  "team": "Feature Request",
  "provider_name": "SafetyPay",
  "status": "Done",
  "priority": "High",
  "assignee": "Marlon Andres Barreto Tejada",
  "created_date": "2025-11-06",
  "chunk_index": 0
}
```

**Confluence Pages:**
```json
{
  "document_type": "confluence",
  "source_id": "3702794",
  "provider_name": "SafetyPay",
  "space": "Integrations Teams",
  "version": "77",
  "created_by": "Juan Manuel Rebull",
  "created_date": "2022-03-03",
  "chunk_index": 0
}
```

---

## 🛠️ Installation

### Prerequisites

- Python 3.10+
- MongoDB Atlas account
- Anthropic API key

### Step 1: Clone repository

```bash
cd yuno-rag-pipeline
```

### Step 2: Install dependencies

```bash
pip install -r requirements.txt
```

**Note about embeddings:**

The system supports 3 embedding options:

1. **Local (default)** - Free, no API key required
   ```bash
   pip install sentence-transformers
   ```

2. **OpenAI** - Recommended for production
   ```bash
   pip install openai
   ```

3. **Voyage AI** - Recommended by Anthropic
   ```bash
   pip install voyageai
   ```

---

## ⚙️ Configuration

### Step 1: Configure environment variables

Copy the sample file:

```bash
cp .env.sample .env
```

Edit `.env`:

```bash
# Anthropic API (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-xxxxx

# MongoDB Atlas (REQUIRED)
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DATABASE=yuno_rag
MONGODB_COLLECTION=documents

# OpenAI (OPTIONAL - only if using OpenAI embeddings)
OPENAI_API_KEY=sk-xxxxx

# Voyage AI (OPTIONAL - only if using Voyage embeddings)
VOYAGE_API_KEY=pa-xxxxx
```

### Step 2: Configure MongoDB Atlas Vector Search

**Option A: Use client-side search (no configuration needed)**

The system works out-of-the-box by calculating cosine similarity on the client.

**Option B: Configure Vector Search Index (recommended for production)**

1. Go to your cluster in MongoDB Atlas
2. Click on "Atlas Search"
3. Create a new Search Index with the following configuration:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 384,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "metadata.document_type"
    },
    {
      "type": "filter",
      "path": "metadata.team"
    },
    {
      "type": "filter",
      "path": "metadata.provider_name"
    },
    {
      "type": "filter",
      "path": "metadata.source_id"
    }
  ]
}
```

**Note:** `numDimensions` depends on the embedding model:
- Local (sentence-transformers): 384
- OpenAI (text-embedding-3-small): 1536
- Voyage (voyage-2): 1024

---

## 🚀 Usage

### 1. Ingest Documents

```bash
# Using local embeddings (default)
python main.py ingest ../rag-knowledge-base/data

# Clear collection before ingesting
python main.py ingest ../rag-knowledge-base/data --clear

# Using OpenAI embeddings
python main.py ingest ../rag-knowledge-base/data --embedding-provider openai
```

**Expected output:**
```
Processing PDFs: 100%|████████████| 78/78
Successfully processed 78/78 documents

Collection Statistics:
{
  "total_documents": 892,
  "jira_documents": 245,
  "confluence_documents": 647,
  "teams": {
    "Integrations": 85,
    "Core": 98,
    "Feature Request": 42,
    "Postmortem": 20
  },
  "providers": {
    "SafetyPay": 15,
    "MercadoPago": 8,
    ...
  }
}
```

### 2. Run Queries

```bash
# Simple query
python main.py query "What is SafetyPay?"

# Analytical query
python main.py query "How many integration tickets are there?"

# Ticket-specific query
python main.py query "Give me information about ticket AP-541"

# Capabilities query
python main.py query "Which providers support PIX?"
```

**Example response:**

```
❓ Query: What is SafetyPay?

📝 Answer:
------------------------------------------------------------
SafetyPay is a non-card payment method that operates the largest
bank network in Latin America. It has presence in 16 countries
with 380 banking partners and 180,000 payment points...
------------------------------------------------------------

📚 Sources:
  - 3702794 (confluence) - SafetyPay
  - AP-541 (jira) - N/A

🔍 Retrieved documents: 5

💰 Token usage: 2451 input + 187 output
```

### 3. Interactive Mode

```bash
python main.py interactive
```

```
Type your questions (or 'quit' to exit)

❓ You: Which providers support PIX?

🤖 Assistant:
According to the documentation, SafetyPay supports PIX in Brazil through
its PIX_SAFETYPAY payment method...

📚 Sources: 3702794, 3702815

❓ You: quit
👋 Goodbye!
```

### 4. Run Evaluations

```bash
python main.py eval
```

**Output:**

```
RUNNING EVALUATIONS
============================================================

[1/4] Query: What is SafetyPay?
------------------------------------------------------------
✓ Precision: 80.00% (4/5 relevant)
✓ Groundedness: 0.95 (GROUNDED)

[2/4] Query: How to configure SafetyPay webhooks?
------------------------------------------------------------
✓ Precision: 100.00% (5/5 relevant)
✓ Groundedness: 1.00 (GROUNDED)

...

============================================================
EVALUATION SUMMARY
============================================================

📊 Average Precision: 85.00%
📊 Average Groundedness: 0.92/1.0
```

---

## 📊 Evaluations

### Precision (Retrieval)

**What it measures:** Of all retrieved documents, how many are relevant?

**Formula:** `Precision = Relevant Documents / Total Retrieved`

**Implementation:**
- Uses Claude to judge relevance of each retrieved document
- Compares content with user query
- Score: 0.0 to 1.0 (higher is better)

**Example:**

```python
from evals.precision import PrecisionEvaluator

evaluator = PrecisionEvaluator()
result = evaluator.evaluate(
    query="How to configure SafetyPay?",
    retrieved_docs=documents
)

print(f"Precision: {result['precision']:.2%}")
# Output: Precision: 80.00% (4/5 relevant)
```

### Groundedness (Generation)

**What it measures:** Is the generated answer fully grounded in the context?

**Prevents:** Model hallucinations

**Implementation:**
- Uses Claude to verify that each claim in the answer can be traced to the context
- Verdict: GROUNDED, PARTIALLY_GROUNDED, NOT_GROUNDED
- Score: 0.0 to 1.0

**Example:**

```python
from evals.groundedness import GroundednessEvaluator

evaluator = GroundednessEvaluator()
result = evaluator.evaluate(
    query="What is SafetyPay?",
    generated_answer="SafetyPay operates in 16 countries...",
    context_docs=documents
)

print(f"Groundedness: {result['groundedness_score']:.2f}")
print(f"Verdict: {result['verdict']}")
# Output: Groundedness: 0.95 (GROUNDED)
```

---

## 📁 Project Structure

```
yuno-rag-pipeline/
├── config.py                 # Centralized configuration
├── main.py                   # Main script
├── requirements.txt          # Dependencies
├── .env.sample              # Configuration template
├── README.md                # This documentation
│
├── ingestion/               # Ingestion module
│   ├── __init__.py
│   ├── document_processor.py  # Processes PDFs and stores
│   └── embeddings.py          # Generates embeddings
│
├── retrieval/               # Retrieval module
│   ├── __init__.py
│   └── retriever.py          # Hybrid search + filters
│
├── generation/              # Generation module
│   ├── __init__.py
│   └── generator.py          # Generates responses with Claude
│
├── evals/                   # Evaluation module
│   ├── __init__.py
│   ├── precision.py          # Precision eval
│   └── groundedness.py       # Groundedness eval
│
└── utils/                   # Utilities
    ├── __init__.py
    ├── metadata_extractor.py  # Extracts metadata from docs
    └── pdf_loader.py          # Loads PDFs
```

---

## 🎯 Design Decisions

### Why Metadata-Filtered RAG?

1. **Predictable structure** - Jira and Confluence have well-defined metadata
2. **Analytical queries** - You need to count, group, filter
3. **Cross-document** - Relate tickets with documentation
4. **Performance** - Filters reduce search space

### Why Claude Sonnet 4.5?

1. **Large context window** - 200K tokens (can handle multiple documents)
2. **Instruction following** - Excellent for structured queries
3. **Native Spanish** - Your documentation is in Spanish
4. **Groundedness** - Less prone to hallucination

### Why MongoDB Atlas?

1. **Vector search + filters** - Hybrid search in a single query
2. **Flexible schema** - Metadata varies by document type
3. **Scalable** - Can grow with your data
4. **Managed service** - No need to maintain infrastructure

---

## 🔧 Troubleshooting

### Error: "No module named 'sentence_transformers'"

```bash
pip install sentence-transformers
```

### Error: "ANTHROPIC_API_KEY not found"

Make sure to:
1. Create `.env` file in the project root
2. Add `ANTHROPIC_API_KEY=sk-ant-xxxxx`
3. Don't share this file (it's in .gitignore)

### Error: "Connection to MongoDB failed"

Verify:
1. MongoDB URI in `.env` is correct
2. Your IP is in MongoDB Atlas whitelist
3. Username/password are correct

### Embeddings are slow

If using local embeddings and it's too slow:
1. Consider using OpenAI embeddings (faster)
2. Or process documents in smaller batches

---

## 📹 Explanatory Video

(You will record a 3-5 minute video explaining:)

1. **Architecture** (1 min)
   - Pipeline diagram
   - Why Metadata-Filtered RAG

2. **Demo** (2 min)
   - Ingest documents
   - Run queries
   - Show results

3. **Evals** (1 min)
   - Run evaluations
   - Explain results

4. **Tradeoffs** (1 min)
   - Design advantages
   - Known limitations

---

## 🤝 Contributing

To add more features:

1. **New metadata types** - Edit `utils/metadata_extractor.py`
2. **New query patterns** - Edit `generation/generator.py`
3. **New evaluations** - Create file in `evals/`

---

## 📝 License

Internal Yuno project.

---

## 🙏 References

- [RAG Cookbook](https://github.com/anthropics/rag-cookbook) - Pattern inspiration
- [LangChain Documentation](https://python.langchain.com/)
- [MongoDB Vector Search](https://www.mongodb.com/products/platform/atlas-vector-search)
- [Anthropic Claude](https://www.anthropic.com/claude)

---
