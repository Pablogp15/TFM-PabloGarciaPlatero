"""Codificador E5 local, cargado una vez y ejecutado exclusivamente en CPU."""

from typing import Any


class LocalEmbeddings:
    def __init__(self, model_path: str) -> None:
        from sentence_transformers import SentenceTransformer

        self.model: Any = SentenceTransformer(model_path, device="cpu", local_files_only=True)

    def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
        prefix = "query: " if query else "passage: "
        encoded = self.model.encode(
            [prefix + text for text in texts],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        values: list[list[float]] = encoded.tolist()
        if any(len(vector) != 384 for vector in values):
            raise ValueError("El modelo debe producir vectores de 384 dimensiones")
        return values

    def split(self, text: str, size: int = 300, overlap: int = 50) -> list[str]:
        if not 0 <= overlap < size <= 450:
            raise ValueError("Tamaño o solapamiento fuera de los límites")
        tokenizer = self.model.tokenizer
        tokens = tokenizer.encode(text, add_special_tokens=False)
        chunks = []
        for start in range(0, len(tokens), size - overlap):
            chunks.append(tokenizer.decode(tokens[start : start + size], skip_special_tokens=True))
            if start + size >= len(tokens):
                break
        return chunks
