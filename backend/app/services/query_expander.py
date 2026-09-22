MAX_QUERIES_PER_PROFILE = 100

def expand(requirement: dict) -> list[dict]:
    values = [("ENTITY", e["canonical_name"]) for e in requirement["entities"]]
    values += [("ENTITY_ALIAS", a) for e in requirement["entities"] for a in e["aliases"]]
    values += [("TOPIC", x) for x in requirement["topics"]] + [("KEYWORD", x) for x in requirement["keywords"]] + [("LOCATION", x) for x in requirement["locations"]]
    result = []
    seen = set()
    def add(parts):
        query = " ".join(f'"{v}"' if t in {"ENTITY", "ENTITY_ALIAS", "LOCATION"} else v for t, v in parts)
        if query and query not in seen and len(result) < MAX_QUERIES_PER_PROFILE:
            seen.add(query); result.append({"query": query, "language": requirement["languages"][0], "method": "deterministic_combination", "generated_from": [{"type": t, "value": v} for t, v in parts]})
    for item in values: add([item])
    entities = [x for x in values if x[0] in {"ENTITY", "ENTITY_ALIAS"}]
    contexts = [x for x in values if x[0] in {"TOPIC", "KEYWORD", "LOCATION"}]
    for entity in entities:
        for context in contexts: add([entity, context])
    for keyword in [x for x in values if x[0] in {"TOPIC", "KEYWORD"}]:
        for location in [x for x in values if x[0] == "LOCATION"]: add([keyword, location])
    return result
