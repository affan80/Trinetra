from enum import Enum


class SourceType(Enum):
    NEWS = "news"
    GOVERNMENT = "government"
    DOCUMENT = "document"
    SOCIAL = "social"
    VIDEO = "video"
    IMAGE = "image"
    WEB = "web"

SOURCE_REGISTRY = {
    "bbc.com": {
        "source_id": "SRC-NEWS-001",
        "name": "BBC",
        "domain": "bbc.com",
        "source_type": SourceType.NEWS,
        "country": "UK",
        "API": False,
        "RSS": True,
        "crawler": True,
        "priority": "high",
        "enabled": True,
        "collection_interval": "30m"
    },
    # Add other sources here following this pattern
}

def get_source_config(domain):
    return SOURCE_REGISTRY.get(domain, {
        "source_id": "UNKNOWN",
        "name": domain,
        "domain": domain,
        "source_type": SourceType.WEB,
        "enabled": False
    })
