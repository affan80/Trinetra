from gliner import GLiNER

class EntityExtractor:

    def __init__(self):

        self.model = GLiNER.from_pretrained(
            "urchade/gliner_medium-v2.1"
        )

        self.labels = [
            "person",
            "organization",
            "location",
            "country",
            "weapon",
            "drone",
            "airbase",
            "military asset"
        ]

    def extract_entities(self, text):

        entities = self.model.predict_entities(
            text,
            self.labels
        )

        return entities


if __name__ == "__main__":

    extractor = EntityExtractor()

    text = """
    Drone activity detected near
    Jaisalmer Airbase.
    """

    entities = extractor.extract_entities(
        text
    )

    print(entities)