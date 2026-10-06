"""Render every converted natural-document page for visual QA."""

import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from scripts.final_validation.common import OUT


def main():
    directory = OUT / "external/previews"
    directory.mkdir(exist_ok=True)
    cards = []
    for path in sorted((OUT / "external/documents").glob("*.pdf")):
        pdf = pdfium.PdfDocument(path)
        for number, page in enumerate(pdf, 1):
            rendered = page.render(scale=1.4).to_pil().convert("RGB")
            rendered.save(directory / f"{path.stem}_page{number}.png")
            rendered.thumbnail((390, 550))
            card = Image.new("RGB", (410, 590), "#dce2e9")
            card.paste(rendered, (10, 28))
            ImageDraw.Draw(card).text((10, 8), path.stem[:42] + f" p{number}", fill="black")
            cards.append(card)
            page.close()
        pdf.close()
    for start in range(0, len(cards), 6):
        canvas = Image.new("RGB", (1230, 1180), "white")
        for position, card in enumerate(cards[start:start + 6]):
            canvas.paste(card, ((position % 3) * 410, (position // 3) * 590))
        canvas.save(directory / f"contact_sheet_{start // 6 + 1}.png")
    print(f"All {len(cards)} real-source conversion pages rendered for QA.")


if __name__ == "__main__":
    main()
