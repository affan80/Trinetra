import cv2
from ocr import OCRExtractor

class VideoOCR:

    def __init__(self):
        self.ocr = OCRExtractor()

    def process_video(self, video_path):

        cap = cv2.VideoCapture(video_path)

        extracted_text = []

        frame_count = 0

        while True:

            ret, frame = cap.read()

            if not ret:
                break

            if frame_count % 30 == 0:

                frame_path = f"temp_{frame_count}.jpg"

                cv2.imwrite(
                    frame_path,
                    frame
                )

                text = self.ocr.extract_text(
                    frame_path
                )

                extracted_text.append(text)

            frame_count += 1

        cap.release()

        return "\n".join(extracted_text)


if __name__ == "__main__":

    video_ocr = VideoOCR()

    text = video_ocr.process_video(
        "sample.mp4"
    )

    print(text)