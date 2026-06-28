from __future__ import annotations

from webclip.models import Document


def render_document_json(document: Document) -> str:
    return document.model_dump_json(indent=2, exclude_none=True)

