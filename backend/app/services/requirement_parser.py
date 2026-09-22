def parse_watchlist(data: dict) -> dict:
    entities = [{"canonical_name": e["name"], "aliases": list(dict.fromkeys(e["aliases"])), "type": e["type"]} for e in data["entities"]]
    return {"entities": entities, "topics": list(dict.fromkeys(data["subjects"])), "keywords": list(dict.fromkeys(data["keywords"])), "exclude_keywords": list(dict.fromkeys(data["exclude_keywords"])), "locations": [x["name"] for x in data["locations"]], "languages": data["languages"], "source_classes": data["source_classes"]}
