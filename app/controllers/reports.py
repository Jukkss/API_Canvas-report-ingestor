import logging

from fastapi import APIRouter

from app.models.report import CommentsOnlyResponse, CompactReportResponse, ReportProcessRequest, ReportProcessResponse
from app.services.report_processor import ReportProcessor
from app.utils.errors import to_http_exception

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/student-analysis/process", response_model=ReportProcessResponse | CompactReportResponse | CommentsOnlyResponse)
async def process_student_analysis(
    payload: ReportProcessRequest,
) -> ReportProcessResponse | CompactReportResponse | CommentsOnlyResponse:
    processor = ReportProcessor()
    try:
        return await processor.process(payload)
    except Exception as exc:
        logger.exception("Erro ao processar report student_analysis")
        raise to_http_exception(exc) from exc
