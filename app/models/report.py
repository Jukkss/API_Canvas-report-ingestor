from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class ReportProcessRequest(BaseModel):
    download_url: HttpUrl | None = Field(
        default=None,
        description="URL temporaria do Canvas retornada para download do arquivo.",
    )
    file_id: str | None = Field(
        default=None,
        description="ID do arquivo Canvas. Usado para montar a URL de download.",
    )
    verifier: str | None = Field(
        default=None,
        description="Token verifier da URL assinada, obrigatorio quando file_id exigir URL assinada.",
    )
    output_format: Literal["comments", "compact", "json", "summary"] = Field(
        default="comments",
        description="Formato de retorno para o Power Automate.",
    )
    encoding: str | None = Field(
        default=None,
        description="Encoding preferencial para o CSV. Usa fallback automatico quando falhar.",
    )

    @field_validator("file_id", "verifier", "encoding", mode="before")
    @classmethod
    def normalize_optional_placeholders(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str) and value.strip().lower() in {"", "string", "null", "none"}:
            return None
        return value

    @model_validator(mode="after")
    def validate_source(self) -> "ReportProcessRequest":
        if not self.download_url and not self.file_id:
            raise ValueError("Informe download_url ou file_id.")
        return self


class CsvComment(BaseModel):
    student_id: str | None = Field(default=None, exclude=True)
    student_name: str | None = Field(default=None, exclude=True)
    course_id: str | None = Field(default=None, exclude=True)
    course_name: str | None = Field(default=None, exclude=True)
    section: str | None = Field(default=None, exclude=True)
    question: str | None = Field(default=None, exclude=True)
    grade: str | None = None
    comment: str
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)


class DownloadMetadata(BaseModel):
    source_url: str
    final_url: str
    status_code: int
    content_type: str | None = None
    content_disposition: str | None = None
    encoding: str
    redirect_count: int
    size_bytes: int


class ReportProcessResponse(BaseModel):
    success: bool
    total_rows: int
    valid_comments: int
    invalid_rows: int
    columns: list[str]
    comments: list[CsvComment]
    metadata: DownloadMetadata


class CompactComment(BaseModel):
    nota: str | None = None
    comentario: str


class CompactReportResponse(BaseModel):
    success: bool
    total_linhas: int
    total_comentarios: int
    linhas_invalidas: int
    respostas: list[CompactComment]


class CommentsOnlyResponse(BaseModel):
    comentarios: list[str]
