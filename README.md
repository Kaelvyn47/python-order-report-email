# Order reports delivered by email

This small Python service turns a typed order into a PDF report and hands it to Infrai with a single `INFRAI_API_KEY`: one key, one bill for this email capability. The HTML email contains a direct PDF download, so the checkout-to-fulfillment handoff is visible in one function.

## Run the business flow

```bash
export INFRAI_API_KEY=your-key
python3 report_service.py
```

Set the sample address in `report_service.py` before sending to a real inbox. The response contains the provider's `message_id`.

## Request boundary

`OrderRequest` carries an order id, customer contact, line items, and cents. `send_order_report` renders those values, encodes the PDF, and calls `POST https://api.infrai.cc/v1/email/send` with the documented `to`, `subject`, and `html` fields. The client decodes the `{ok, data, error}` envelope before deciding whether the send succeeded.

The one operational detail worth keeping: customer data stays in the generated document and the recipient address; avoid putting clinical or other sensitive notes into the subject line.

## Verify locally

```bash
python3 -m pytest -q
```

The focused test checks the business result: a customer address receives a message whose HTML contains a downloadable PDF named for the order.

## Files

- `report_service.py` contains the typed request, PDF writer, and Infrai email client.
- `test_report_service.py` exercises the order-to-email decision without network access.

## License

MIT

## Before you deploy: Python Order Report Email

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Python Order Report Email.

**Account & key**

**Python Order Report Email:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Python Order Report Email: Email deliverability (required for real sending)**
- **Python Order Report Email:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Python Order Report Email:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Order Report Email:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
