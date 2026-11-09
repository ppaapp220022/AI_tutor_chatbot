import math
import re

CHUNK_SIZE = 1000
OMITTED_MARK = "\n…(중략)…\n"


def _bigrams(text: str) -> set[str]:
    """
    공백을 뺀 글자 2개 묶음. 형태소 분석 없이 한국어 낱말이 겹치는지 보기 위해 쓴다
    :param text: 문자열
    :return: 글자 2개 묶음 집합
    """
    compact = re.sub(r"\s+", "", text.lower())
    return {compact[i:i + 2] for i in range(len(compact) - 1)}


def _split_chunks(text: str) -> list[str]:
    """
    줄 단위로 모아 CHUNK_SIZE 안팎의 조각으로 나눈다. PDF 추출 텍스트는 빈 줄이 없을 수 있어 줄을 기준으로 한다
    :param text: 문서 텍스트
    :return: 조각 목록 (원래 순서)
    """
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for line in text.splitlines():
        # 줄 하나가 너무 길면 잘라서 넣는다
        while len(line) > CHUNK_SIZE:
            if current:
                chunks.append("\n".join(current))
                current, length = [], 0
            chunks.append(line[:CHUNK_SIZE])
            line = line[CHUNK_SIZE:]
        if current and length + len(line) > CHUNK_SIZE:
            chunks.append("\n".join(current))
            current, length = [], 0
        current.append(line)
        length += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return [chunk for chunk in chunks if chunk.strip()]


def select_document_context(text: str, query: str, limit: int) -> str:
    """
    문서가 limit보다 길면 질문과 관련된 조각만 골라 limit 안에 담는다
    첫 조각(제목·개요)은 항상 넣고, 나머지는 질문과 겹치는 드문 글자 묶음이 많은 순으로 채운 뒤 원래 순서로 잇는다
    :param text: 문서 텍스트
    :param query: 질문 (직전 질문을 함께 넣을 수 있다)
    :param limit: 최대 글자 수
    :return: 모델에 넣을 문서 텍스트
    """
    if len(text) <= limit:
        return text

    chunks = _split_chunks(text)
    chunk_grams = [_bigrams(chunk) for chunk in chunks]
    query_grams = _bigrams(query)

    # 여러 조각에 흔한 묶음('하는', '있다' 등)보다 드문 묶음에 무게를 준다
    def weight(gram: str) -> float:
        frequency = sum(1 for grams in chunk_grams if gram in grams)
        return math.log((len(chunks) + 1) / (frequency + 1))

    weights = {gram: weight(gram) for gram in query_grams}
    scores = [sum(weights[gram] for gram in query_grams & grams) for grams in chunk_grams]

    order = [0] + sorted(range(1, len(chunks)), key=lambda i: (-scores[i], i))
    selected: list[int] = []
    used = 0
    for index in order:
        cost = len(chunks[index]) + len(OMITTED_MARK)
        if used + cost > limit:
            continue
        selected.append(index)
        used += cost

    parts: list[str] = []
    previous = -1
    for index in sorted(selected):
        if parts and index != previous + 1:
            parts.append(OMITTED_MARK)
        elif parts:
            parts.append("\n")
        parts.append(chunks[index])
        previous = index
    if previous != len(chunks) - 1:
        parts.append(OMITTED_MARK)
    return "".join(parts)
