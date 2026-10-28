"""HTTP transport to the TelemetryBot collector."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from agentelemetry.schemas import IngestBatch

logger = logging.getLogger("agentelemetry")


class HttpTransport:
    def __init__(
        self,
        collector_url: str,
        api_key: str = "",
        timeout_seconds: float = 5.0,
    ) -> None:
        self.collector_url = collector_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def send_batch(self, batch: IngestBatch) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        url = f"{self.collector_url}/v1/ingest"
        payload = batch.model_dump(mode="json")
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.warning("Failed to flush telemetry to %s: %s", url, exc)
            return {"ok": False, "error": str(exc)}

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        url = f"{self.collector_url}{path}"
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()

    def post(self, path: str, json_body: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        url = f"{self.collector_url}{path}"
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(url, json=json_body, headers=headers)
            response.raise_for_status()
            return response.json()
