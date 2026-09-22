ADAPTERS = {"rss": "Layer 3 RSS adapter", "http": "Layer 3 HTTP adapter", "api": "Layer 3 API adapter"}

def supported(name):
    return name in ADAPTERS
