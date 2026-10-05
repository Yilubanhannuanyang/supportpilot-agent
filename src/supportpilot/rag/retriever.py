import json
from datetime import datetime
from pathlib import Path
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import chromadb

from supportpilot.observability.tracer import get_current_trace_id


CHROMA_PATH = "data/chroma"
COLLECTION_NAME = "supportpilot_knowledge"
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"

# distance 越小通常表示语义越相关
MAX_DISTANCE = 0.50

# RAG 检索日志保存路径
LOG_PATH = Path("data/logs/rag_retrieval.jsonl")


def log_retrieval(
    query: str,
    source: str,
    distance: float,
    passed: bool,
) -> None:
    """记录每一次知识库检索结果。"""

    LOG_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    record = {
        "timestamp": datetime.now().isoformat(),
        "trace_id": get_current_trace_id(),  # OPT-013：串起三个日志的链路 ID
        "query": query,
        "source": source,
        "distance": distance,
        "passed": passed,
    }

    with LOG_PATH.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(
                record,
                ensure_ascii=False,
            )
            + "\n"
        )


def search_knowledge_base(
    query: str,
    top_k: int = 3,
) -> list[dict]:
    """从 ChromaDB 中检索与问题最相关的知识片段。"""

    client = chromadb.PersistentClient(
        path=CHROMA_PATH,
    )

    embedding_function = SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL,
)

    collection = client.get_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_function,
)

    results = collection.query(
        query_texts=[query], # type: ignore
        n_results=top_k,
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    matches = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):
        passed = distance <= MAX_DISTANCE

        print(
            f"[Retriever] distance={distance:.4f}, "
            f"source={metadata['source']}, "
            f"passed={passed}"
        )

        log_retrieval(
            query=query,
            source=metadata["source"],
            distance=distance,
            passed=passed,
        )

        if not passed:
            continue

        matches.append(
            {
                "content": document,
                "source": metadata["source"],
                "distance": distance,
            }
        )

    return matches


if __name__ == "__main__":
    question = input("请输入问题：")

    results = search_knowledge_base(question)

    if not results:
        print("\n未找到足够相关的知识库内容。")

    else:
        print("\n检索结果：\n")

        for index, result in enumerate(
            results,
            start=1,
        ):
            print("=" * 50)
            print(f"Top {index}")
            print("来源：", result["source"])
            print("距离：", result["distance"])
            print("内容：")
            print(result["content"])
            print()