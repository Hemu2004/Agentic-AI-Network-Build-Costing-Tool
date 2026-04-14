"""Ollama LLM client with graceful fallback when Ollama is not running."""
import logging
from config import get_settings

logger = logging.getLogger(__name__)

_ollama_llm = None
_ollama_available = None


def _check_ollama_available() -> bool:
    """Check if Ollama server is reachable and configured model is available."""
    global _ollama_available
    if _ollama_available is not None:
        return _ollama_available
    try:
        import httpx
        s = get_settings()
        base = s.ollama_base_url.rstrip("/")
        r = httpx.get(f"{base}/api/tags", timeout=3.0)
        if r.status_code != 200:
            _ollama_available = False
            return False
        data = r.json()
        models = data.get("models") or []
        want = (s.ollama_model or "llama3.2").strip()
        # Match exact name or name with :tag (e.g. llama3.2:latest)
        has_model = any(
            m.get("name") == want or (m.get("name") or "").startswith(want + ":")
            for m in models
        )
        _ollama_available = has_model
        if not has_model and models:
            logger.debug("Ollama model %r not in list: %s", want, [m.get("name") for m in models])
    except Exception as e:
        logger.debug("Ollama not available: %s", e)
        _ollama_available = False
    return _ollama_available


def is_ollama_available() -> bool:
    """Public check for Ollama availability."""
    return _check_ollama_available()


def get_llm():
    """Return Ollama LLM instance, or None if Ollama is not available."""
    global _ollama_llm
    if not _check_ollama_available():
        return None
    if _ollama_llm is None:
        try:
            from langchain_community.llms import Ollama
            s = get_settings()
            _ollama_llm = Ollama(
                base_url=s.ollama_base_url,
                model=s.ollama_model,
                temperature=0.3,
                num_predict=2048,
            )
        except Exception as e:
            logger.warning("Failed to create Ollama client: %s", e)
            return None
    return _ollama_llm


def get_chat_llm():
    """Return ChatOllama for CrewAI, or None if unavailable."""
    if not _check_ollama_available():
        return None
    try:
        from langchain_community.chat_models import ChatOllama
        s = get_settings()
        return ChatOllama(
            base_url=s.ollama_base_url,
            model=s.ollama_model,
            temperature=0.3,
            num_predict=2048,
        )
    except Exception as e:
        logger.warning("Failed to create ChatOllama: %s", e)
        return None
