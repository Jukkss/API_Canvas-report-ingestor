import logging
from dataclasses import dataclass

import httpx

from app.config import settings
from app.models.report import DownloadMetadata
from app.utils.errors import CanvasDownloadError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DownloadResult:
    content: bytes
    metadata: DownloadMetadata


class CanvasDownloader:
    def __init__(
        self,
        timeout_seconds: float = settings.request_timeout_seconds,
        max_redirects: int = settings.max_redirects,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_redirects = max_redirects

    def build_download_url(self, file_id: str, verifier: str | None = None) -> str:
        url = f"{settings.canvas_base_url.rstrip('/')}/files/{file_id}/download?download_frd=1"
        if verifier:
            url = f"{url}&verifier={verifier}"
        return url

    async def download(self, url: str) -> DownloadResult:
        logger.info("Iniciando download do report Canvas")
        limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.timeout_seconds,
            max_redirects=self.max_redirects,
            limits=limits,
        ) as client:
            try:
                response = await client.get(url)
            except httpx.TooManyRedirects as exc:
                raise CanvasDownloadError("Limite de redirects excedido.") from exc
            except httpx.TimeoutException as exc:
                raise CanvasDownloadError("Timeout ao baixar o arquivo Canvas.") from exc
            except httpx.HTTPError as exc:
                raise CanvasDownloadError(f"Falha HTTP ao baixar arquivo Canvas: {exc}") from exc

        if response.status_code >= 400:
            raise CanvasDownloadError(
                f"Canvas/CDN retornou status HTTP {response.status_code}.",
                status_code=response.status_code,
            )
        if not response.content:
            raise CanvasDownloadError("Download concluido, mas o arquivo esta vazio.")

        metadata = DownloadMetadata(
            source_url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
            content_disposition=response.headers.get("content-disposition"),
            encoding=response.encoding or settings.default_encoding,
            redirect_count=len(response.history),
            size_bytes=len(response.content),
        )
        logger.info("Download concluido com %s redirect(s)", metadata.redirect_count)
        return DownloadResult(content=response.content, metadata=metadata)
