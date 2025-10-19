"""Utilities to ingest the TUIR document and build a local vector index."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import List, Sequence, Tuple

import faiss
import pdfplumber
import requests
from sentence_transformers import SentenceTransformer

LOGGER = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PDF_PATH = DATA_DIR / "tuir.pdf"
INDEX_PATH = DATA_DIR / "tuir.faiss"
METADATA_PATH = DATA_DIR / "tuir_metadata.json"
OUTLINE_PATH = DATA_DIR / "tuir_outline.json"

DEFAULT_TUIR_SOURCE_URLS: Tuple[str, ...] = (
    "https://www.finanze.gov.it/export/sites/finanze/.content/Documenti/Varie/TUIR_aggiornato_2024.pdf",
    "https://www.finanze.gov.it/export/sites/finanze/.content/Documenti/Varie/TUIR.pdf",
    "https://www1.finanze.gov.it/upload/tuir.pdf",
)


def _normalize_source_urls(urls: str | Sequence[str] | None) -> List[str]:
    """Return a list of candidate URLs to download the TUIR document from."""

    if urls is None:
        env_value = os.getenv("TUIR_SOURCE_URL", "")
        if env_value:
            env_urls = [candidate.strip() for candidate in env_value.split(",")]
            return [candidate for candidate in env_urls if candidate]
        return list(DEFAULT_TUIR_SOURCE_URLS)

    if isinstance(urls, str):
        return [urls]

    return [candidate for candidate in urls if candidate]

EMBEDDING_MODEL_NAME = os.getenv(
    "TUIR_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)


def ensure_document(
    url: str | Sequence[str] | None = None,
    *,
    force: bool = False,
) -> Path:
    """Ensure the TUIR PDF is available locally.

    Args:
        url: One or multiple candidate URLs for downloading the TUIR PDF. When ``None``
            the function will look at the ``TUIR_SOURCE_URL`` environment variable. It
            accepts either a single URL or a comma separated list. If the environment
            variable is not provided, a set of baked-in defaults is used.
        force: If ``True`` forces a re-download of the document even if it already exists.

    Returns:
        Path to the local PDF file.
    """

    source_urls = _normalize_source_urls(url)
    if not source_urls:
        raise ValueError("No candidate URLs provided to download the TUIR document.")

    if PDF_PATH.exists() and not force:
        LOGGER.debug("TUIR PDF already present at %s", PDF_PATH)
        return PDF_PATH

    errors: List[str] = []
    tmp_path = PDF_PATH.with_suffix(PDF_PATH.suffix + ".download")

    for candidate_url in source_urls:
        LOGGER.info("Downloading TUIR document from %s", candidate_url)
        response = None
        try:
            response = requests.get(candidate_url, stream=True, timeout=120)
            response.raise_for_status()

            with tmp_path.open("wb") as pdf_file:
                for chunk in response.iter_content(chunk_size=1 << 20):
                    if chunk:
                        pdf_file.write(chunk)

            tmp_path.replace(PDF_PATH)
            LOGGER.info("Saved TUIR PDF to %s", PDF_PATH)
            return PDF_PATH
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            errors.append(f"{candidate_url} -> HTTP {status}")
            LOGGER.warning("Failed to download TUIR from %s: %s", candidate_url, exc)
        except requests.RequestException as exc:
            errors.append(f"{candidate_url} -> {exc.__class__.__name__}: {exc}")
            LOGGER.warning("Error downloading TUIR from %s: %s", candidate_url, exc)
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    error_message = ", ".join(errors) or "Unknown error"
    raise RuntimeError(
        "Unable to download the TUIR PDF. Tried the following sources: "
        f"{', '.join(source_urls)}. Last errors: {error_message}"
    )


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract raw text from the PDF using pdfplumber."""

    LOGGER.info("Extracting text from %s", pdf_path)
    text_parts: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            LOGGER.debug("Extracted %d characters from page %d", len(page_text), page_number)
            text_parts.append(page_text)
    full_text = "\n".join(text_parts)
    LOGGER.info("Total characters extracted: %d", len(full_text))
    return full_text


def split_into_sections(text: str) -> List[str]:
    """Split the TUIR text into logical sections.

    The heuristic looks for patterns like "Art. <number>" which appear throughout the
    document. If the pattern is not found, the fallback splits on double new lines.
    """

    import re

    LOGGER.info("Splitting text into sections")
    article_pattern = re.compile(r"(?=\bArt\.\s+\d+)", re.IGNORECASE)
    matches = list(article_pattern.finditer(text))

    if not matches:
        LOGGER.warning("No 'Art.' headings found; splitting on double newlines instead")
        sections = [section.strip() for section in text.split("\n\n") if section.strip()]
        return sections

    sections: List[str] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        if section_text:
            sections.append(section_text)
    LOGGER.info("Identified %d sections", len(sections))
    return sections


def load_embedder(model_name: str = EMBEDDING_MODEL_NAME) -> SentenceTransformer:
    """Load the sentence-transformer embedder with a local cache."""

    LOGGER.info("Loading embedding model: %s", model_name)
    return SentenceTransformer(model_name)


def build_embeddings(
    sections: Sequence[str], embedder: SentenceTransformer
) -> Tuple[faiss.IndexFlatIP, List[dict]]:
    """Create FAISS index and metadata entries for the provided sections."""

    LOGGER.info("Encoding %d sections", len(sections))
    vectors = embedder.encode(list(sections), batch_size=32, show_progress_bar=True)

    index = faiss.IndexFlatIP(vectors.shape[1])
    faiss.normalize_L2(vectors)
    index.add(vectors)

    metadata = [
        {
            "id": idx,
            "text": section,
        }
        for idx, section in enumerate(sections)
    ]

    return index, metadata


def _build_outline(metadata: Sequence[dict]) -> List[dict]:
    """Generate a lightweight outline structure from metadata entries."""

    outline: List[dict] = []
    for item in metadata:
        text = str(item.get("text", ""))
        first_line = "".join(text.splitlines()[:1]).strip()
        title = first_line or f"Sezione {item.get('id')}"
        outline.append(
            {
                "id": str(item.get("id")),
                "title": title,
                "path": title,
                "keywords": [],
                "children": [],
            }
        )
    return outline


def persist_index(index: faiss.IndexFlatIP, metadata: Sequence[dict]) -> None:
    """Persist FAISS index, metadata, and document outline to disk."""

    faiss.write_index(index, str(INDEX_PATH))
    with METADATA_PATH.open("w", encoding="utf-8") as meta_file:
        json.dump(list(metadata), meta_file, ensure_ascii=False, indent=2)

    outline = _build_outline(metadata)
    with OUTLINE_PATH.open("w", encoding="utf-8") as outline_file:
        json.dump(outline, outline_file, ensure_ascii=False, indent=2)

    LOGGER.info(
        "Persisted index to %s, metadata to %s, and outline to %s",
        INDEX_PATH,
        METADATA_PATH,
        OUTLINE_PATH,
    )


def ingest_document(force_download: bool = False) -> None:
    """End-to-end routine to download, parse, embed, and index the TUIR document."""

    pdf_path = ensure_document(force=force_download)
    text = extract_text_from_pdf(pdf_path)
    sections = split_into_sections(text)

    embedder = load_embedder()
    index, metadata = build_embeddings(sections, embedder)
    persist_index(index, metadata)


def load_index() -> Tuple[faiss.IndexFlatIP, List[dict], SentenceTransformer]:
    """Load the FAISS index, metadata, and embedder for querying."""

    if not INDEX_PATH.exists() or not METADATA_PATH.exists():
        raise RuntimeError("Vector index not found. Run ingest_document() first.")

    LOGGER.info("Loading FAISS index from %s", INDEX_PATH)
    index = faiss.read_index(str(INDEX_PATH))
    with METADATA_PATH.open("r", encoding="utf-8") as meta_file:
        metadata = json.load(meta_file)

    embedder = load_embedder()
    return index, metadata, embedder


def load_outline() -> List[dict]:
    """Load the precomputed outline for the TUIR document."""

    if not OUTLINE_PATH.exists():
        raise RuntimeError("Outline not found. Run ingest_document() first.")

    with OUTLINE_PATH.open("r", encoding="utf-8") as outline_file:
        return json.load(outline_file)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingest_document()
