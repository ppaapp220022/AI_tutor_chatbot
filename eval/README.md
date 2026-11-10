# 평가

AI 튜터 답변을 고정된 문항으로 채점한다. 프롬프트·모델·문서 처리 방식을 바꿀 때 전후 점수를 비교하는 용도다.

```bash
uv run python -m app.evaluation.run                        # 전체
uv run python -m app.evaluation.run sci-in-001 long-001    # 일부만
uv run python -m app.evaluation.run --model gpt-4o         # 답변 모델 바꾸기
uv run python -m app.evaluation.run --judge-model gpt-4.1  # judge 모델 바꾸기
uv run python -m app.evaluation.run --batch --poll 30      # Batch API로 (비용 절반, 결과는 몇 분~최대 24시간 뒤)
```

`--batch`는 답변 배치가 끝나면 그 답변으로 judge 배치를 보낸다. 요청 본문이 바로 돌릴 때와 같아 점수를 그대로 비교한다. 결과 파일의 `mode`가 `batch`이고 문항별 시간은 0이다. 기다리는 동안 프로세스가 살아 있어야 결과 파일이 남는다.

여러 실행을 동시에 띄우지 않는다. 결과 파일 이름이 초 단위라 같은 초에 끝나면 서로 덮어쓴다.

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
| `follow_up` | 이전 대화에 이어지는 질문("그럼…", "그 사람들은…")을 맥락대로 답하는가 | 가리키는 대상을 바르게 이어받고 `in_doc`과 같음 |
| `unreadable_doc` | 대화방 문서를 읽지 못했을 때(`document_unreadable: true`, `documents: []`) 문서 내용을 지어내지 않는가 | 문서를 읽지 못해 확인할 수 없다고 밝힘. "문서에 없다"고 단정하면 틀림 |

문항에 `history`(이전 대화, `{"role": "user" | "assistant", "content": ...}`를 학생부터 번갈아)를 넣으면, 서비스와 같은 방식으로 이전 대화를 붙여 튜터에게 보내고 judge에게도 보여 준다. 이전 대화의 튜터 답은 문서대로 맞게 써 둔 고정 문장이다. `follow_up`이 아닌 유형(예: `out_of_doc`)에도 쓸 수 있다.

어떤 문서를 메시지에 넣는지(예: 파일 없이 이어서 한 질문에 채팅방 문서를 넣는 것)는 DB를 거치는 서비스 로직이므로 `test/service/test_handle_chat_request_service.py`에서 검사한다.

`long_doc` 문항의 `anchor`는 답의 위치를 표시한다(12,000자 뒤). 서비스는 12,000자가 넘는 문서를 앞에서 자르지 않고, 질문(과 직전 질문)과 겹치는 부분을 골라 12,000자 안에 담는다(`app/backend/service/document_context_service.py`).

- `long-001`: 학습지 5개(약 12,900자). 12,000자를 조금 넘을 뿐이라 답이 있는 마지막 부분만 넘치는 경우다.
- `long-002`: 학습지 5개 사이에 가정통신문 모음(`school_life_guide.md`)을 끼운 약 18,700자. 답(교외 체험학습)은 가운데에 있고, 비슷한 낱말(신청, 기한, 제출)을 쓰는 항목이 여럿이며, 질문은 문서 낱말을 그대로 쓰지 않는다('가족 여행 때문에 학교를 빠지려고'). 고르는 방식이 맞는 항목을 찾는지 본다.

이보다 훨씬 긴 문서는 `test/service/test_document_context_service.py`에서 검사한다.

## 채점

judge 모델(기본 `gpt-4o`, `EVAL_JUDGE_MODEL`)이 문항마다 세 항목을 true/false로 판정하고 근거를 남긴다.

- `correct`: 유형별 기준(위 표)
- `unsupported_claim`: 다음 중 하나라도 해당함
  - 문서와 어긋나는 말을 함
  - 문서에 없는 사실(문서 용어에 덧붙인 설명 포함)을 문서 밖 지식이라고 밝히지 않고 말함
  - 문서 밖 지식이라고 밝혔지만 사실과 다름. judge가 대조할 수 있도록 `expected`에 "(참고 사실: ...)"을 적어 둔다
- `persona_violation`: `persona_check`를 지키지 않음

셋 다 통과해야 pass다. judge 응답을 해석하지 못하면 `judge_error`로 세고 통과로 치지 않는다.

## 규칙

- 답변 모델·judge 모델·judge 버전·프롬프트 버전이 다른 점수끼리 섞지 않는다. 결과 파일에 넷이 함께 남는다.
- 평가 문항과 학습지를 프롬프트 예시로 쓰지 않는다.
- judge는 답변 모델보다 강한 모델을 쓴다. 같은 모델이 자기 답을 채점하면 점수가 후해진다.
- 문항을 고치면 `cases_version`이 바뀐다. 이전 결과와 비교할 때 확인한다.
