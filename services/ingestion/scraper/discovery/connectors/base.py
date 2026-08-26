from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

import requests
from services.scraper.discovery import UrlCandidate


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass
class ConnectorError:
    source: str
    message: str
    code: str = "connector_error"
    recoverable: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "message": self.message,
            "code": self.code,
            "recoverable": self.recoverable,
            "metadata": dict(self.metadata),
        }


@dataclass
class ConnectorResult:
    source: str
    candidates: list[UrlCandidate] = field(default_factory=list)
    errors: list[ConnectorError] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_candidate(self, candidate: UrlCandidate | dict[str, Any]) -> None:
        if isinstance(candidate, dict):
            candidate = UrlCandidate.from_dict(candidate)

        self.candidates.append(candidate)

    def add_error(
        self,
        message: str,
        code: str = "connector_error",
        recoverable: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.errors.append(
            ConnectorError(
                source=self.source,
                message=message,
                code=code,
                recoverable=recoverable,
                metadata=metadata or {},
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "errors": [error.to_dict() for error in self.errors],
            "metadata": dict(self.metadata),
        }


class HttpDiscoveryConnector:
    source_name = "connector"
    default_headers = {
        "User-Agent": os.getenv("DISCOVERY_USER_AGENT", "TrinetraOSINT/1.0"),
        "Accept": "application/json,text/xml,application/xml,text/html;q=0.9,*/*;q=0.8",
    }

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout_seconds: int | None = None,
        max_results: int | None = None,
        retries: int | None = None,
        rate_limit_seconds: float | None = None,
    ):
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds or env_int("DISCOVERY_TIMEOUT_SECONDS", 20)
        self.max_results = max_results or env_int("DISCOVERY_MAX_RESULTS", 50)
        self.retries = retries if retries is not None else env_int("DISCOVERY_RETRIES", 2)
        self.rate_limit_seconds = (
            rate_limit_seconds
            if rate_limit_seconds is not None
            else env_float("DISCOVERY_RATE_LIMIT_SECONDS", 0.0)
        )

    def new_result(self, **metadata: Any) -> ConnectorResult:
        return ConnectorResult(source=self.source_name, metadata=metadata)

    def request(self, url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None):
        merged_headers = dict(self.default_headers)
        if headers:
            merged_headers.update(headers)

        last_error = None

        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=merged_headers,
                    timeout=self.timeout_seconds,
                )

                if self.rate_limit_seconds:
                    time.sleep(self.rate_limit_seconds)

                if response.status_code < 400:
                    return response, None

                last_error = ConnectorError(
                    source=self.source_name,
                    message=f"HTTP {response.status_code} from {url}",
                    code=f"http_{response.status_code}",
                    recoverable=response.status_code in {408, 429, 500, 502, 503, 504},
                    metadata={"url": url, "params": params or {}},
                )

                if not last_error.recoverable:
                    break

            except Exception as error:
                last_error = ConnectorError(
                    source=self.source_name,
                    message=str(error),
                    code=error.__class__.__name__,
                    recoverable=True,
                    metadata={"url": url, "params": params or {}, "attempt": attempt + 1},
                )

            if attempt < self.retries:
                time.sleep(min(2 ** attempt, 8))

        return None, last_error

    def request_json(
        self,
        result: ConnectorResult,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        response, error = self.request(url, params=params, headers=headers)
        if error:
            result.errors.append(error)
            return None

        try:
            return response.json()
        except Exception as error:
            result.add_error(
                str(error),
                code="invalid_json",
                metadata={"url": url, "params": params or {}},
            )
            return None

    def request_text(
        self,
        result: ConnectorResult,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        response, error = self.request(url, params=params, headers=headers)
        if error:
            result.errors.append(error)
            return ""

        return response.text

    def request_bytes(
        self,
        result: ConnectorResult,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        response, error = self.request(url, params=params, headers=headers)
        if error:
            result.errors.append(error)
            return b""

        return response.content

    def limit_candidates(self, candidates: list[UrlCandidate], max_results: int | None = None) -> list[UrlCandidate]:
        limit = max_results or self.max_results
        return candidates[: max(0, limit)]
