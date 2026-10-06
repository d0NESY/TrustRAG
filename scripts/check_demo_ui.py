"""Real browser checks for the finished local UI, including isolated uploads."""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def ask(page, question, expected):
    messages = page.get_by_test_id("stChatMessage").count()
    textbox = page.get_by_test_id("stChatInputTextArea")
    textbox.fill(question)
    textbox.press("Enter")
    page.wait_for_function("count => document.querySelectorAll('[data-testid=stChatMessage]').length >= count", arg=messages + 2, timeout=300000)
    page.wait_for_function("() => { const nodes=document.querySelectorAll('[data-testid=stChatMessage]'); return nodes.length && nodes[nodes.length-1].innerText.includes('Sources / 来源'); }", timeout=300000)
    answer = page.get_by_test_id("stChatMessage").last.inner_text()
    assert expected in answer, answer
    return answer


def main():
    output = ROOT / "docs/demo_screenshots"
    output.mkdir(parents=True, exist_ok=True)
    records = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.goto("http://127.0.0.1:8501", wait_until="domcontentloaded")
        page.get_by_test_id("stChatInputTextArea").wait_for(timeout=300000)
        answer = ask(page, "How much paid sick leave do employees receive?", "10 working days")
        assert "[S1]" in answer and "Page 1" in answer
        page.screenshot(path=str(output / "demo_answer.png"), full_page=True)
        records.append({"case": "demo_cited_answer", "ui_text": answer})
        answer = ask(page, "What is Northstar Labs' 2028 IPO valuation target?", "I couldn't find sufficient evidence")
        page.screenshot(path=str(output / "demo_refusal.png"), full_page=True)
        records.append({"case": "demo_refusal", "ui_text": answer})
        page.get_by_test_id("stRadio").get_by_text("上传 PDF", exact=True).click()
        page.locator('input[type="file"]').set_input_files(str(ROOT / "data/baseline/fictional_handbook.pdf"))
        page.get_by_test_id("stChatInputTextArea").wait_for(timeout=300000)
        answer = ask(page, "How many working days of paid sick leave do employees receive per year?", "10 working days")
        assert "fictional_handbook.pdf" in answer and "Page 1" in answer
        page.screenshot(path=str(output / "uploaded_answer.png"), full_page=True)
        records.append({"case": "uploaded_pdf_cited_answer", "ui_text": answer})
        page.get_by_role("button", name="清空聊天记录").click()
        page.wait_for_function("() => document.querySelectorAll('[data-testid=stChatMessage]').length===0", timeout=60000)
        records.append({"case": "clear_history", "passed": True})
        browser.close()
    (ROOT / "docs/demo_ui_results.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print("Real TrustRAG UI passed: cited demo answer, refusal, actual PDF upload, page/source rendering and reset.")


if __name__ == "__main__":
    main()
