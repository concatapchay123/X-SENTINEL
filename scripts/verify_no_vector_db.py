from pathlib import Path

FORBIDDEN = ["pinecone", "qdrant", "weaviate", "milvus", "pgvector"]
for path in Path("backend").rglob("*.py"):
    text = path.read_text(encoding="utf-8").lower()
    hits = [x for x in FORBIDDEN if x in text]
    if hits:
        raise SystemExit(f"Unexpected vector DB dependency in {path}: {hits}")
print("Vector DB applicability guard: PASS")
