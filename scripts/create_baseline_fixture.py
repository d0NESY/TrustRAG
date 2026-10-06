"""Create an openly synthetic PDF for the upstream three-question smoke test."""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, PageBreak


PAGES = [
    ("Employee handbook", [
        "This is a fictional company policy for software testing. It contains no real employee information.",
        "Employees receive 10 working days of paid sick leave per calendar year. Sick leave covers illness, including influenza, and medical recovery. Employees should inform their manager before the start of a missed shift.",
        "Employees receive 20 working days of annual vacation. Up to 5 unused vacation days can be carried into the next year. Carried days expire on March 31.",
    ]),
    ("Expense policy", [
        "Domestic business travel uses economy class flights. The domestic meal reimbursement limit is USD 35 per person per day. Itemized receipts are required for reimbursement.",
        "Employees must submit expense claims within 30 calendar days of the purchase. The Finance team reviews complete claims within 7 business days.",
    ]),
    ("IT security", [
        "Company laptops must use AES-256 full disk encryption. Multi-factor authentication is required for remote access. Employees must report a lost company device to the IT team within 2 hours.",
        "Passwords must contain at least 14 characters. Security incidents are reported through the internal helpdesk. This policy does not include company valuation, IPO plans, or future stock prices.",
    ]),
]


def main():
    output = Path(__file__).resolve().parents[1] / "data" / "baseline" / "fictional_handbook.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    story = []
    for index, (title, paragraphs) in enumerate(PAGES):
        if index:
            story.append(PageBreak())
        story.append(Paragraph(title, styles["Title"]))
        story.append(Spacer(1, 20))
        for paragraph in paragraphs:
            story.append(Paragraph(paragraph, styles["BodyText"]))
            story.append(Spacer(1, 16))
    SimpleDocTemplate(str(output), pagesize=A4).build(story)
    print(output)


if __name__ == "__main__":
    main()
