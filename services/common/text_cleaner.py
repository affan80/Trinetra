import re

def clean_text(text):
    """
    Cleans the given text by removing extra whitespace, HTML tags, and other noise.
    """
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text
