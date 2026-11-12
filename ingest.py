import chromadb
from sentence_transformers import SentenceTransformer
from mock_chunks import MOCK_CHUNKS

client = chromadb.PersistentClient(path="./chroma_store")
collection = client.get_or_create_collection(name="ip_sakti_mock")

model = SentenceTransformer("all-MiniLM-L6-v2")

def ingest():
    ids = [c.chunk_id for c in MOCK_CHUNKS]
    texts = [c.text for c in MOCK_CHUNKS]

    # exclude_none drops formulation_relevance entirely for chunks that
    # omitted it, instead of sending None or [] — Chroma rejects both.
    metadatas = [c.metadata.model_dump(exclude_none=True) for c in MOCK_CHUNKS]

    embeddings = model.encode(texts).tolist()

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    print(f"Ingested {collection.count()} chunks into '{collection.name}'.")

if __name__ == "__main__":
    ingest()