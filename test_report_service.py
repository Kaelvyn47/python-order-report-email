import json

from report_service import OrderRequest, send_order_report


class FakeClient:
    def __init__(self):
        self.payload = None

    def send(self, payload):
        self.payload = payload
        return {"message_id": "msg-test"}


def test_order_report_contains_pdf_download_and_customer_address():
    client = FakeClient()
    order = OrderRequest("ORD-7", "patient@example.com", "Ari", (("Mask", 2),), 1800)
    result = send_order_report(order, client)
    assert result["message_id"] == "msg-test"
    assert client.payload["to"] == "patient@example.com"
    assert "application/pdf;base64," in client.payload["html"]
    assert "ORD-7.pdf" in client.payload["html"]
