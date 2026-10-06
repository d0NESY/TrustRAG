"""Build authored hard scenarios before running any V2 retrieval model."""

from collections import Counter
from difflib import SequenceMatcher
import hashlib
import random
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import normalize, sha256_file, write_jsonl
from scripts.v2.benchmark_specs import CATEGORIES, FAMILIES
from scripts.v2.common import DATA, REPORTS, verify_v1


def question_template(text):
    text = normalize(text)
    text = re.sub(r"\b[a-z]{2,8}-\d{2,5}\b", "<identifier>", text)
    text = re.sub(r"\b\d+(?:\.\d+)?\b", "<number>", text)
    return text


def tokens(text):
    return set(re.findall(r"\w+", question_template(text)))


def integrity(rows, document_paths):
    dev, test = [row for row in rows if row["split"] == "dev"], [row for row in rows if row["split"] == "test"]
    comparisons = []
    exact = set(normalize(row["question"]) for row in dev) & set(normalize(row["question"]) for row in test)
    template_overlap = set(question_template(row["question"]) for row in dev) & set(question_template(row["question"]) for row in test)
    for left in dev:
        for right in test:
            a, b = question_template(left["question"]), question_template(right["question"])
            similarity = SequenceMatcher(None, a, b).ratio()
            ta, tb = tokens(a), tokens(b)
            jaccard = len(ta & tb) / max(len(ta | tb), 1)
            if similarity >= 0.9 or jaccard >= 0.8:
                comparisons.append({"dev_id": left["id"], "test_id": right["id"], "sequence_similarity": similarity,
                                    "token_jaccard": jaccard, "dev_question": left["question"], "test_question": right["question"]})
    span_dev = {normalize(row["evidence_text"]) for row in dev if row["answerable"]}
    span_test = {normalize(row["evidence_text"]) for row in test if row["answerable"]}
    families_dev, families_test = {row["family_id"] for row in dev}, {row["family_id"] for row in test}
    document_counts = {"total": len(document_paths), "dev_families": len(families_dev), "test_families": len(families_test)}
    result = {"benchmark_version": "meridian-hard-v2.0", "seed": 173, "split_policy": "entire document/policy family assigned before model evaluation",
              "counts": {split: {"total": len(part), "answerable": sum(row["answerable"] for row in part), "unanswerable": sum(not row["answerable"] for row in part),
                                 "categories": dict(Counter(row["category"] for row in part))} for split, part in [("dev", dev), ("test", test)]},
              "document_counts": document_counts, "normalized_question_overlap": sorted(exact), "template_overlap": sorted(template_overlap),
              "family_overlap": sorted(families_dev & families_test), "source_span_overlap": sorted(span_dev & span_test),
              "near_duplicate_checks": {"sequence_threshold": 0.9, "token_jaccard_threshold": 0.8, "pairs": comparisons},
              "question_hashes": {row["id"]: hashlib.sha256(normalize(row["question"]).encode()).hexdigest() for row in rows},
              "source_hashes": {path.relative_to(DATA).as_posix(): sha256_file(path) for path in document_paths},
              "synthetic": True, "gold_authoring": "facts/questions authored together; no LLM gold; independent human validation remains pending"}
    write_json(REPORTS / "benchmark_integrity.json", result)
    if exact or template_overlap or families_dev & families_test or span_dev & span_test or comparisons:
        raise ValueError("Pre-model benchmark integrity failed; inspect reported overlaps before freezing")
    return result


def make_pdf(path, title, status, pages):
    styles = getSampleStyleSheet()
    story = []
    for page_index, paragraphs in enumerate(pages):
        if page_index:
            story.append(PageBreak())
        story.append(Paragraph(title, styles["Heading1"]))
        story.append(Paragraph(status, styles["BodyText"]))
        story.append(Spacer(1, 12))
        for paragraph in paragraphs:
            story.append(Paragraph(paragraph, styles["BodyText"]))
            story.append(Spacer(1, 10))
    SimpleDocTemplate(str(path), pagesize=A4, invariant=1, title=title, author="TrustRAG fictional hard benchmark").build(story)


def main():
    verify_v1()
    manifest_path = DATA / "manifest.json"
    if manifest_path.exists():
        raise ValueError("V2 dataset already built; preserve it and its predictions rather than overwrite gold")
    documents = DATA / "documents"
    sources = DATA / "source_docs"
    documents.mkdir(parents=True, exist_ok=True)
    sources.mkdir(parents=True, exist_ok=True)
    rng = random.Random(173)
    dev_families = set(rng.sample([record["family_id"] for record in FAMILIES], 10))
    rows, facts, document_map = [], [], []
    assert len(FAMILIES) == 30
    for record in FAMILIES:
        assert [row["category"] for row in record["tasks"]] == CATEGORIES
        slug = record["family_id"]
        tasks = record["tasks"]
        main_name, old_name, annex_name = slug + "_operations_2026.pdf", slug + "_archive_2024.pdf", slug + "_reference_annex.pdf"
        identifier = re.search(r"\b([A-Z]{2,8})-(\d{3})\b", tasks[1]["evidence_text"])
        prefix, code = identifier.group(1), int(identifier.group(2))
        # Operational lookup entries add nearby but genuinely distinct identifiers.
        # They do not alter any labelled fact or supply missing negative-question facts.
        registry = [f"Registry {prefix}-{code + offset}: record the request in the pending owner-verification queue; this entry is not the named exception route."
                    for offset in [101, 112, 123, 134, 145, 156, 167, 178]]
        page1 = [f"Scope: {record['scope']}. This is fictional Meridian Works guidance. The following responsibilities apply only to the named activity, not to other procedures with similar labels.",
                 tasks[0]["evidence_text"], tasks[1]["evidence_text"],
                 "The coordinator records what actually happened, identifies the responsible owner and checks the applicable route. A similarly numbered form is not interchangeable with the recorded form. For a rejected submission, retain the original request and obtain corrected evidence rather than creating a replacement event.",
                 *registry[:4]]
        page2 = ["Eligibility and operational limits. Select the named cohort and activity before applying a period or amount; different entitlements in this section are not substitutes.",
                 tasks[2]["evidence_text"], tasks[3]["evidence_text"],
                 "A valid request contains its underlying event date and the scope used for the calculation. Reviewers distinguish acknowledgement, completion and storage periods. A deadline for submitting evidence is not a service restoration promise. If the activity or group is not stated, escalate the question rather than borrowing a nearby rule.",
                 *registry[4:]]
        page3 = ["Document control: this 2026 operating guide is CURRENT and effective from 1 August 2026. The 2024 edition is archived and superseded. No forecast for a later year is stated.",
                 tasks[4]["evidence_text"], record["routing_note"],
                 "The reference annex has its own scope. Staff should distinguish operational permission from commercial price, evidence retention and service specifications. Publication of a code or a process owner does not create a missing technical limit or a financial guarantee.",
                 "Amendment log: this edition consolidates the current timing rule and ownership path. Historical examples remain in the archive for traceability. They are not exceptions to the current rule. A request citing an older edition must be checked against the effective document before execution."]
        old_pages = [["ARCHIVED, SUPERSEDED: this 2024 edition is retained for historical record only and is not the current operating policy.", record["legacy_evidence"],
                      "The old edition covered the same operating activity. Its prior timing must not be treated as a forecast. Historic case records show how approvals were documented at the time; they do not authorise new work under that edition."],
                     ["Historical route register. These entries are examples of administrative queues in the retired edition, not current forms.", *registry[:5]]]
        annex_pages = [[f"Controlling reference for {record['title'].lower()}. {record['routing_note']}", tasks[5]["evidence_text"],
                        "Apply only the activity and conditions named in this annex. An operational guide cannot be used to invent an absent commercial rate, compensation clause or retention term. Where an entity-specific negotiated term is requested, the general policy is not sufficient evidence."]]
        docs = [(main_name, record["title"] + " - operating guide", "CURRENT 2026; effective 1 August 2026", [page1, page2, page3]),
                (old_name, record["title"] + " - historical edition", "ARCHIVED 2024; superseded", old_pages),
                (annex_name, record["title"] + " - reference annex", "CURRENT REFERENCE; named scope only", annex_pages)]
        split = "dev" if slug in dev_families else "test"
        for filename, title, status, pages in docs:
            make_pdf(documents / filename, title, status, pages)
            text = "\n\n".join("\n".join(page) for page in pages)
            (sources / (filename.removesuffix(".pdf") + ".txt")).write_text(title + "\n" + status + "\n\n" + text + "\n", encoding="utf-8", newline="\n")
            document_map.append({"filename": filename, "family_id": slug, "split": split, "status": status, "pages": len(pages)})
        for number, task in enumerate(tasks, 1):
            page = 1 if number <= 2 else (2 if number <= 4 else (3 if number == 5 else 1))
            filename = annex_name if number == 6 else main_name
            sample = {"id": f"v2_{slug}_{task['category']}", "family_id": slug, "split": split, "category": task["category"],
                      "question": task["question"], "answer": task["answer"], "answerable": True,
                      "relevant_documents": [filename], "relevant_pages": [page], "relevant_chunk_ids": [], "evidence_text": task["evidence_text"],
                      "template_signature": question_template(task["question"])}
            rows.append(sample)
            facts.append({"id": sample["id"], "family_id": slug, "filename": filename, "page": page, "evidence_text": task["evidence_text"], "answer": task["answer"]})
        for number, question in enumerate(record["negative_questions"], 1):
            rows.append({"id": f"v2_{slug}_near_miss_{number}", "family_id": slug, "split": split, "category": "near_miss_unanswerable",
                         "question": question, "answer": None, "answerable": False, "relevant_documents": [], "relevant_pages": [],
                         "relevant_chunk_ids": [], "related_documents": [main_name, annex_name], "template_signature": question_template(question)})
    rng.shuffle(rows)
    dev, test = [row for row in rows if row["split"] == "dev"], [row for row in rows if row["split"] == "test"]
    write_jsonl(DATA / "dev.jsonl", dev)
    write_jsonl(DATA / "test.jsonl", test)
    write_jsonl(DATA / "source_facts.jsonl", facts)
    write_json(DATA / "document_families.json", document_map)
    checked = integrity(rows, sorted(documents.glob("*.pdf")))
    manifest = {"version": "meridian-hard-v2.0", "synthetic": True, "seed": 173, "answerable": 180, "unanswerable": 60,
                "split": checked["counts"], "files": {p.relative_to(DATA).as_posix(): sha256_file(p) for p in sorted(DATA.rglob("*")) if p.is_file()},
                "family_policy": "No family split across dev/test; no model-assisted gold; no V2 test tuning."}
    write_json(manifest_path, manifest)
    verify_v1()
    print(f"V2 built before models: {len(dev)} dev, {len(test)} test, {len(document_map)} PDFs, 180 answerable + 60 near-miss questions.")


if __name__ == "__main__":
    main()
