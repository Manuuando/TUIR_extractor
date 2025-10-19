import numpy as np

from backend.ingest import _build_outline, build_embeddings, split_into_sections


def test_split_into_sections_with_articles():
    text = (
        "Art. 1 Primo articolo\nContenuto...\n"
        "Art. 2 Secondo articolo\nAltri dettagli"
    )

    sections = split_into_sections(text)

    assert sections == [
        "Art. 1 Primo articolo\nContenuto...",
        "Art. 2 Secondo articolo\nAltri dettagli",
    ]


def test_split_into_sections_fallback_double_newline():
    text = "Introduzione\n\nSezione intermedia\n\nConclusione"

    sections = split_into_sections(text)

    assert sections == [
        "Introduzione",
        "Sezione intermedia",
        "Conclusione",
    ]


def test_build_embeddings_and_outline():
    sections = [
        "Art. 1 Primo articolo\nContenuto...",
        "Art. 2 Secondo articolo\nAltri dettagli",
    ]

    class DummyEmbedder:
        def encode(self, texts, batch_size=32, show_progress_bar=True):
            assert texts == sections
            return np.array(
                [
                    [1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                ],
                dtype="float32",
            )

    embedder = DummyEmbedder()

    index, metadata = build_embeddings(sections, embedder)

    assert index.ntotal == len(sections)
    assert metadata == [
        {"id": 0, "text": sections[0]},
        {"id": 1, "text": sections[1]},
    ]

    outline = _build_outline(metadata)

    assert outline == [
        {
            "id": "0",
            "title": "Art. 1 Primo articolo",
            "path": "Art. 1 Primo articolo",
            "keywords": [],
            "children": [],
        },
        {
            "id": "1",
            "title": "Art. 2 Secondo articolo",
            "path": "Art. 2 Secondo articolo",
            "keywords": [],
            "children": [],
        },
    ]


