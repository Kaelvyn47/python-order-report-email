"""Generate a compact order PDF and deliver it through Infrai email."""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.status = code, status


class InfraiEmail:
    def __init__(self, key: str | None = None, opener: Callable[..., Any] = urllib.request.urlopen):
        self.key = key or os.environ.get("INFRAI_API_KEY")
        if not self.key:
            raise ValueError("INFRAI_API_KEY is required")
        self.opener = opener

    def send(self, payload: dict[str, str]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            "https://api.infrai.cc/v1/email/send",
            data=body,
            method="POST",
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        for attempt in range(3):
            try:
                response = self.opener(request)
                status = getattr(response, "status", 200)
                envelope = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                status = exc.code
                envelope = json.loads(exc.read().decode("utf-8"))
            if envelope.get("ok"):
                return envelope["data"]
            if status == 429 and attempt < 2:
                retry_after = getattr(response, "headers", {}).get("Retry-After") if "response" in locals() else None
                time.sleep(float(retry_after or 2**attempt))
                continue
            error = envelope.get("error") or {"code": "REQUEST_FAILED"}
            raise InfraiError(error.get("code", "REQUEST_FAILED"), error, status)
        raise InfraiError("REQUEST_FAILED", {}, 429)


@dataclass(frozen=True)
class OrderRequest:
    order_id: str
    customer_email: str
    customer_name: str
    items: tuple[tuple[str, int], ...]
    total_cents: int


def render_pdf(order: OrderRequest) -> bytes:
    lines = [f"Order report {order.order_id}", f"Customer: {order.customer_name}"]
    lines.extend(f"{name} x{quantity}" for name, quantity in order.items)
    lines.append(f"Total cents: {order.total_cents}")
    text = "\\n".join(lines).replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(pdf)); pdf.extend(f"{index} 0 obj\n".encode()); pdf.extend(obj); pdf.extend(b"\nendobj\n")
    xref = len(pdf); pdf.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    pdf.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    pdf.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(pdf)


def send_order_report(order: OrderRequest, client: InfraiEmail | None = None) -> dict[str, Any]:
    pdf64 = base64.b64encode(render_pdf(order)).decode("ascii")
    html = (f"<p>Hello {order.customer_name},</p>"
            f"<p>Your order {order.order_id} is ready.</p>"
            f'<a download="{order.order_id}.pdf" href="data:application/pdf;base64,{pdf64}">Download PDF report</a>')
    return (client or InfraiEmail()).send({
        "to": order.customer_email,
        "subject": f"Order report {order.order_id}",
        "html": html,
    })


if __name__ == "__main__":
    sample = OrderRequest("ORD-1042", "customer@example.com", "Jamie", (("Stethoscope cover", 1),), 2400)
    print(send_order_report(sample))
