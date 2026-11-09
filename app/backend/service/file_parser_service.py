from functools import lru_cache
from pathlib import Path
from pypdf import PdfReader

# 이어지는 질문마다 대화방 PDF를 다시 읽으므로, 뽑은 텍스트를 프로세스 메모리에 둔다
MAX_CACHED_FILES = 32

def extract_text_from_pdf(file_path: str) -> str:
    """
    PDF 파일에서 텍스트 추출
    :param file_path: PDF 파일 경로
    :return: 추출된 텍스트
    """
    path = Path(file_path)

    if not path.exists():
        raise ValueError("파일이 존재하지 않습니다.")

    if path.suffix.lower() != ".pdf":
        raise ValueError("pdf 파일만 지원합니다.")

    # 같은 경로에 다른 파일이 덮어써지면 수정 시각·크기가 바뀌어 다시 읽는다
    stat = path.stat()
    return _extract_pdf_text(str(path.resolve()), stat.st_mtime_ns, stat.st_size)

@lru_cache(maxsize=MAX_CACHED_FILES)
def _extract_pdf_text(file_path: str, mtime_ns: int, size: int) -> str:
    """
    PDF 텍스트 추출 (캐시). 예외는 캐시되지 않는다
    :param file_path: PDF 절대 경로
    :param mtime_ns: 파일 수정 시각 (캐시 키)
    :param size: 파일 크기 (캐시 키)
    :return: 추출된 텍스트
    """
    reader = PdfReader(file_path)
    texts = []

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            texts.append(page_text)

    content = "\n".join(texts).strip()

    if not content:
        raise ValueError("PDF에서 추출된 텍스트가 없습니다.")

    return content

def extract_text_from_file(file_path: str) -> str:
    """
    파일 경로에 맞는 텍스트 추출 함수 실행
    :param file_path: 파일 경로
    :return: 추출된 텍스트
    """
    return extract_text_from_pdf(file_path)