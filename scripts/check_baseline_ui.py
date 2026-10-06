"""Exercise a real Streamlit upload and three real upstream model responses."""

import argparse
import json
from pathlib import Path
import time

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = [
    ("explicit", "How many working days of paid sick leave do employees receive per year?"),
    ("semantic", "If I catch the flu and cannot work, how many paid days can I take off?"),
    ("unanswerable", "What is the company's 2028 IPO valuation target?"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    parser.add_argument("--upload-only", action="store_true")
    args = parser.parse_args()
    output = ROOT / ".runtime" / "baseline" / "ui"
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
        page.locator('input[type="file"]').set_input_files(str(ROOT / "data" / "baseline" / "fictional_handbook.pdf"))
        page.get_by_test_id("stChatInputTextArea").wait_for(timeout=600000)
        page.screenshot(path=str(output / "uploaded.png"), full_page=True)
        if args.upload_only:
            print("Real PDF upload, parsing, index construction and chat UI succeeded.", flush=True)
            browser.close()
            return
        for index, (kind, question) in enumerate(QUESTIONS):
            started = time.perf_counter()
            textbox = page.get_by_test_id("stChatInputTextArea")
            textbox.fill(question)
            textbox.press("Enter")
            page.wait_for_function("count => document.querySelectorAll('[data-testid=stChatMessage]').length >= count", arg=2 * index + 3, timeout=600000)
            page.wait_for_function("() => { const messages = document.querySelectorAll('[data-testid=stChatMessage]'); return messages.length && messages[messages.length-1].innerText.includes('Source #1'); }", timeout=600000)
            # A source expander is rendered only after the async generation loop ends.
            answer = page.get_by_test_id("stChatMessage").last.inner_text()
            screenshot = output / f"question_{index + 1}.png"
            page.screenshot(path=str(screenshot), full_page=True)
            result = {"kind": kind, "question": question, "ui_answer_with_sources": answer, "latency_seconds": time.perf_counter() - started, "screenshot": screenshot.name}
            results.append(result)
            (output / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
            print(json.dumps(result), flush=True)
        browser.close()


if __name__ == "__main__":
    main()
