from paddleocr import PaddleOCR

class OCRExtractor:
    def __init__(self):
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang="en"
        )

    def extract_text(self, image_path):
        result = self.ocr.ocr(
            image_path,
            cls=True
        )

        texts = []

        for line in result[0]:
            texts.append(line[1][0])

        return " ".join(texts)


if __name__ == "__main__":
    ocr = OCRExtractor()

    text = ocr.extract_text("sample.jpg")

    print(text)