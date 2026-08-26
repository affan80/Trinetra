from langdetect import detect


class LanguageDetector:

    def detect_language(self, text):

        try:
            return detect(text)

        except:
            return "unknown"


if __name__ == "__main__":

    detector = LanguageDetector()

    text = "Drone activity detected"

    print(
        detector.detect_language(text)
    )