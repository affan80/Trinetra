# Configuration

Runtime configuration that is not tied to a Python package lives here.

```text
config/
  scraper/
    source_registry.json
```

Package code should read these files through explicit paths or environment variables, not by assuming config lives inside `services/`.
