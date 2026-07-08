import json
from pathlib import Path

from gliner import GLiNER

from config import LABELS


class EntityExtractor:

    def __init__(self):
        self.model = GLiNER.from_pretrained(
            "urchade/gliner_medium-v2.1"
        )

    def extract_entities(self, text):

        entities = self.model.predict_entities(
            text,
            LABELS
        )

        # Save output
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / "entities.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                entities,
                f,
                indent=4,
                ensure_ascii=False
            )

        return entities