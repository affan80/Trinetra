import spacy
import logging
from scrapy.exceptions import NotConfigured

logger = logging.getLogger(__name__)

class EntityExtractionPipeline:
    """
    Pipeline to extract Named Entities (People, Orgs, Locations) from item text.
    Requires Spacy model: `python -m spacy download en_core_web_sm`
    """
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.error("Spacy model 'en_core_web_sm' not found. Please run 'python -m spacy download en_core_web_sm'")
            raise NotConfigured("Spacy model not found")

    def process_item(self, item, spider):
        text = item.get("text")
        if not text:
            return item
            
        doc = self.nlp(text[:100000]) # Cap text for performance
        
        entities = {
            "org": set(),
            "person": set(),
            "location": set()
        }
        
        for ent in doc.ents:
            if ent.label_ == "ORG":
                entities["org"].add(ent.text)
            elif ent.label_ == "PERSON":
                entities["person"].add(ent.text)
            elif ent.label_ in ["GPE", "LOC"]:
                entities["location"].add(ent.text)
                
        # Convert sets to sorted lists for JSON serialization
        metadata = item.get("metadata", {})
        metadata["entities"] = {k: sorted(list(v)) for k, v in entities.items()}
        item["metadata"] = metadata
        
        return item
