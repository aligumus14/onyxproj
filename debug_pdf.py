import chromadb

DB_PATH = "./vector_db"
COLLECTION_NAME = "company_docs"

def main():
    client = chromadb.PersistentClient(path=DB_PATH)
    col = client.get_collection(name=COLLECTION_NAME)

    print("count:", col.count())

    sample = col.get(limit=5, include=["documents", "metadatas", "embeddings"])
    embs = sample.get("embeddings")

    # embeddings bazen [[...],[...]] veya None dönebilir
    has_any = False
    emb_shapes = []
    if embs:
        for e in embs:
            if e is None:
                emb_shapes.append(None)
            else:
                has_any = True
                emb_shapes.append(len(e))

    print("embeddings_present:", bool(embs) and has_any)
    print("embedding_lengths:", emb_shapes)

    # Bir de ilk dokümanı göster
    docs = sample.get("documents", [])
    metas = sample.get("metadatas", [])
    for i in range(min(3, len(docs))):
        src = (metas[i] or {}).get("source", "BILINMEYEN") if isinstance(metas, list) else "?"
        print(f"\n[{i}] source={src}")
        print((docs[i] or "")[:250])

if __name__ == "__main__":
    main()
