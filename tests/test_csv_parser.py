from app.parsers.csv_parser import parse_student_analysis_csv


def test_parse_utf8_student_analysis_csv_extracts_comments() -> None:
    content = (
        "student_id,student_name,course_name,question,comment\n"
        "123,Ana Silva,Engenharia,Como foi?,Excelente orientação\n"
        "456,Bruno Lima,Engenharia,Como foi?,\n"
        ",,,,\n"
    ).encode("utf-8")

    result = parse_student_analysis_csv(content)

    assert result.encoding == "utf-8"
    assert result.total_rows == 3
    assert result.invalid_rows == 2
    assert len(result.comments) == 1
    assert result.comments[0].student_id == "123"
    assert result.comments[0].comment == "Excelente orientação"


def test_parse_latin1_student_analysis_csv_with_portuguese_aliases() -> None:
    content = (
        "matricula;aluno;curso;pergunta;comentario\n"
        "789;João Souza;Administração;Avaliação;Ótima condução\n"
    ).encode("latin1")

    result = parse_student_analysis_csv(content)

    assert result.encoding == "latin1"
    assert result.total_rows == 1
    assert result.invalid_rows == 0
    assert result.comments[0].student_id == "789"
    assert result.comments[0].student_name == "João Souza"
    assert result.comments[0].comment == "Ótima condução"


def test_parse_canvas_open_question_column_as_comment() -> None:
    content = (
        'section,section_id,submitted,"5754081: Em uma escala de 0 a 10, quanto você indicaria esta disciplina?",5754082: Diga o que motivou sua resposta acima.,score\n'
        "Turma A,10,2026-05-06,9,Material claro e boa didática,8\n"
        "Turma B,11,2026-05-06,7,,7\n"
    ).encode("utf-8")

    result = parse_student_analysis_csv(content)

    assert result.total_rows == 2
    assert result.invalid_rows == 1
    assert len(result.comments) == 1
    assert result.comments[0].section == "Turma A"
    assert result.comments[0].submitted == "2026-05-06"
    assert result.comments[0].question == "5754082: Diga o que motivou sua resposta acima."
    assert result.comments[0].grade == "9"
    assert result.comments[0].comment == "Material claro e boa didática"


def test_parse_submited_alias() -> None:
    content = "submited,comment\n2026-05-07,Comentário válido\n".encode("utf-8")

    result = parse_student_analysis_csv(content)

    assert result.comments[0].submitted == "2026-05-07"


def test_parse_ignores_unknown_preferred_encoding() -> None:
    content = "student_id,comment\n1,Comentário válido\n".encode("utf-8")

    result = parse_student_analysis_csv(content, preferred_encoding="string")

    assert result.encoding == "utf-8"
    assert result.comments[0].comment == "Comentário válido"
