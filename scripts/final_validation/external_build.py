"""Faithful PDF conversion of public natural excerpts and native SQuAD2 gold."""

import json
import re
from xml.sax.saxutils import escape
import pypdfium2 as pdfium
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import normalize, sha256_file, write_jsonl, validate_benchmark
from scripts.final_validation.common import ROOT, OUT, prepare, verify_frozen


def sentence_span(context, answer):
    start, end = answer["answer_start"], answer["answer_start"] + len(answer["text"])
    if context[start:end] != answer["text"]:
        raise ValueError("Native answer offsets do not match source; preserve failed source rather than invent gold")
    left = max(context.rfind(". ", 0, start), context.rfind("? ", 0, start), context.rfind("! ", 0, start))
    left = left + 2 if left >= 0 else 0
    candidates = [position + 1 for mark in [". ", "? ", "! "] if (position := context.find(mark, end)) >= 0]
    return context[left:min(candidates) if candidates else len(context)]


def main():
    prepare()
    directory = OUT / "external"
    manifest_path = directory / "dataset_manifest.json"
    if manifest_path.exists():
        raise ValueError("External test already frozen; do not regenerate or revise gold")
    source = directory / "squad_v2_dev.json"
    provenance = json.loads((directory / "download_provenance.json").read_text(encoding="utf-8"))
    if sha256_file(source) != provenance["sha256"]:
        raise ValueError("Downloaded natural source changed")
    documents = directory / "documents"
    documents.mkdir(exist_ok=True)
    pdfmetrics.registerFont(TTFont("ExternalArial", "C:/Windows/Fonts/arial.ttf"))
    heading = ParagraphStyle("heading", fontName="ExternalArial", fontSize=16, leading=20, spaceAfter=12)
    body = ParagraphStyle("body", fontName="ExternalArial", fontSize=11, leading=16)
    note = ParagraphStyle("note", fontName="ExternalArial", fontSize=8, leading=11, textColor="#555555")
    samples, records = [], []
    for article in json.loads(source.read_text(encoding="utf-8"))["data"]:
        eligible = [(number, paragraph) for number, paragraph in enumerate(article["paragraphs"])
                    if sum(not q["is_impossible"] for q in paragraph["qas"]) >= 3 and sum(q["is_impossible"] for q in paragraph["qas"]) >= 2]
        if not eligible:
            continue
        paragraph_index, paragraph = eligible[0]
        title, context = article["title"], paragraph["context"]
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
        filename = slug + "_squad2_excerpt.pdf"
        path = documents / filename
        story = [Paragraph(escape(title.replace("_", " ")), heading),
                 Paragraph("Public Wikipedia excerpt supplied by SQuAD2.0; native paragraph " + str(paragraph_index) + ".", note),
                 Spacer(1, 14), Paragraph(escape(context), body), Spacer(1, 18),
                 Paragraph("Source: rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json. Text faithfully converted for the unchanged PDF pipeline; no new policy or facts authored.", note)]
        SimpleDocTemplate(str(path), pagesize=A4, rightMargin=48, leftMargin=48, topMargin=48, bottomMargin=48,
                          title=title, author="Wikipedia contributors / SQuAD2", invariant=1).build(story)
        pdf = pdfium.PdfDocument(path)
        extracted = []
        for page in pdf:
            textpage = page.get_textpage()
            extracted.append(textpage.get_text_range())
            textpage.close()
            page.close()
        pdf.close()
        if normalize(context) not in normalize(" ".join(extracted)):
            raise ValueError(f"Natural source not faithfully preserved after conversion: {title}")
        chosen = [q for q in paragraph["qas"] if not q["is_impossible"]][:3] + [q for q in paragraph["qas"] if q["is_impossible"]][:2]
        for q in chosen:
            positive = not q["is_impossible"]
            answer = q["answers"][0] if positive else None
            evidence = sentence_span(context, answer) if positive else None
            pages = [number + 1 for number, text in enumerate(extracted) if evidence and normalize(evidence) in normalize(text)]
            if positive and not pages:
                raise ValueError("Native gold sentence was not preserved on a PDF page")
            samples.append({"id": q["id"], "family_id": slug, "category": "native_answerable" if positive else "native_unanswerable",
                            "question": q["question"], "answerable": positive, "answer": answer["text"] if positive else None,
                            "evidence_text": evidence, "relevant_documents": [filename] if positive else [],
                            "relevant_pages": pages, "relevant_chunk_ids": [], "native_answers": q["answers"],
                            "native_plausible_answers": q.get("plausible_answers", []), "native_title": title,
                            "native_paragraph_index": paragraph_index, "native_annotation_scope": "individual supplied paragraph"})
        records.append({"title": title, "filename": filename, "paragraph_index": paragraph_index, "context": context,
                        "source_context_sha256": __import__("hashlib").sha256(context.encode()).hexdigest(), "pages": len(extracted)})
        if len(records) == 15:
            break
    if len(records) != 15 or len(samples) != 75:
        raise ValueError("Expected 15 natural excerpts and 75 original crowd-authored questions")
    validate_benchmark(samples)
    write_jsonl(directory / "questions.jsonl", samples)
    write_json(directory / "source_contexts.json", records)
    manifest = {"source_url": provenance["url"], "source_sha256": provenance["sha256"], "documents": 15, "questions": 75,
                "answerable": 45, "unanswerable": 30, "natural_source_text": True, "synthetic_qa": False,
                "human_gold_source": "SQuAD2 native crowd annotations; not this project's independent human audit",
                "selection": "First 15 native-order articles; first paragraph per article with >=3 answerable and >=2 impossible; first 3 positive and 2 negative QA in native order. No length/score/performance filter.",
                "scope_caveat": "Excerpts rather than full Wikipedia articles; impossible labels originally paragraph-scoped; global multi-document validity remains unreviewed. Public set may be in model pretraining.",
                "zero_retuning": True, "config_sha256": sha256_file(ROOT / "configs/v2/dense_reranker.yaml"),
                "files": {p.relative_to(directory).as_posix(): sha256_file(p) for p in sorted(documents.glob("*.pdf"))},
                "questions_sha256": sha256_file(directory / "questions.jsonl"), "contexts_sha256": sha256_file(directory / "source_contexts.json")}
    write_json(manifest_path, manifest)
    verify_frozen()
    print("External frozen before inference: 15 natural excerpts, 45 answerable + 30 native impossible QA; no retuning.")


if __name__ == "__main__":
    main()
