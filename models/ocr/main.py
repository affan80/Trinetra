from ocr import OCRExtractor
from language_detector import LanguageDetector
from translator import Translator
from entity_extractor import EntityExtractor

ocr = OCRExtractor()
detector = LanguageDetector()
translator = Translator()
entity_extractor = EntityExtractor()

text = ocr.extract_text(
    "sample.jpg"
)

language = detector.detect_language(
    text
)

translated_text = translator.translate_to_english(
    text
)

entities = entity_extractor.extract_entities(
    translated_text
)

print("\nTEXT")
print(translated_text)

print("\nLANGUAGE")
print(language)

print("\nENTITIES")
print(entities)