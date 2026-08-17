"""Top-level service package.

The services were reorganized into ingestion, processing, and storage domains.
The aliases below keep the former public module paths importable for downstream
deployments while callers migrate to the new layout.
"""

import sys

from services.ingestion import crawlers as _crawlers
from services.ingestion import scraper as _scraper
from services.processing import parser as _parser
from services.processing import worker_service as _worker_service
from services.storage import common as _common
from services.storage import shared as _shared

_LEGACY_MODULES = {
    "crawlers": _crawlers,
    "scraper": _scraper,
    "parser": _parser,
    "worker_service": _worker_service,
    "common": _common,
    "shared": _shared,
}

for _name, _module in _LEGACY_MODULES.items():
    sys.modules.setdefault(f"{__name__}.{_name}", _module)
