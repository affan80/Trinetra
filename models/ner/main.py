from pathlib import Path

from entity_extractor import EntityExtractor

# Read OCR output
ocr_output = (
    Path(__file__).parent.parent
    / "ocr"
    / "output"
    / "output.txt"
)

text = ocr_output.read_text(encoding="utf-8")

extractor = EntityExtractor()

entities = extractor.extract_entities(text)

print("\nDetected Entities\n")

for entity in entities:
    print(entity)