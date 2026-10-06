"""Gate-off browser smoke test; all new evidence stays in reports/v2."""

import json
import argparse

from playwright.sync_api import sync_playwright

from scripts.check_demo_ui import ask
from scripts.v2.common import REPORTS, ROOT, verify_v1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    args = parser.parse_args()
    verify_v1()
    directory = REPORTS / "demo_screenshots"
    directory.mkdir(parents=True, exist_ok=True)
    records = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.goto(args.url, wait_until="domcontentloaded")
        page.get_by_test_id("stChatInputTextArea").wait_for(timeout=300000)
        mode = page.get_by_test_id("stSelectbox").inner_text()
        answer = ask(page, "How much paid sick leave do employees receive?", "10 working days")
        assert "[S1]" in answer and "Page 1" in answer
        assert "关闭" in answer and "证据门限" in answer, answer
        page.screenshot(path=str(directory / "gate_off_cited_answer.png"), full_page=True)
        records.append({"case": "gate_off_demo_answer", "url": args.url, "selected_mode": mode, "ui_text": answer})
        answer = ask(page, "What is Northstar Labs' 2028 IPO valuation target?", "I couldn't find sufficient evidence")
        assert "关闭" in answer
        page.screenshot(path=str(directory / "gate_off_refusal.png"), full_page=True)
        records.append({"case": "gate_off_prompt_refusal", "ui_text": answer})
        page.get_by_test_id("stRadio").get_by_text("上传 PDF", exact=True).click()
        page.locator('input[type="file"]').set_input_files(str(ROOT / "data/baseline/fictional_handbook.pdf"))
        page.get_by_test_id("stChatInputTextArea").wait_for(timeout=300000)
        answer = ask(page, "How many working days of paid sick leave do employees receive per year?", "10 working days")
        assert "fictional_handbook.pdf" in answer and "Page 1" in answer and "关闭" in answer
        page.screenshot(path=str(directory / "gate_off_uploaded_answer.png"), full_page=True)
        records.append({"case": "gate_off_uploaded_pdf", "ui_text": answer})
        page.get_by_role("button", name="清空聊天记录").click()
        page.wait_for_function("() => document.querySelectorAll('[data-testid=stChatMessage]').length===0", timeout=60000)
        records.append({"case": "clear_history", "passed": True})
        browser.close()
    (REPORTS / "demo_ui_results.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verify_v1()
    print("V2 gate-off demo browser checks passed; V1 unchanged.")


if __name__ == "__main__":
    main()
