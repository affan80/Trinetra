import hashlib

def fingerprint(profile_id, source_id, query, language):
    return hashlib.sha256(f"{profile_id}:{source_id}:{language}:{query}".encode()).hexdigest()
