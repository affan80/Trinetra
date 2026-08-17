"""Deterministic, provenance-first multimodal intake for Trinetra V1."""

from __future__ import annotations

import io
import mimetypes
import re
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, UnidentifiedImageError

from .schemas import InputKind, Investigation, MediaArtifact

URL_PATTERN = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
HANDLE_PATTERN = re.compile(r"(?<!\w)@[A-Za-z0-9_]{2,30}\b")
DOMAIN_PATTERN = re.compile(r"\b(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b")
CAPITALIZED_PATTERN = re.compile(r"\b[A-Z][A-Za-z0-9-]*(?:\s+[A-Z][A-Za-z0-9-]*)*\b")


def classify_upload(filename: str, content_type: str | None) -> InputKind:
    mime = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    if mime.startswith("image/"):
        return InputKind.IMAGE
    if mime.startswith("video/"):
        return InputKind.VIDEO
    if mime.startswith("audio/"):
        return InputKind.AUDIO
    if mime == "application/pdf" or filename.lower().endswith(".pdf"):
        return InputKind.PDF
    return InputKind.DOCUMENT


class MultimodalIngestor:
    def __init__(self, repository) -> None:
        self.repository = repository

    @staticmethod
    def image_details(content: bytes) -> tuple[tuple[int, int] | None, str | None, dict, list[str]]:
        try:
            with Image.open(io.BytesIO(content)) as image:
                pixels = image.convert("L").resize((8, 8))
                values = list(pixels.getdata())
                average = sum(values) / len(values)
                perceptual_hash = "".join("1" if value >= average else "0" for value in values)
                exif = {str(key): str(value) for key, value in image.getexif().items()}
                return image.size, perceptual_hash, {"format": image.format, "exif": exif}, [
                    "Image dimensions and embedded metadata were extracted.",
                    "EXIF values are unverified metadata, not proof of capture location or time.",
                ]
        except UnidentifiedImageError:
            return None, None, {}, ["The upload could not be decoded as an image."]

    @staticmethod
    def extract_observable_mentions(text: str) -> tuple[list[str], list[str]]:
        values: list[str] = []
        for pattern in (URL_PATTERN, HANDLE_PATTERN, DOMAIN_PATTERN, CAPITALIZED_PATTERN):
            values.extend(pattern.findall(text))
        seen = list(dict.fromkeys(value.strip(".,;:!?") for value in values if value.strip()))
        return seen, [f"Search permitted public sources for: {value}" for value in seen[:20]]

    @staticmethod
    def pdf_text(content: bytes) -> tuple[list[str], dict, list[str]]:
        try:
            import fitz

            with fitz.open(stream=content, filetype="pdf") as document:
                return [page.get_text() for page in document], {"pages": document.page_count}, [
                    "PDF text was extracted directly. Image-only pages require an OCR adapter.",
                ]
        except ImportError:
            return [], {}, ["PDF was preserved; install the configured PDF processor to extract text."]
        except Exception as exc:
            return [], {}, [f"PDF text extraction failed: {type(exc).__name__}."]

    def ingest_file(self, investigation: Investigation, filename: str, content_type: str | None, content: bytes) -> MediaArtifact:
        kind = classify_upload(filename, content_type)
        digest, path = self.repository.save_raw(investigation.id, content, Path(filename).suffix or ".bin")
        dimensions, perceptual_hash, metadata, observations = (None, None, {}, [])
        extracted_text: list[str] = []
        if kind == InputKind.IMAGE:
            dimensions, perceptual_hash, metadata, observations = self.image_details(content)
            observations.append("OCR and vision-model observations require configured local model adapters.")
        elif kind == InputKind.PDF:
            extracted_text, metadata, observations = self.pdf_text(content)
        elif kind == InputKind.DOCUMENT:
            if (content_type or "").startswith("text/"):
                extracted_text = [content.decode("utf-8", errors="replace")]
            else:
                observations.append("Document was preserved; PDF/OCR text extraction requires a configured processor.")
        else:
            observations.append("Media was preserved; ASR/keyframe extraction requires a configured processor.")
        entities, hypotheses = self.extract_observable_mentions("\n".join(extracted_text))
        artifact = MediaArtifact(
            artifact_id=f"MED-{len(self.repository.artifacts[investigation.id]) + 1:04d}",
            investigation_id=investigation.id, input_kind=kind, filename=Path(filename).name,
            mime_type=content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
            size_bytes=len(content), sha256=digest, perceptual_hash=perceptual_hash, dimensions=dimensions,
            metadata=metadata, extracted_text=extracted_text, entities=entities, search_hypotheses=hypotheses,
            observations=observations, original_path=path,
        )
        self.repository.artifacts[investigation.id].append(artifact)
        self.repository.log(investigation.id, "Multimodal Ingestor", f"Preserved {kind.value} input {artifact.filename}")
        return artifact

    def ingest_text(self, investigation: Investigation, text: str, input_kind: InputKind = InputKind.TEXT) -> MediaArtifact:
        content = text.encode("utf-8")
        digest, path = self.repository.save_raw(investigation.id, content, ".txt")
        entities, hypotheses = self.extract_observable_mentions(text)
        artifact = MediaArtifact(
            artifact_id=f"MED-{len(self.repository.artifacts[investigation.id]) + 1:04d}",
            investigation_id=investigation.id, input_kind=input_kind, filename="analyst-input.txt",
            mime_type="text/plain", size_bytes=len(content), sha256=digest, extracted_text=[text],
            entities=entities, search_hypotheses=hypotheses,
            observations=["Text supplied by the analyst; claims remain unverified until supporting evidence is collected."],
            original_path=path,
        )
        self.repository.artifacts[investigation.id].append(artifact)
        self.repository.log(investigation.id, "Multimodal Ingestor", f"Preserved {input_kind.value} input")
        return artifact

    def ingest_url(self, investigation: Investigation, url: str) -> MediaArtifact:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("A public HTTP(S) URL is required")
        domains = ("x.com", "facebook.com", "instagram.com", "youtube.com", "reddit.com", "linkedin.com")
        kind = InputKind.SOCIAL_URL if any(name in parsed.netloc.lower() for name in domains) else InputKind.URL
        return self.ingest_text(investigation, url, kind)
