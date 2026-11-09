import os

import pytest

from app.backend.service import file_parser_service
from app.backend.service.file_parser_service import extract_text_from_file


class FakePage:
    def __init__(self, text: str):
        self.text = text

    def extract_text(self) -> str:
        return self.text


@pytest.fixture
def reads(monkeypatch):
    # PdfReader 대신 파일 내용을 그대로 페이지 텍스트로 돌려주고, 몇 번 읽었는지 센다
    opened: list[str] = []

    class FakeReader:
        def __init__(self, file_path: str):
            opened.append(file_path)
            with open(file_path, encoding="utf-8") as file:
                self.pages = [FakePage(file.read())]

    monkeypatch.setattr(file_parser_service, "PdfReader", FakeReader)
    file_parser_service._extract_pdf_text.cache_clear()
    yield opened
    file_parser_service._extract_pdf_text.cache_clear()


def test_same_file_is_read_once(tmp_path, reads):
    pdf = tmp_path / "doc.pdf"
    pdf.write_text("광합성 학습지", encoding="utf-8")

    first = extract_text_from_file(str(pdf))
    second = extract_text_from_file(str(pdf))

    assert first == second == "광합성 학습지"
    assert len(reads) == 1


def test_overwritten_file_is_read_again(tmp_path, reads):
    pdf = tmp_path / "doc.pdf"
    pdf.write_text("처음 내용", encoding="utf-8")
    extract_text_from_file(str(pdf))

    pdf.write_text("바뀐 내용입니다", encoding="utf-8")
    stat = pdf.stat()
    os.utime(pdf, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))

    assert extract_text_from_file(str(pdf)) == "바뀐 내용입니다"
    assert len(reads) == 2


def test_empty_text_error_is_not_cached(tmp_path, reads):
    pdf = tmp_path / "doc.pdf"
    pdf.write_text("", encoding="utf-8")

    for _ in range(2):
        with pytest.raises(ValueError):
            extract_text_from_file(str(pdf))

    assert len(reads) == 2


def test_missing_file_raises(tmp_path, reads):
    with pytest.raises(ValueError):
        extract_text_from_file(str(tmp_path / "없는파일.pdf"))
