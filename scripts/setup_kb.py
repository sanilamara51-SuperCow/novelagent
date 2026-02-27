from __future__ import annotations

import argparse
import asyncio
import sys

from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config import load_config
from src.knowledge.data_loader import HistoricalTextLoader
from src.knowledge.text_chunker import ClassicalChineseChunker
from src.knowledge.embedding_service import EmbeddingService
from src.knowledge.rag_retriever import RAGRetriever


TEST_QUERIES = [
    {
        "query": "北魏孝文帝为何迁都洛阳？",
        "keywords": ["孝文帝", "迁都", "洛阳"],
    },
    {
        "query": "太武帝灭佛的原因与影响是什么？",
        "keywords": ["太武帝", "灭佛", "佛"],
    },
    {
        "query": "北魏统一北方的关键战役有哪些？",
        "keywords": ["北魏", "统一", "战"],
    },
    {
        "query": "拓跋珪建立北魏的过程如何？",
        "keywords": ["拓跋珪", "建立", "北魏"],
    },
    {
        "query": "献文帝与孝文帝之间的关系如何？",
        "keywords": ["献文帝", "孝文帝"],
    },
    {
        "query": "北魏与柔然的关系如何发展？",
        "keywords": ["北魏", "柔然"],
    },
    {
        "query": "洛阳伽蓝记中记载的主要寺院有哪些？",
        "keywords": ["洛阳", "伽蓝记", "寺"],
    },
    {
        "query": "太和改制的内容是什么？",
        "keywords": ["太和", "改制"],
    },
    {
        "query": "景明年间的重大事件有哪些？",
        "keywords": ["景明", "年"],
    },
    {
        "query": "孝明帝时期的政治困境是什么？",
        "keywords": ["孝明帝", "政治"],
    },
    {
        "query": "孝庄帝与尔朱氏的冲突发生了什么？",
        "keywords": ["孝庄帝", "尔朱"],
    },
    {
        "query": "北魏的均田制如何实施？",
        "keywords": ["均田制", "北魏"],
    },
    {
        "query": "北魏都城平城的地理位置在哪里？",
        "keywords": ["平城", "都城"],
    },
    {
        "query": "北魏对南朝刘宋的战争有哪些？",
        "keywords": ["北魏", "刘宋", "战争"],
    },
    {
        "query": "太平真君年间发生了什么重大事件？",
        "keywords": ["太平真君", "年"],
    },
    {
        "query": "北魏与高句丽的关系如何？",
        "keywords": ["北魏", "高句丽"],
    },
    {
        "query": "延兴年间有什么政治改革？",
        "keywords": ["延兴", "改革"],
    },
    {
        "query": "洛阳城的城门有哪些记载？",
        "keywords": ["洛阳", "城门"],
    },
    {
        "query": "北魏对鲜卑旧俗进行了哪些变革？",
        "keywords": ["鲜卑", "变革"],
    },
    {
        "query": "宣武帝在位期间有哪些重要政策？",
        "keywords": ["宣武帝", "政策"],
    },
    {
        "query": "正光年间的社会动乱有哪些？",
        "keywords": ["正光", "动乱"],
    },
    {
        "query": "北魏孝文帝的汉化措施包括哪些方面？",
        "keywords": ["孝文帝", "汉化"],
    },
]


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Setup knowledge base for historical texts.")
    parser.add_argument(
        "--raw-dir",
        default="data/knowledge_base/raw",
        help="Path to raw texts directory",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run validation only, do not index",
    )
    return parser


def _select_chunker_strategy(format_type: str, chunker: ClassicalChineseChunker):
    if format_type == "weishu":
        return chunker.chunk_by_biography
    if format_type == "zizhitongjian":
        return chunker.chunk_by_year
    if format_type == "luoyang":
        return chunker.chunk_by_entry
    return chunker.chunk_text


async def _load_and_chunk(raw_dir: str) -> list:
    config = load_config()
    loader = HistoricalTextLoader(raw_dir)
    chunker = ClassicalChineseChunker(
        chunk_size=config.rag.chunk_size,
        chunk_overlap=config.rag.chunk_overlap,
    )

    raw_texts = await asyncio.to_thread(loader.load_all)
    all_chunks = []

    for content, metadata in raw_texts:
        cleaned_text = await asyncio.to_thread(loader.preprocess, content)
        format_type = metadata.get("detected_format", "unknown")
        base_meta = {
            "source": metadata.get("filename", "unknown"),
            "detected_format": format_type,
        }
        base_meta.update(metadata)
        chunk_strategy = _select_chunker_strategy(format_type, chunker)
        chunks = await asyncio.to_thread(chunk_strategy, cleaned_text, base_meta)
        for chunk in chunks:
            chunk.metadata.setdefault("chunk_id", chunk.id)
            chunk.metadata.setdefault("source", base_meta["source"])
        all_chunks.extend(chunks)

    return all_chunks


async def _index_chunks(retriever: RAGRetriever, chunks: list, batch_size: int = 100) -> None:
    if not chunks:
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
    ) as progress:
        task = progress.add_task(
            f"Indexing chunks (0/{len(chunks)})",
            total=len(chunks),
        )
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]
            await asyncio.to_thread(retriever.index_documents, batch, len(batch))
            progress.advance(task, len(batch))
            progress.update(
                task,
                description=f"Indexing chunks ({min(start + len(batch), len(chunks))}/{len(chunks)})",
            )


def _collect_text_for_recall(results: list[dict]) -> str:
    pieces = []
    for result in results:
        text = result.get("text", "")
        metadata = result.get("metadata") or {}
        meta_text = " ".join([f"{k}:{v}" for k, v in metadata.items()])
        pieces.append(f"{text} {meta_text}")
    return " ".join(pieces).lower()


async def _run_validation(retriever: RAGRetriever) -> float:
    recalls = []
    for test_case in TEST_QUERIES:
        query = test_case["query"]
        keywords = test_case["keywords"]
        results = await asyncio.to_thread(retriever.search, query, 5)
        combined_text = _collect_text_for_recall(results)
        matched = sum(1 for keyword in keywords if keyword.lower() in combined_text)
        recall = matched / max(1, len(keywords))
        recalls.append(recall)
        print(f"recall@5={recall:.2f} | query={query}")

    average_recall = sum(recalls) / max(1, len(recalls))
    print(f"average_recall@5={average_recall:.2f}")
    return average_recall


async def _async_main(args: argparse.Namespace) -> int:
    config = load_config()
    embedding_service = EmbeddingService(model_name=config.rag.embedding_model)
    if not hasattr(embedding_service, "embed"):
        embedding_service.embed = embedding_service.embed_texts
    retriever = RAGRetriever(config.rag, embedding_service)

    if args.validate:
        average_recall = await _run_validation(retriever)
        if average_recall < 0.5:
            print("QUALITY GATE FAILED")
            return 1
        print("QUALITY GATE PASSED")
        return 0

    chunks = await _load_and_chunk(args.raw_dir)
    await _index_chunks(retriever, chunks)
    return 0


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()
    return asyncio.run(_async_main(args))


if __name__ == "__main__":
    sys.exit(main())
