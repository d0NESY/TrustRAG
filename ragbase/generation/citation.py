from dataclasses import asdict, dataclass
import re

PATTERN = re.compile(r"\[(S\d+)\]")


@dataclass(frozen=True)
class Source:
    source_id: str
    chunk_id: str
    document_id: str
    filename: str
    page: int
    text: str
    context_start_index: int
    context_end_index: int
    context_clipped: bool

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class CitationValidation:
    valid: bool
    cited_ids: list[str]
    invalid_ids: list[str]
    duplicate_count: int
    missing: bool


def validate_citations(answer, available_ids):
    all_ids = PATTERN.findall(answer)
    ids = list(dict.fromkeys(all_ids))
    invalid = [identity for identity in ids if identity not in set(available_ids)]
    return CitationValidation(bool(ids) and not invalid, ids, invalid, len(all_ids) - len(ids), not bool(ids))


def make_sources(results, top_k=5, char_budget=1024):
    if char_budget <= 0:
        raise ValueError("Source context budget must be positive")
    sources, seen = [], set()
    for result in results:
        if result.chunk_id in seen:
            continue
        seen.add(result.chunk_id)
        text = result.text[:char_budget]
        if len(text) < len(result.text) and " " in text:
            text = text.rsplit(" ", 1)[0]
        start = result.metadata["start_index"]
        sources.append(Source(f"S{len(sources) + 1}", result.chunk_id, result.document_id, result.metadata["filename"],
                              result.metadata["page"], text, start, start + len(text), len(text) < len(result.text)))
        if len(sources) == top_k:
            break
    return sources


def format_sources(sources):
    return "\n\n".join(f"[{source.source_id}]\nDocument: {source.filename}\nPage: {source.page}\nContent: {source.text}" for source in sources)
