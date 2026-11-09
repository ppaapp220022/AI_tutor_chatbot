# 평가

AI 튜터 답변을 고정된 문항으로 채점한다. 프롬프트·모델·문서 처리 방식을 바꿀 때 전후 점수를 비교하는 용도다.

```bash
uv run python -m app.evaluation.run                        # 전체
uv run python -m app.evaluation.run sci-in-001 long-001    # 일부만
uv run python -m app.evaluation.run --model gpt-4o         # 답변 모델 바꾸기
uv run python -m app.evaluation.run --judge-model gpt-4.1  # judge 모델 바꾸기
```

`OPENAI_API_KEY`가 필요하다. DB와 Redis는 쓰지 않는다. 문항 형식과 채점 로직 검사(`test/evaluation/`)는 API 없이 돈다.

## 폴더

| 경로 | 내용 |
|---|---|
| `cases.jsonl` | 평가 문항. 한 줄에 한 문항 |
| `documents/` | 문항이 쓰는 학습지. 업로드된 PDF에서 뽑은 텍스트 대신 넣는다 |
| `results/` | 실행 결과 JSON (git 제외) |

## 문항 유형

| kind | 보는 것 | correct 기준 |
|---|---|---|
| `in_doc` | 문서에 있는 내용을 맞게 답하는가 | 기준 답의 핵심을 빠짐없이, 틀리지 않게 담음 |
| `out_of_doc` | 문서에 없는 내용을 지어내지 않는가 | 문서에 없다고 밝힘 |
| `persona` | 페르소나 지시(`persona_check`)를 따르는가 | `in_doc`과 같음 + 페르소나 위반 없음 |
| `long_doc` | 12,000자(`MAX_FILE_CONTEXT_LENGTH`)를 넘는 문서 뒷부분을 답하는가 | `in_doc`과 같음 |

`long_doc` 문항의 `anchor`는 답의 위치를 표시한다. 지금 서비스는 문서를 12,000자에서 자르므로 이 문항은 실패하는 것이 정상이다. 문서 처리 방식(검색, 요약 등)을 바꾼 뒤 통과하는지 본다.

## 채점

judge 모델(기본 `gpt-4o`, `EVAL_JUDGE_MODEL`)이 문항마다 세 항목을 true/false로 판정하고 근거를 남긴다.

- `correct`: 유형별 기준(위 표)
- `unsupported_claim`: 문서에 없는 내용을 문서에 있는 것처럼 말하거나 문서와 어긋나는 말을 함. 문서 밖 지식이라고 밝힌 보충 설명은 괜찮다
- `persona_violation`: `persona_check`를 지키지 않음

셋 다 통과해야 pass다. judge 응답을 해석하지 못하면 `judge_error`로 세고 통과로 치지 않는다.

## 규칙

- 답변 모델·judge 모델·프롬프트 버전이 다른 점수끼리 섞지 않는다. 결과 파일에 셋이 함께 남는다.
- 평가 문항과 학습지를 프롬프트 예시로 쓰지 않는다.
- judge는 답변 모델보다 강한 모델을 쓴다. 같은 모델이 자기 답을 채점하면 점수가 후해진다.
- 문항을 고치면 `cases_version`이 바뀐다. 이전 결과와 비교할 때 확인한다.
