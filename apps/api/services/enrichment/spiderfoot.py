"""Small adapter around the local SpiderFoot v4.0 web interface."""

from __future__ import annotations

import os
from urllib.parse import urlparse

import httpx

from apps.api.services.discovery.normalize import normalize_url, validate_public_url
from apps.api.services.enrichment.models import EnrichmentFinding, SpiderFootStartRequest, SpiderFootStartResponse, SpiderFootStatusResponse

MODULES = {
    "account_discovery": "sfp_accounts",
    "public_metadata": "sfp_filemeta",
    "domain_provenance": "sfp_dnsresolve",
}


class SpiderFootClient:
    def __init__(self, base_url: str | None = None, timeout_seconds: int | None = None, max_results: int | None = None) -> None:
        self.base_url = (base_url or os.getenv("SPIDERFOOT_BASE_URL", "http://127.0.0.1:5001")).rstrip("/")
        self.timeout_seconds = timeout_seconds or int(os.getenv("SPIDERFOOT_JOB_TIMEOUT_SECONDS", "120"))
        self.max_results = max_results or int(os.getenv("SPIDERFOOT_MAX_RESULTS", "250"))
        host = urlparse(self.base_url).hostname
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("SpiderFoot sidecar must be a local loopback service")

    async def start(self, request: SpiderFootStartRequest) -> SpiderFootStartResponse:
        modules = [MODULES[module] for module in dict.fromkeys(request.modules)]
        data = {"scanname": f"Borrowed Intimacy: {request.target}", "scantarget": request.target,
                "modulelist": ",".join(modules), "typelist": "", "usecase": ""}
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds) as client:
                response = await client.post("/startscan", data=data, headers={"Accept": "application/json"})
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise RuntimeError("SpiderFoot sidecar is unavailable") from error
        if not isinstance(payload, list) or len(payload) < 2 or payload[0] != "SUCCESS":
            raise RuntimeError("SpiderFoot could not start the selected-source scan")
        return SpiderFootStartResponse(jobId=f"sf_{payload[1]}", status="queued", modules=list(dict.fromkeys(request.modules)))

    async def status(self, job_id: str, target: str = "") -> SpiderFootStatusResponse:
        if not job_id.startswith("sf_"):
            raise ValueError("invalid SpiderFoot job id")
        sidecar_id = job_id.removeprefix("sf_")
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds) as client:
                status_response = await client.get("/scanstatus", params={"id": sidecar_id})
                status_response.raise_for_status()
                status_payload = status_response.json()
                results_response = await client.post("/scaneventresults", data={"id": sidecar_id})
                results_response.raise_for_status()
                results_payload = results_response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise RuntimeError("SpiderFoot sidecar is unavailable") from error
        status = str(status_payload[5]).casefold() if isinstance(status_payload, list) and len(status_payload) > 5 else "unknown"
        findings = self._findings(results_payload)
        return SpiderFootStatusResponse(jobId=job_id, status=status, target=target, findings=findings, warnings=[])

    def _findings(self, payload: object) -> list[EnrichmentFinding]:
        findings: dict[str, EnrichmentFinding] = {}
        rows = payload if isinstance(payload, list) else []
        for row in rows:
            values = row.values() if isinstance(row, dict) else row if isinstance(row, list) else []
            for value in values:
                if not isinstance(value, str) or not value.startswith(("https://", "http://")):
                    continue
                try:
                    validate_public_url(value)
                    url = normalize_url(value)
                except ValueError:
                    continue
                findings.setdefault(url, EnrichmentFinding(type="public_url", value=url, source="spiderfoot", module="selected_source", confidence="low"))
                if len(findings) >= self.max_results:
                    return list(findings.values())
        return list(findings.values())
