import time
from functools import lru_cache
from typing import Any, Dict, Tuple

from modules.models import load_embeddings, load_llm
from modules.rag.chains import build_generator, build_grader, build_rewriter
from modules.rag.graph import CRAGWorkflow
from modules.retrieval.vector_store import create_vector_store
from modules.settings import RETRIEVAL_K, SIMILARITY_THRESHOLD


@lru_cache(maxsize=1)
def get_retriever():
    embeddings = load_embeddings()
    store = create_vector_store(embeddings, force_rebuild=False)
    if store is None:
        raise RuntimeError("Could not create or load vector store. Check the Data directory and path configuration.")

    return store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": RETRIEVAL_K, "score_threshold": SIMILARITY_THRESHOLD},
    )


def clear_retriever() -> None:
    get_retriever.cache_clear()


def rebuild_store() -> str:
    started = time.perf_counter()
    clear_retriever()
    embeddings = load_embeddings()
    store = create_vector_store(embeddings, force_rebuild=True)
    if store is None:
        raise RuntimeError("Could not rebuild vector store. Check the Data directory and uploaded sources.")
    clear_retriever()
    elapsed = time.perf_counter() - started
    return f"Vector store rebuilt in {elapsed:.1f}s. The next question will use the refreshed index."


def build_workflow():
    llm = load_llm()
    workflow = CRAGWorkflow(
        retriever=get_retriever(),
        grader_chain=build_grader(llm),
        rewriter_chain=build_rewriter(llm),
        generator_chain=build_generator(llm),
    )
    return workflow.compile()


def answer_question(question: str) -> Tuple[Dict[str, Any], float]:
    started = time.perf_counter()
    graph = build_workflow()
    result = graph.invoke({"question": question, "documents": [], "generation": ""})
    return result, time.perf_counter() - started


# Backward-compatible names for older imports.
get_cached_retriever = get_retriever
clear_cached_retriever = clear_retriever
clear_retriever_cache = clear_retriever
rebuild_vector_store = rebuild_store
rebuild_vector_db = rebuild_store
build_crag_workflow = build_workflow
build_graph = build_workflow
answer_question_with_workflow = answer_question
invoke_question = answer_question