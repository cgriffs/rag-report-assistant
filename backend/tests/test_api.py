from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def make_client() -> TestClient:
    # Default settings: no Azure OpenAI configured, so the API runs in
    # extractive demo mode and answers are deterministic.
    return TestClient(create_app(Settings()))


def build_minimal_pdf(text: str) -> bytes:
    """Build a one page PDF with a single line of text, for ingest tests."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
        + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_start = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF"
    ).encode()
    return bytes(out)


def test_health_reports_demo_mode_and_sample_docs():
    response = make_client().get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "extractive-demo"
    assert body["documents"] == 3
    assert body["chunks"] >= 3


def test_documents_lists_sample_set():
    response = make_client().get("/documents")
    assert response.status_code == 200
    names = {doc["name"] for doc in response.json()}
    assert names == {
        "emissions-summary.md",
        "project-status-report.md",
        "quarterly-operations-report.md",
    }


def test_ask_returns_answer_with_citations():
    response = make_client().post(
        "/ask", json={"question": "What was the first time fix rate in Q3?"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "extractive-demo"
    assert "87 percent" in body["answer"]
    assert "[1]" in body["answer"]
    assert body["citations"]
    top = body["citations"][0]
    assert top["document"] == "quarterly-operations-report.md"
    assert top["chunk_id"].startswith("quarterly-operations-report.md#chunk-")
    assert top["score"] > 0


def test_ask_about_emissions_cites_emissions_doc():
    response = make_client().post(
        "/ask", json={"question": "How much were Scope 2 emissions?"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["citations"][0]["document"] == "emissions-summary.md"
    assert "16,340 tonnes" in body["answer"]


def test_ask_unknown_topic_has_no_citations():
    response = make_client().post(
        "/ask", json={"question": "What is the stock price forecast?"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["citations"] == []
    assert "could not find" in body["answer"]


def test_upload_markdown_then_ask():
    client = make_client()
    upload = client.post(
        "/documents",
        files={
            "file": (
                "garden.md",
                b"The community garden harvested 240 kilograms of tomatoes "
                b"in September, a record for the garden.",
                "text/markdown",
            )
        },
    )
    assert upload.status_code == 201
    assert upload.json()["name"] == "garden.md"
    response = client.post(
        "/ask", json={"question": "How many kilograms of tomatoes were harvested?"}
    )
    assert response.json()["citations"][0]["document"] == "garden.md"


def test_upload_pdf_is_indexed():
    client = make_client()
    pdf = build_minimal_pdf("The warehouse stored 512 pallets in October")
    upload = client.post(
        "/documents", files={"file": ("warehouse.pdf", pdf, "application/pdf")}
    )
    assert upload.status_code == 201
    names = {doc["name"] for doc in client.get("/documents").json()}
    assert "warehouse.pdf" in names


def test_upload_rejects_unsupported_type():
    client = make_client()
    upload = client.post(
        "/documents", files={"file": ("data.csv", b"a,b\n1,2", "text/csv")}
    )
    assert upload.status_code == 400
