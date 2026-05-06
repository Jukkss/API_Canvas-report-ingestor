from app.models.report import (
    CommentsOnlyResponse,
    CompactComment,
    CompactReportResponse,
    ReportProcessRequest,
    ReportProcessResponse,
)
from app.parsers.csv_parser import parse_student_analysis_csv
from app.services.canvas_downloader import CanvasDownloader


class ReportProcessor:
    def __init__(self, downloader: CanvasDownloader | None = None) -> None:
        self.downloader = downloader or CanvasDownloader()

    async def process(
        self,
        payload: ReportProcessRequest,
    ) -> ReportProcessResponse | CompactReportResponse | CommentsOnlyResponse:
        source_url = str(payload.download_url) if payload.download_url else self.downloader.build_download_url(
            payload.file_id or "",
            payload.verifier,
        )
        download = await self.downloader.download(source_url)
        parsed = parse_student_analysis_csv(download.content, payload.encoding)
        metadata = download.metadata.model_copy(update={"encoding": parsed.encoding})

        if payload.output_format == "comments":
            return CommentsOnlyResponse(
                comentarios=[comment.comment for comment in parsed.comments],
            )

        if payload.output_format == "compact":
            return CompactReportResponse(
                success=True,
                total_linhas=parsed.total_rows,
                total_comentarios=len(parsed.comments),
                linhas_invalidas=parsed.invalid_rows,
                respostas=[
                    CompactComment(nota=comment.grade, comentario=comment.comment)
                    for comment in parsed.comments
                ],
            )

        return ReportProcessResponse(
            success=True,
            total_rows=parsed.total_rows,
            valid_comments=len(parsed.comments),
            invalid_rows=parsed.invalid_rows,
            columns=parsed.columns,
            comments=parsed.comments if payload.output_format == "json" else [],
            metadata=metadata,
        )
