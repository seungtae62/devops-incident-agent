# Quick Start: Switch to File-Based RAG

## File based vectors unless you don't have an qdrant infrastructure

```
src/file_rag/              # New file-based RAG module
├── __init__.py
├── embeddings.py          # Azure OpenAI embeddings
├── vector_store.py        # File-based vector search (replaces Qdrant)
└── retriever.py           # Document retriever using files

data/
├── export_to_files.py     # Script to export Qdrant → JSON (if you have Qdrant)
└── vectors/               # Will contain exported data
    ├── incidents.json     # (create in step 1)
    └── runbooks.json      # (create in step 1)
```

---

## Setup

### Step 1: Export Data
```bash
python data/export_to_files.py
```

### Step 2: Modify 2 Files

#### File 1: `src/agents/supervisor.py`
```python
# Change this:
from src.rag.retriever import DocumentRetriever

# To this:
from src.file_rag.retriever import DocumentRetriever
```

#### File 2: `streamlit_app.py`
```python
# Change this:
from src.rag.retriever import DocumentRetriever

# To this:
from src.file_rag.retriever import DocumentRetriever
```

### Step 3: Test and Run application
```bash
# Run tests
pytest test/

# Run app
streamlit run streamlit_app.py
```
