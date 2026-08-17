from dataclasses import dataclass, field


@dataclass
class FetchResult:
    url: str
    status: int = 0
    html: str = ""
    fetcher: str = ""
    headers: dict = field(default_factory=dict)
    error: str = ""
    elapsed_ms: int = 0

    @property
    def ok(self):
        return not self.error and 200 <= self.status < 400 and bool(self.html)
