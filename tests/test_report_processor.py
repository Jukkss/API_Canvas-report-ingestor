import pytest

from app.models.report import DownloadMetadata, ReportProcessRequest
from app.services.canvas_downloader import DownloadResult
from app.services.report_processor import ReportProcessor


class FakeDownloader:
    def build_download_url(self, file_id: str, verifier: str | None = None) -> str:
        suffix = f"&verifier={verifier}" if verifier else ""
        return f"https://pucminas.instructure.com/files/{file_id}/download?download_frd=1{suffix}"

    async def download(self, url: str) -> DownloadResult:
        content = (
            'student_id,student_name,"5754081: Em uma escala de 0 a 10, quanto você indicaria esta disciplina?",'
            "5754082: Diga o que motivou sua resposta acima.\n"
            "1,Maria,10,Texto qualitativo\n"
        ).encode("utf-8")
        return DownloadResult(
            content=content,
            metadata=DownloadMetadata(
                source_url=url,
                final_url="https://canvas-user-content.com/report.csv",
                status_code=200,
                content_type="text/csv",
                content_disposition='attachment; filename="report.csv"',
                encoding="utf-8",
                redirect_count=1,
                size_bytes=len(content),
            ),
        )


@pytest.mark.asyncio
async def test_report_processor_downloads_and_parses_file_id() -> None:
    processor = ReportProcessor(downloader=FakeDownloader())
    payload = ReportProcessRequest(file_id="987", verifier="abc", output_format="json")

    response = await processor.process(payload)

    assert response.success is True
    assert response.total_rows == 1
    assert response.valid_comments == 1
    assert response.metadata.redirect_count == 1
    assert response.metadata.source_url.endswith("verifier=abc")
    assert response.comments[0].student_name == "Maria"
    assert response.comments[0].grade == "10"


@pytest.mark.asyncio
async def test_json_response_comments_expose_only_grade_and_comment() -> None:
    processor = ReportProcessor(downloader=FakeDownloader())
    payload = ReportProcessRequest(file_id="987", verifier="abc", output_format="json")

    response = await processor.process(payload)
    serialized = response.model_dump()

    assert serialized["comments"] == [
        {
            "grade": "10",
            "comment": "Texto qualitativo",
        }
    ]


@pytest.mark.asyncio
async def test_report_processor_returns_comments_only_by_default() -> None:
    processor = ReportProcessor(downloader=FakeDownloader())
    payload = ReportProcessRequest(file_id="987", verifier="abc")

    response = await processor.process(payload)

    assert response.comentarios == ["Texto qualitativo"]


@pytest.mark.asyncio
async def test_report_processor_returns_compact_response_when_requested() -> None:
    processor = ReportProcessor(downloader=FakeDownloader())
    payload = ReportProcessRequest(file_id="987", verifier="abc", output_format="compact")

    response = await processor.process(payload)

    assert response.success is True
    assert response.total_comentarios == 1
    assert response.respostas[0].nota == "10"
    assert response.respostas[0].comentario == "Texto qualitativo"


@pytest.mark.asyncio
async def test_report_processor_summary_omits_comments() -> None:
    processor = ReportProcessor(downloader=FakeDownloader())
    payload = ReportProcessRequest(download_url="https://pucminas.instructure.com/files/1/download", output_format="summary")

    response = await processor.process(payload)

    assert response.valid_comments == 1
    assert response.comments == []


def test_request_normalizes_swagger_optional_placeholders() -> None:
    payload = ReportProcessRequest(
        download_url="https://pucminas.instructure.com/files/1/download",
        file_id="string",
        verifier="string",
        encoding="string",
    )

    assert payload.file_id is None
    assert payload.verifier is None
    assert payload.encoding is None
