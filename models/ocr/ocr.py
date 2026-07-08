from pathlib import Path
from paddleocr import PaddleOCR


class OCRExtractor:
    def __init__(self):
        self.ocr = PaddleOCR(lang="en")

    def extract_text(self, image_path):
        result = self.ocr.predict(image_path)

        texts = []

        if len(result) > 0:
            res = result[0]

            if "rec_texts" in res:
                texts = res["rec_texts"]

        final_text = "\n".join(texts)

        # Save output
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "output.txt"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_text)

        return final_text


if __name__ == "__main__":
    ocr = OCRExtractor()

    text = ocr.extract_text("sample.jpg")

    print(text)