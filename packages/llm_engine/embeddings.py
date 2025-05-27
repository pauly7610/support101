from fastembed import TextEmbedding
from langchain_community.embeddings import HuggingFaceEmbeddings

_DEFAULT_EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
_embedding_model_instance = None


def get_huggingface_embedding_model(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
):
    """Return a HuggingFaceEmbeddings model for LangChain integration."""
    return HuggingFaceEmbeddings(model_name=model_name)


# FastEmbed singleton for efficient embedding


def get_fastembed_model(model_name: str = _DEFAULT_EMBED_MODEL_NAME) -> TextEmbedding:
    """Return a singleton FastEmbed model instance."""
    global _embedding_model_instance
    if _embedding_model_instance is None or _embedding_model_instance.model_name != model_name:
        _embedding_model_instance = TextEmbedding(model_name=model_name, max_length=512)
    return _embedding_model_instance
