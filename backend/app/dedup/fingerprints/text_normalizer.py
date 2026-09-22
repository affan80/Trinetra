import re
import unicodedata

MAX_TEXT_LENGTH_FOR_FINGERPRINT = 5_000_000

def normalize_text_for_fingerprint(value: str) -> str:
    # ponytail: bounded fingerprint input; stream/chunk hashing belongs in a later bulk path.
    value = unicodedata.normalize("NFKC", (value or "")[:MAX_TEXT_LENGTH_FOR_FINGERPRINT]).replace("\u200b", "")
    return re.sub(r"\s+", " ", value).strip().casefold()
