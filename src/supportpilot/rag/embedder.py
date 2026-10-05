from sentence_transformers import SentenceTransformer

from supportpilot.rag.chunker import build_chunks


MODEL_NAME = "BAAI/bge-small-zh-v1.5"


def create_embedding_model():
    return SentenceTransformer(MODEL_NAME)


def embed_chunks():
    chunks = build_chunks()

    model = create_embedding_model()

    texts = [chunk["content"] for chunk in chunks]

    embeddings = model.encode(texts)

    return chunks, embeddings


if __name__ == "__main__":
    chunks, embeddings = embed_chunks()

    print(f"Chunk 数量：{len(chunks)}")
    print(f"Embedding 数量：{len(embeddings)}")
    print(f"单个向量维度：{len(embeddings[0])}")

    print("\n第一个 Chunk：")
    print(chunks[0]["content"])

    print("\n第一个 Embedding 前 15 个数字：")
    print(embeddings[0][:15])