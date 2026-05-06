from fastapi import HTTPException, status


class CanvasDownloadError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class CsvProcessingError(Exception):
    pass


def to_http_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, CanvasDownloadError):
        code = exc.status_code or status.HTTP_502_BAD_GATEWAY
        return HTTPException(status_code=code, detail=str(exc))
    if isinstance(exc, CsvProcessingError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno.")
