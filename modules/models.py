# utils.py
import hashlib
import math
import os
import re
from typing import List, Tuple

from modules.settings import (
    EMBEDDING_MODEL_NAME,
    LLM_API_PROVIDERS,
    LLM_FALLBACK_MODEL,
    LLM_FALLBACK_PROVIDER,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_PROVIDER_CHAIN,
)


class HashingEmbeddingBackend:
    """Small offline fallback embedding model for demos when HuggingFace is unavailable."""

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def _embed(self, text: str) -> List[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"\w+", (text or "").lower(), flags=re.UNICODE)
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8", errors="ignore")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)


def load_embeddings():
    if os.getenv("EMBEDDING_BACKEND", "huggingface").strip().lower() == "hashing":
        print("[INIT] Using offline hashing embeddings.")
        return HashingEmbeddingBackend()

    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError as exc:
        print(f"[WARNING] HuggingFace embeddings unavailable: {exc}")
        print("[INIT] Falling back to offline hashing embeddings.")
        return HashingEmbeddingBackend()

    print(f"[INIT] Loading Embedding Model: {EMBEDDING_MODEL_NAME}...")
    try:
        model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            # model_kwargs={'device': 'cuda'},
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        model.embed_query("health check")
        return model
    except Exception as exc:
        print(f"[WARNING] HuggingFace embeddings failed: {exc}")
        print("[INIT] Falling back to offline hashing embeddings.")
        return HashingEmbeddingBackend()


def _providers() -> List[str]:
    providers = [LLM_PROVIDER] + LLM_PROVIDER_CHAIN
    if LLM_FALLBACK_PROVIDER:
        providers.append(LLM_FALLBACK_PROVIDER)

    chain = []
    for provider in providers:
        provider = provider.strip().lower()
        if provider and provider not in chain:
            chain.append(provider)
    return chain


def _model_name(provider: str) -> str:
    if provider not in LLM_API_PROVIDERS:
        raise ValueError(f"Unsupported LLM provider '{provider}'.")

    provider_cfg = LLM_API_PROVIDERS[provider]
    provider_model = os.getenv(provider_cfg["model_env"], "").strip()
    if provider_model:
        return provider_model

    if provider == LLM_PROVIDER and LLM_MODEL:
        return LLM_MODEL
    if provider == LLM_FALLBACK_PROVIDER and LLM_FALLBACK_MODEL:
        return LLM_FALLBACK_MODEL

    raise ValueError(
        f"Missing model config for LLM provider '{provider}'. "
        f"Set {provider_cfg['model_env']} in .env."
    )
def _chat_model(provider: str, max_tokens: int, model_override: str = None):
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise RuntimeError("Missing dependency 'langchain-openai'. Run: pip install -r requirements.txt") from exc

    if provider not in LLM_API_PROVIDERS:
        raise ValueError(f"Unsupported LLM provider '{provider}'.")

    provider_cfg = LLM_API_PROVIDERS[provider]
    api_key = os.getenv(provider_cfg["api_key_env"], "").strip()
    if not api_key:
        print(f"[WARNING] Skip provider '{provider}' because {provider_cfg['api_key_env']} is not set.")
        return None

    model_to_use = model_override or _model_name(provider)
    kwargs = {
        "model": model_to_use,
        "api_key": api_key,
        "temperature": 0,
        "max_tokens": max_tokens,
        "timeout": float(os.getenv("LLM_TIMEOUT_SECONDS", "25")),
        "max_retries": int(os.getenv("LLM_MAX_RETRIES", "2")),
    }

    if provider_cfg["base_url"]:
        kwargs["base_url"] = provider_cfg["base_url"]

    if provider == "openrouter":
        kwargs["default_headers"] = {
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "Agentic-CRAG"),
        }

    return ChatOpenAI(**kwargs)


def _api_llm(max_tokens: int, purpose: str):
    configured_models: List[Tuple[str, str, object]] = []
    for provider in _providers():
        try:
            model_name = _model_name(provider)
            model = _chat_model(provider, max_tokens=max_tokens)
            if model is not None:
                configured_models.append((provider, model_name, model))

            # Load provider-specific fallback model (e.g. GROQ_FALLBACK_MODEL)
            fallback_var = f"{provider.upper()}_FALLBACK_MODEL"
            fallback_model = os.getenv(fallback_var, "").strip()
            if fallback_model and fallback_model != model_name:
                fb_inst = _chat_model(provider, max_tokens=max_tokens, model_override=fallback_model)
                if fb_inst is not None:
                    configured_models.append((f"{provider}-fallback", fallback_model, fb_inst))
        except Exception as exc:
            print(f"[WARNING] Skip provider '{provider}': {exc}")
            continue

    if not configured_models:
        providers = ", ".join(_providers()) or "<empty>"
        raise RuntimeError(f"No usable API LLM providers configured. Checked: {providers}")

    provider_summary = ", ".join(f"{provider}:{model}" for provider, model, _ in configured_models)
    print(f"[INIT] Using API {purpose} LLM provider chain: {provider_summary}")

    primary = configured_models[0][2]
    fallbacks = [model for _, _, model in configured_models[1:]]
    return primary.with_fallbacks(fallbacks) if fallbacks else primary
def load_llm():
    return _api_llm(max_tokens=2048, purpose="generation")


def load_judge():
    return _api_llm(max_tokens=256, purpose="judge")
# Backward-compatible names for older imports.
HashingEmbeddings = HashingEmbeddingBackend
load_embedding_backend = load_embeddings
load_embedding_model = load_embeddings
load_generation_model = load_llm
load_llm_model = load_llm
load_evaluation_model = load_judge
load_judge_model = load_judge