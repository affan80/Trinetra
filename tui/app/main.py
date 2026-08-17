"""Trinetra multimodal OSINT analyst workstation."""

from __future__ import annotations

import json
import mimetypes
import os
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static, TextArea

API_URL = os.getenv("TRINETRA_API_URL", "http://127.0.0.1:8000")


class AnalystWorkstation(App[None]):
    CSS_PATH = "styles/app.tcss"
    TITLE = "Trinetra | Multimodal OSINT Investigation Engine"
    BINDINGS = [
        Binding("1", "dashboard", "Dashboard"),
        Binding("2", "intake", "New Investigation"),
        Binding("4", "evidence", "Evidence"),
        Binding("7", "media", "Media"),
        Binding("r", "report", "Report"),
        Binding("l", "logs", "Logs"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="workstation"):
            yield Static(
                "[1] Dashboard\n[2] New Investigation\n[3] Collection\n[4] Evidence Explorer\n[5] Entities\n[6] Claims\n[7] Media Analysis\n[8] Timeline\n[9] GIS\n[R] Report\n[L] Agent Logs",
                id="navigation",
            )
            with Vertical(id="main"):
                yield Static(id="status")
                with Vertical(id="intake-panel"):
                    yield Label("NEW MULTIMODAL OSINT INVESTIGATION", classes="title")
                    yield Select(
                        [("Upload image, video, audio, PDF, or document", "upload"), ("Enter URL or public social URL", "url"), ("Enter text", "text")],
                        value="upload", id="input-kind",
                    )
                    yield Input(placeholder="Investigation title", id="title")
                    yield Input(placeholder="Target / subject (optional)", id="target")
                    yield Input(placeholder="Local path for upload, public URL, or leave blank for text", id="value")
                    yield TextArea("", id="text", language=None)
                    yield Button("INVESTIGATE", id="investigate", variant="primary")
                yield Static(id="content")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#title", Input).value = "Multimodal OSINT investigation"
        self.query_one("#target", Input).value = "Analyst-provided input"
        self.show_dashboard()

    def request(self, path: str, method: str = "GET", payload: dict | None = None) -> dict | list:
        data = json.dumps(payload).encode() if payload is not None else None
        request = Request(f"{API_URL}{path}", data=data, method=method, headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=30) as response:  # nosec B310 - analyst-configured local endpoint
            return json.loads(response.read())

    def upload(self, path: Path, title: str, target: str) -> dict:
        boundary = f"----Trinetra{uuid.uuid4().hex}"
        fields = {"title": title, "target": target, "objective": "Extract observable information and identify evidence gaps."}
        chunks: list[bytes] = []
        for key, value in fields.items():
            chunks.extend([f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(), value.encode(), b"\r\n"])
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode(),
            f"Content-Type: {mime}\r\n\r\n".encode(), path.read_bytes(), b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ])
        request = Request(f"{API_URL}/v1/intake/upload", data=b"".join(chunks), method="POST", headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urlopen(request, timeout=120) as response:  # nosec B310 - analyst-configured local endpoint
            return json.loads(response.read())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "investigate":
            self.investigate()

    def investigate(self) -> None:
        mode = self.query_one("#input-kind", Select).value
        title = self.query_one("#title", Input).value.strip() or "Multimodal OSINT investigation"
        target = self.query_one("#target", Input).value.strip() or "Analyst-provided input"
        value = self.query_one("#value", Input).value.strip()
        text = self.query_one("#text", TextArea).text.strip()
        try:
            if mode == "upload":
                path = Path(value).expanduser()
                if not path.is_file():
                    raise ValueError("Enter a readable local file path for upload.")
                result = self.upload(path, title, target)
            elif mode == "url":
                result = self.request("/v1/intake/url", "POST", {"title": title, "target": target, "url": value})
            else:
                result = self.request("/v1/intake/text", "POST", {"title": title, "target": target, "text": text or value})
            investigation = result["investigation"]
            artifact = result["artifact"]
            self.notify(f"{investigation['id']} created: {artifact['artifact_id']}", severity="information")
            self.show_media(investigation["id"])
        except Exception as exc:
            self.notify(f"Investigation could not start: {exc}", severity="error")

    def show_dashboard(self) -> None:
        try:
            investigations = self.request("/v1/investigations")
            message = "DASHBOARD\n\nNo investigation selected. Use [2] to begin." if not investigations else self.dashboard_text(investigations[-1])
        except Exception as exc:
            message = f"DASHBOARD\n\nAPI unavailable at {API_URL}\n{exc}\n\nRun: docker compose -f docker-compose.v1.yml up --build"
        self.query_one("#content", Static).update(message)

    def dashboard_text(self, inv: dict) -> str:
        dashboard = self.request(f"/v1/investigations/{inv['id']}/dashboard")
        intel, evidence = dashboard["intelligence"], dashboard["evidence"]
        return (
            f"DASHBOARD — {inv['id']}\n\nTarget: {inv['target']}\nStatus: {inv['status'].upper()}\n\n"
            f"COLLECTION\n{dashboard['collection']}\n\nINTELLIGENCE\nEntities {intel['entities']}  Claims {intel['claims']}\n"
            f"Events {intel['events']}  Locations {intel['locations']}\n\nEVIDENCE\nSupported {evidence['supported']}  Unresolved {evidence['unresolved']}\n\n"
            "All leads require evidence-backed corroboration."
        )

    def selected_investigation(self) -> dict | None:
        investigations = self.request("/v1/investigations")
        return investigations[-1] if investigations else None

    def show_media(self, investigation_id: str | None = None) -> None:
        try:
            inv = self.selected_investigation() if investigation_id is None else {"id": investigation_id}
            if not inv:
                raise ValueError("No investigation yet.")
            media = self.request(f"/v1/investigations/{inv['id']}/media")
            if not media:
                message = "MEDIA ANALYSIS\n\nNo media input for this investigation."
            else:
                row = media[-1]
                message = (
                    f"MEDIA ANALYSIS — {row['filename']}\n\nType: {row['input_kind']}\nMIME: {row['mime_type']}\n"
                    f"SHA256: {row['sha256']}\nSize: {row['size_bytes']} bytes\nDimensions: {row.get('dimensions')}\n\n"
                    f"OBSERVATIONS\n" + "\n".join(f"• {item}" for item in row['observations']) +
                    f"\n\nOBSERVED TEXT / IDENTIFIERS\n" + ("\n".join(row['entities']) or "No text-derived identifiers yet.") +
                    f"\n\nSEARCH HYPOTHESES\n" + ("\n".join(row['search_hypotheses']) or "Configure OCR/ASR/vision adapters for more leads.")
                )
        except Exception as exc:
            message = f"MEDIA ANALYSIS\n\n{exc}"
        self.query_one("#content", Static).update(message)

    def action_dashboard(self) -> None:
        self.show_dashboard()

    def action_intake(self) -> None:
        self.query_one("#intake-panel").focus()

    def action_media(self) -> None:
        self.show_media()

    def action_evidence(self) -> None:
        self.query_one("#content", Static).update("EVIDENCE EXPLORER\n\nSelect an investigation, then browse /evidence via the API. Each evidence item preserves source URL, collection time, hash, and original artifact.")

    def action_report(self) -> None:
        self.query_one("#content", Static).update("REPORT\n\nRun the bounded collection workflow for an evidence-linked intelligence report. Intake analysis alone creates leads, not verified findings.")

    def action_logs(self) -> None:
        self.query_one("#content", Static).update("AGENT LOGS\n\nPlanner, Multimodal Ingestor, Collection Controller, Analyst, Verifier, and Reporter activities are available from the investigation dashboard endpoint.")


if __name__ == "__main__":
    AnalystWorkstation().run()
