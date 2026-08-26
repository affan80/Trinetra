import abc
from datetime import datetime


class BaseCollector(abc.ABC):
    @abc.abstractmethod
    async def collect(self, source_url: str):
        pass

    def prepare_item(self, **kwargs):
        """Standardizes output format."""
        return {
            **kwargs,
            "collected_at": datetime.utcnow().isoformat(),
        }
