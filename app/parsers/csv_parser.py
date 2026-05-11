import csv
import io
import logging
import re
import unicodedata
import codecs
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.models.report import CsvComment
from app.utils.errors import CsvProcessingError

logger = logging.getLogger(__name__)

COMMENT_KEYS = {
    "comment",
    "comments",
    "comentario",
    "comentarios",
    "answer",
    "resposta",
    "response",
    "student_answer",
    "student_response",
}

OPEN_QUESTION_HINTS = {
    "aberta",
    "aberto",
    "comente",
    "comentario",
    "comentarios",
    "descreva",
    "diga",
    "explique",
    "justifique",
    "motivou",
    "motivo",
    "observacao",
    "observacoes",
    "opiniao",
    "resposta_acima",
    "sugestao",
    "sugestoes",
}

GRADE_QUESTION_HINTS = {
    "escala_de_0_a_10",
    "indicaria",
    "nota",
    "recomendaria",
}

METADATA_COLUMNS = {
    "id",
    "section",
    "section_id",
    "section_sis_id",
    "submitted",
    "n_correct",
    "n_incorrect",
    "score",
}

COLUMN_ALIASES = {
    "student_id": {"student_id", "student sis id", "sis_user_id", "user_id", "id_aluno", "matricula"},
    "student_name": {"student_name", "student", "student name", "nome_aluno", "aluno", "name"},
    "course_id": {"course_id", "sis_course_id", "id_curso"},
    "course_name": {"course_name", "course", "curso", "nome_curso"},
    "section": {"section", "section_name", "turma"},
    "submitted": {"submitted", "submited", "submitted_at", "submitted date", "data_envio", "data_de_envio"},
    "question": {"question", "question_text", "pergunta", "questao"},
}


@dataclass(frozen=True)
class CsvParseResult:
    total_rows: int
    invalid_rows: int
    columns: list[str]
    comments: list[CsvComment]
    encoding: str


def normalize_column_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_value.strip().lower())
    return cleaned.strip("_")


def _decode(content: bytes, preferred_encoding: str | None = None) -> tuple[str, str]:
    encodings = [preferred_encoding, settings.default_encoding, "utf-8-sig", settings.fallback_encoding]
    for encoding in dict.fromkeys(item for item in encodings if item):
        try:
            codecs.lookup(encoding)
            return content.decode(encoding), encoding
        except LookupError:
            logger.warning("Encoding desconhecido ignorado: %s", encoding)
        except UnicodeDecodeError:
            logger.warning("Falha ao decodificar CSV com encoding %s", encoding)
    raise CsvProcessingError("Nao foi possivel decodificar o CSV com UTF-8 ou latin1.")


def _extract_value(row: dict[str, str], aliases: set[str]) -> str | None:
    normalized_aliases = {normalize_column_name(alias) for alias in aliases}
    for key, value in row.items():
        if normalize_column_name(key) in normalized_aliases and value and value.strip():
            return value.strip()
    return None


def _find_comment(row: dict[str, str]) -> str | None:
    normalized_comment_keys = {normalize_column_name(key) for key in COMMENT_KEYS}
    for key, value in row.items():
        if normalize_column_name(key) in normalized_comment_keys and value and value.strip():
            return value.strip()

    text_candidates = [
        value.strip()
        for key, value in row.items()
        if value and value.strip() and normalize_column_name(key) not in {"id", "student_id", "course_id"}
    ]
    if len(text_candidates) == 1:
        return text_candidates[0]
    return None


def _looks_like_open_question(column_name: str) -> bool:
    normalized = normalize_column_name(column_name)
    if normalized in METADATA_COLUMNS:
        return False
    return any(hint in normalized for hint in OPEN_QUESTION_HINTS)


def _extract_comment_entries(row: dict[str, str]) -> list[tuple[str | None, str]]:
    entries: list[tuple[str | None, str]] = []
    normalized_comment_keys = {normalize_column_name(key) for key in COMMENT_KEYS}

    for key, value in row.items():
        normalized_key = normalize_column_name(key)
        if normalized_key in normalized_comment_keys and value and value.strip():
            entries.append((key, value.strip()))

    for key, value in row.items():
        if _looks_like_open_question(key) and value and value.strip():
            entries.append((key, value.strip()))

    if entries:
        seen: set[tuple[str | None, str]] = set()
        unique_entries: list[tuple[str | None, str]] = []
        for question, comment in entries:
            marker = (question, comment)
            if marker not in seen:
                unique_entries.append(marker)
                seen.add(marker)
        return unique_entries

    fallback = _find_comment(row)
    return [(None, fallback)] if fallback else []


def _looks_like_grade_question(column_name: str) -> bool:
    normalized = normalize_column_name(column_name)
    if normalized in METADATA_COLUMNS:
        return False
    return any(hint in normalized for hint in GRADE_QUESTION_HINTS)


def _extract_grade(row: dict[str, str], comment_question: str | None = None) -> str | None:
    for key, value in row.items():
        if comment_question and key == comment_question:
            break
        if _looks_like_grade_question(key) and value and value.strip():
            return value.strip()

    for key, value in row.items():
        if _looks_like_grade_question(key) and value and value.strip():
            return value.strip()

    return None


def parse_student_analysis_csv(content: bytes, preferred_encoding: str | None = None) -> CsvParseResult:
    decoded, encoding = _decode(content, preferred_encoding)
    sample = decoded[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(decoded), dialect=dialect)
    if not reader.fieldnames:
        raise CsvProcessingError("CSV sem cabecalho.")

    comments: list[CsvComment] = []
    total_rows = 0
    invalid_rows = 0

    for row in reader:
        total_rows += 1
        clean_row: dict[str, Any] = {
            (key or "").strip(): (value.strip() if isinstance(value, str) else value)
            for key, value in row.items()
        }
        if not any(value for value in clean_row.values()):
            invalid_rows += 1
            continue

        comment_entries = _extract_comment_entries(clean_row)
        if not comment_entries:
            invalid_rows += 1
            continue

        for question, comment in comment_entries:
            comments.append(
                CsvComment(
                    student_id=_extract_value(clean_row, COLUMN_ALIASES["student_id"]),
                    student_name=_extract_value(clean_row, COLUMN_ALIASES["student_name"]),
                    course_id=_extract_value(clean_row, COLUMN_ALIASES["course_id"]),
                    course_name=_extract_value(clean_row, COLUMN_ALIASES["course_name"]),
                    section=_extract_value(clean_row, COLUMN_ALIASES["section"]),
                    submitted=_extract_value(clean_row, COLUMN_ALIASES["submitted"]),
                    question=question or _extract_value(clean_row, COLUMN_ALIASES["question"]),
                    grade=_extract_grade(clean_row, question),
                    comment=comment,
                    raw=clean_row,
                )
            )

    return CsvParseResult(
        total_rows=total_rows,
        invalid_rows=invalid_rows,
        columns=[normalize_column_name(column) for column in reader.fieldnames],
        comments=comments,
        encoding=encoding,
    )
