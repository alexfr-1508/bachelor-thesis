import os
import requests
import chromadb

OLLAMA_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"  # ollama pull nomic-embed-text
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "knowledge_base"
CHUNK_SIZE = 500        # characters per chunk
CHUNK_OVERLAP = 50      # overlap between chunks to preserve context
TOP_K = 3              # number of chunks to retrieve per query


def _get_embedding(text: str) -> list[float]:
    """Get embedding vector from Ollama."""
    response = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBEDDING_MODEL, "input": text},
        timeout=30
    )
    response.raise_for_status()
    return response.json()["embeddings"][0]


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


class RAGTool:
    def __init__(self, chroma_path: str = CHROMA_PATH, top_k: int = TOP_K):
        self.top_k = top_k
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    # ------------------------------------------------------------------ #
    # Indexing via setup script                                          #
    # ------------------------------------------------------------------ #

    def add_document(self, text: str, source: str = "unknown"):
        """Chunk a document and add all chunks to the vector store."""
        chunks = _chunk_text(text)
        for i, chunk in enumerate(chunks):
            embedding = _get_embedding(chunk)
            doc_id = f"{source}_{i}"
            self.collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"source": source, "chunk": i}]
            )
        return {"indexed": len(chunks), "source": source}

    def add_file(self, filepath: str):
        """Read a .txt file and index it."""
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        return self.add_document(text, source=os.path.basename(filepath))

    # ------------------------------------------------------------------ #
    # Retrieval                                  #
    # ------------------------------------------------------------------ #

    def search_knowledge_base(self, query: str, request: str = ""):
        """Search the local knowledge base and return the most relevant passages."""
        if self.collection.count() == 0:
            return {"results": [], "info": "Knowledge base is empty."}

        try:
            query_embedding = _get_embedding(query)
        except Exception as e:
            return {"error": f"Embedding failed: {e}"}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(self.top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"]
        )

        passages = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            passages.append({
                "content": doc,
                "source": meta.get("source", "unknown"),
                "relevance_score": round(1 - dist, 4)  # cosine: 1=identical, 0=unrelated
            })

        return {"results": passages}

    def return_tool_schema(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge_base",
                    "description": (
                        "Searches the local knowledge base for relevant passages. "
                        "Use this when the question might be answered by stored documents."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to find relevant passages."
                            },
                            "request": {
                                "type": "string",
                                "description": "Reason for searching the knowledge base."
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    def get_tools(self):
        return {
            "search_knowledge_base": self.search_knowledge_base
        }
