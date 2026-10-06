import hashlib
from pathlib import Path

from langchain_community.document_loaders import PyPDFium2Loader
from langchain_core.documents import Document


def parse_pdfs(paths):
    pages = []
    for path in sorted(map(Path, paths), key=lambda p: p.name):
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Only PDF input is supported: {path.name}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        document_id = hashlib.sha256((path.name + ":" + digest).encode()).hexdigest()[:32]
        loaded = PyPDFium2Loader(str(path)).load()
        for index, page in enumerate(loaded, 1):
            text = " ".join(page.page_content.split())
            if not text:
                continue
            pages.append(Document(page_content=text, metadata={"document_id": document_id, "document_sha256": digest,
                                                               "filename": path.name, "page": index, "source_type": "pdf",
                                                               "offset_unit": "normalized_page_character"}))
    if not pages:
        raise ValueError("No extractable PDF text; scanned PDFs require a separate OCR workflow")
    return pages
