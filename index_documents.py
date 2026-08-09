"""
index_documents.py – Index a folder of documents into the RAG knowledge base.

Usage:
    python index_documents.py ./my_documents
    python index_documents.py ./my_documents --clear   # wipe DB first
    python index_documents.py ./my_documents --ext .txt .md .py

Supported file types: .txt, .md, .py, .json, .csv
For PDFs install pymupdf: pip install pymupdf
"""

import argparse
import os
import sys
import pymupdf
from tools.rag import RAGTool

SUPPORTED_EXTENSIONS = {".txt", ".md", ".py", ".json", ".csv", ".pdf"}


def read_file(filepath: str) -> str | None:
    ext = os.path.splitext(filepath)[1].lower()

    if ext in {".txt", ".md", ".py", ".json", ".csv"}:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    if ext == ".pdf":
        try:
            doc = pymupdf.open(filepath)
            return "\n".join(page.get_text() for page in doc)
        except ImportError:
            print(f"  [skip] {filepath} – install pymupdf to index PDFs: pip install pymupdf")
            return None

    return None


def index_folder(folder: str, clear: bool, extensions: set[str]):
    rag = RAGTool()

    if clear:
        rag.client.delete_collection("knowledge_base")
        rag.collection = rag.client.get_or_create_collection(
            name="knowledge_base",
            metadata={"hnsw:space": "cosine"}
        )
        print("Knowledge base cleared.\n")

    files = []
    for root, _, filenames in os.walk(folder):
        for filename in filenames:
            if os.path.splitext(filename)[1].lower() in extensions:
                files.append(os.path.join(root, filename))

    if not files:
        print(f"No supported files found in '{folder}'.")
        sys.exit(0)

    print(f"Found {len(files)} file(s) to index...\n")
    success, failed = 0, 0

    for filepath in files:
        text = read_file(filepath)
        if text is None:
            failed += 1
            continue
        if not text.strip():
            print(f"  [skip] {filepath} – empty file")
            failed += 1
            continue

        try:
            result = rag.add_document(text, source=os.path.relpath(filepath, folder))
            print(f"  [ok]   {filepath} – {result['indexed']} chunk(s)")
            success += 1
        except Exception as e:
            print(f"  [err]  {filepath} – {e}")
            failed += 1

    print(f"\nDone. {success} indexed, {failed} skipped/failed.")
    print(f"Total chunks in DB: {rag.collection.count()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index documents into RAG knowledge base.")
    parser.add_argument("folder", help="Path to the folder containing documents.")
    parser.add_argument("--clear", action="store_true", help="Clear the knowledge base before indexing.")
    parser.add_argument("--ext", nargs="+", default=None, help="File extensions to include, e.g. --ext .txt .md")
    args = parser.parse_args()

    extensions = set(args.ext) if args.ext else SUPPORTED_EXTENSIONS

    if not os.path.isdir(args.folder):
        print(f"Error: '{args.folder}' is not a directory.")
        sys.exit(1)

    index_folder(args.folder, args.clear, extensions)
