# 🤖 AI Tutor Chatbot

> AI 도우미 학습용 챗봇 서비스

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?style=flat&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red?style=flat)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-blue?style=flat&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-8.0-DC382D?style=flat&logo=redis&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-API-412991?style=flat&logo=openai&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.57-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI-499848?style=flat)

---

## 목차

- [프로젝트 소개](#프로젝트-소개)
- [기간](#기간)
- [팀원 소개](#팀원-소개)
- [기술 스택](#기술-스택)
- [기술 의사결정](#기술-의사결정)
- [주요 기능](#주요-기능)
- [프로젝트 구조](#프로젝트-구조)
- [ERD](#erd)
- [API 명세](#api-명세)
- [AI 답변 평가](#ai-답변-평가)
- [환경 설정](#환경-설정)
- [트러블슈팅](#트러블슈팅)
- [소감문](#소감문)

---

## 프로젝트 소개

AI Tutor Chatbot은 사용자가 PDF 문서를 업로드하고 페르소나를 선택하여 문서 내용 기반으로 AI와 대화할 수 있는 학습 보조 챗봇 서비스입니다.

Spring Boot 기반 개발 경험을 바탕으로 Python 생태계로 전환하며 FastAPI, SQLAlchemy, Streamlit 등 Python 웹 프레임워크를 학습하고 적용하는 것을 목표로 진행한 팀 프로젝트입니다.

백엔드는 FastAPI로 REST API를 구성하고 JWT 인증, Redis 기반 OTP 관리, OpenAI API 연동을 구현하였으며 프론트엔드는 Streamlit으로 별도의 HTML/CSS/JS 없이 Python만으로 UI를 구성하였습니다.

---

## 기간

26-05-25 ~ 26-06-08

---

## 팀원 소개

| 이름  | 담당                                                                                         |
|-----|--------------------------------------------------------------------------------------------|
| 김준용 | DB 설계, 회원 도메인 (모델, 레파짓토리, 서비스, 라우터), JWT 인증, OTP 이메일 인증 (Redis), 관리자 기능, Streamlit UI 구현 |
| 김민기 | 채팅 관련 도메인 및 관련 서비스 로직 구현 (채팅, 메시지, 파일 업로드), 페이징 처리, 예외처리 구현                                |

---

## 기술 스택

| 분류       | 기술                        | 버전                          |
|----------|---------------------------|-----------------------------|
| Language | Python                    | 3.12                        |
| Backend  | FastAPI                   | 0.136.3                     |
| ORM      | SQLAlchemy                | 2.0.49                      |
| Database | PostgreSQL                | 17                          |
| Cache    | Redis                     | 7.2.14                      |
| AI       | OpenAI API                | 2.38.0                      |
| Frontend | Streamlit                 | 1.57.0                      |
| Server   | Uvicorn                   | 0.47.0                      |
| Auth     | python-jose (JWT)         | 3.5.0                       |
| Tools    | Ruff / Mypy / Pytest / uv | 0.15.15 / 2.1.0 / 9.0.3 / - |

---

## 기술 의사결정

### FastAPI
Spring Boot 경험을 바탕으로 Python 웹 프레임워크를 선택하는 과정에서 Django, Flask, FastAPI 세 가지를 비교하였다. Django는 풀스택 프레임워크로 기능이 방대하여 소규모 프로젝트에 오버스펙이라고 판단하였고 Flask는 기능이 너무 최소화되어 있었다. FastAPI는 Spring Boot와 유사한 레이어 구조를 가지면서도 비동기 처리를 기본으로 지원하고 Swagger 문서가 자동 생성되어 API 개발에 적합하다고 판단하여 선택하였다.

### SQLAlchemy
Python ORM 중 Django ORM과 SQLAlchemy를 비교하였다. Django ORM은 Django 프레임워크에 종속적이어서 FastAPI와 조합이 어색했고 SQLAlchemy는 프레임워크에 독립적으로 사용할 수 있으며 JPA와 유사한 방식으로 동작하여 기존 Java 경험을 살릴 수 있다고 판단하여 선택하였다.

### PostgreSQL
관계형 데이터베이스 중 MariaDB와 PostgreSQL을 비교하였다. 두 DB 모두 사용 경험이 있었으나 PostgreSQL이 JSON 타입, AI 관련 확장성을 고려했을 때 적합하다고 판단하였다.

### Redis
OTP 인증코드 관리를 위해 도입하였다. OTP는 짧은 TTL(만료 시간)이 필요하고 빠른 읽기/쓰기가 요구되는 특성상 인메모리 DB인 Redis가 가장 적합하다고 판단하였다.

### Streamlit
Python만으로 UI를 구성할 수 있어 별도의 프론트엔드 언어 없이 빠르게 화면을 구성할 수 있다는 점에서 선택하였다. 다만 실제 사용 과정에서 브라우저 직접 API 요청이 불가능하고 컴포넌트 자유도가 낮아 React에 비해 제약이 많다는 한계를 경험하였다.

### uv
기존 Python 패키지 관리 도구인 pip + requirements.txt 방식 대신 uv를 도입하였다. 의존성 설치 속도가 pip 대비 월등히 빠르고 pyproject.toml 기반으로 의존성을 관리하여 팀 환경 통일이 용이하다는 점에서 선택하였다.

### 답변 모델 (gpt-4.1-mini)
같은 프롬프트·평가 문항(26개)·judge(gpt-4o)로 세 모델을 3번씩 돌려 비교하였다([AI 답변 평가](#ai-답변-평가)).

| 모델 | 통과 문항 (3번) | 평균 | 문항당 시간 |
|---|---|---|---|
| gpt-4o-mini | 25, 24, 23 | 24.0 | 4.1초 |
| **gpt-4.1-mini** | 25, 26, 24 | 25.0 | 3.8초 |
| gpt-5.4-mini | 26, 25, 25 | 25.3 | 5.1초 |

gpt-5.4-mini가 평균 0.3문항 더 통과했지만 문항당 1초 이상 느려서, 점수와 속도가 함께 좋은 gpt-4.1-mini를 기본값으로 정하였다. `OPENAI_CHAT_MODEL`을 설정하면 다른 모델을 쓸 수 있다.
(prompt 40a384a0f876, judge 692d8b00f787, cases 1667335c2ca6 기준)

---

## 주요 기능

### 회원
- 이메일 OTP 인증을 통한 회원가입
- JWT 기반 로그인 / 로그아웃 (Access Token + Refresh Token)
- 회원 정보 수정
- 내 정보 조회

### 채팅
- 페르소나 선택 후 채팅방 생성
- PDF 파일 업로드 후 문서 기반 AI 응답 (같은 채팅방에서 파일 없이 이어서 질문해도 가장 최근에 올린 문서를 함께 보냄)
- 채팅 이력 조회
- 페르소나(일반 튜터, 수학·영어·과학·역사 전문가)별 지시와, 문서에 없는 내용을 지어내지 않게 하는 공통 지시
- AI 채팅 요청 횟수 제한: 사용자별 1분 5회, 하루 100회 (Redis, 넘으면 429)

### 관리자
- 전체 회원 목록 조회 (페이징)
- 회원 상세 조회
- 회원 채팅 이력 조회
- 회원 계정 활성화 / 비활성화 (단건 / 다건)

---

## 프로젝트 구조

```
ai_tutor_chatbot/
├── app/
│   ├── backend/
│   │   ├── database.py          # DB 및 Redis 연결
│   │   ├── dependencies.py      # JWT 인증 의존성
│   │   ├── exception/           # 전역 예외 처리
│   │   ├── model/               # SQLAlchemy 모델
│   │   │   ├── users.py
│   │   │   ├── chat_room.py
│   │   │   ├── messages.py
│   │   │   └── uploaded_files.py
│   │   ├── repository/          # DB 접근 계층 (DAO)
│   │   ├── router/              # API 엔드포인트 (Controller)
│   │   ├── schema/              # Pydantic 스키마 (DTO)
│   │   ├── service/             # 비즈니스 로직
│   │   └── util/                # 유틸리티 (JWT, Email)
│   ├── evaluation/              # AI 답변 평가 (실행, judge, Batch API)
│   └── frontend/
│       ├── main.py              # Streamlit 진입점
│       └── pages/               # Streamlit 페이지
│           ├── login.py
│           ├── signup.py
│           ├── chat.py
│           └── admin.py
├── test/                        # 테스트 코드
│   ├── evaluation/
│   ├── repository/
│   ├── service/
│   └── util/
├── eval/                        # 평가 문항, 학습지, 결과 (README 있음)
├── db/
│   └── init.sql                 # DB 초기화 SQL
├── logs/                        # 로그 파일
├── main.py                      # FastAPI 진입점
└── pyproject.toml
```

---

## ERD

```
users
├── id (PK)
├── login_id
├── password (BCrypt)
├── email
├── role (USER / ADMIN)
├── is_active
└── created_at

chat_rooms
├── id (PK)
├── member_id (FK → users.id)
├── title
├── persona
└── created_at

messages
├── id (PK)
├── room_id (FK → chat_rooms.id)
├── role (user / assistant)
├── content
└── created_at

uploaded_files
├── id (PK)
├── room_id (FK → chat_rooms.id)
├── file_name
├── file_path
└── created_at
```

---

## API 명세

### 회원 (Public)
| Method | URL               | 설명         |
|--------|-------------------|------------|
| POST   | /users/send-otp   | OTP 이메일 발송 |
| POST   | /users/verify-otp | OTP 검증     |
| POST   | /users/signup     | 회원가입       |
| POST   | /users/login      | 로그인        |
| POST   | /users/refresh    | 액세스 토큰 재발급 |

### 회원 (Private - JWT 필요)
| Method | URL           | 설명       |
|--------|---------------|----------|
| POST   | /users/logout | 로그아웃     |
| PUT    | /users/modify | 회원 정보 수정 |
| GET    | /users/me     | 내 정보 조회  |

### 관리자 (JWT 필요)
| Method | URL                                   | 설명             |
|--------|---------------------------------------|----------------|
| GET    | /admin/member                         | 전체 회원 조회 (페이징) |
| GET    | /admin/member/{login_id}              | 회원 상세 조회       |
| GET    | /admin/member/{login_id}/chat-history | 회원 채팅 이력       |
| PUT    | /admin/member/activate                | 계정 활성화 / 비활성화  |

### 채팅 (JWT 필요)
| Method | URL                 | 설명        |
|--------|---------------------|-----------|
| POST   | /chat-rooms         | 채팅방 생성    |
| GET    | /chat-rooms         | 채팅방 목록 조회 |
| PUT    | /chat-rooms/{id}    | 채팅방 수정    |
| DELETE | /chat-rooms/{id}    | 채팅방 삭제    |
| POST   | /ai-chat            | AI 채팅 요청  |
| GET    | /messages/{room_id} | 메시지 목록 조회 |

---

## AI 답변 평가

프롬프트·모델·문서 처리 방식을 바꿀 때 답변이 좋아졌는지 숫자로 비교하려고 만든 평가 도구다. 자세한 문항 형식과 채점 기준은 [eval/README.md](eval/README.md)에 있다.

- **문항 26개** (`eval/cases.jsonl`): 문서 안 질문 8, 문서 밖 질문 6, 페르소나 4, 이어지는 질문 4, 긴 문서 2, 문서를 읽지 못한 경우 2
- **답변**: 서비스와 같은 함수로 메시지를 만들어 답변 모델에 보낸다 (DB·Redis는 쓰지 않는다)
- **채점**: 답변 모델보다 강한 judge(gpt-4o)가 정답 여부, 근거 없는 주장, 페르소나 위반을 판정한다. 셋 다 통과해야 pass
- **버전**: 결과 파일에 답변 모델·judge 모델·judge 버전·프롬프트 버전·문항 버전이 함께 남고, 버전이 다른 점수끼리는 비교하지 않는다

```bash
uv run python -m app.evaluation.run                        # 전체
uv run python -m app.evaluation.run sci-in-001 long-001    # 일부만
uv run python -m app.evaluation.run --model gpt-4o         # 답변 모델 바꾸기
uv run python -m app.evaluation.run --batch                # Batch API (비용 절반, 결과는 몇 분~최대 24시간 뒤)
```

**현재 기준선**: gpt-4.1-mini, judge gpt-4o, 3번 돌려 25, 25, 26 / 26 (prompt 94c1a636baec, judge 692d8b00f787, cases a3e1da62c1c7)

**알려진 약점 — `sci-persona-001`**: 과학 전문가에게 "더우면 광합성이 왜 줄어드는지" 묻는 문항으로, 생활 속 예시가 빠지면 실패한다. 프롬프트로 예시를 강제해 보았지만 모델이 "더운 날 잎이 시드는 것은 효소 때문"이라는 오개념을 반복하였다(실제로는 주로 수분 손실 때문). 점수를 올리려다 틀린 과학을 가르치게 되어 프롬프트는 되돌리고, 이 문항을 알려진 약점으로 남겨 두었다.

---

## 환경 설정

### .env 설정
```env
DATABASE_URL=postgresql://username:password@localhost:5432/ai_tutor_chatbot
REDIS_HOST=localhost
REDIS_PORT=6379
NAVER_EMAIL=your_email@naver.com
NAVER_PASSWORD=your_password
JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=7
OPENAI_API_KEY=your_openai_api_key
```

선택 값 (없으면 기본값을 쓴다)

| 이름 | 기본값 | 설명 |
|---|---|---|
| `OPENAI_CHAT_MODEL` | `gpt-4.1-mini` | 답변 모델 |
| `AI_CHAT_LIMIT_PER_MINUTE` | `5` | 사용자별 1분 AI 채팅 요청 수. 0이면 제한하지 않음 |
| `AI_CHAT_LIMIT_PER_DAY` | `100` | 사용자별 하루 AI 채팅 요청 수. 0이면 제한하지 않음 |
| `EVAL_JUDGE_MODEL` | `gpt-4o` | 평가 judge 모델 |

공개 배포 전에는 OpenAI 대시보드에서 프로젝트 월 예산(usage limit)도 설정한다. 요청 횟수 제한은 사용자 한 명이 몰아 쓰는 것을 막을 뿐, 전체 비용 상한은 아니다.

### 실행 방법
```bash
# 의존성 설치
uv sync

# 서버 실행 (FastAPI + Streamlit 동시 실행)
uvicorn main:app --reload

# FastAPI  → http://localhost:8000
# Swagger  → http://localhost:8000/docs
# Streamlit → http://localhost:8501
```

---

## 트러블슈팅

---

## 김준용

### 1. FastAPI + SQLAlchemy 2.0 타입 시스템 적응

**문제**

Spring Boot + JPA에 익숙한 상태에서 FastAPI와 SQLAlchemy를 처음 사용하다 보니 타입 시스템에서 다수의 오류 발생

기존 `Column` + 타입힌트 혼용 방식에서 mypy 타입 불일치 오류가 대량 발생하였고 `Optional`, `Mapped`, `mapped_column` 등 SQLAlchemy 2.0 방식에 대한 이해 부족으로 레파짓토리 전반에 걸쳐 타입 오류가 발생하였다

또한 `os.getenv()` 반환값이 `str | None` 임을 고려하지 않아 `create_engine`, JWT 설정 등에서 `None` 가능성으로 인한 타입 오류도 다수 발생하였다

**해결**

SQLAlchemy 2.0 공식 방식인 `Mapped` + `mapped_column` 으로 모델 전체 리팩토링

```python
# 기존
id: int = Column(Integer, primary_key=True)

# 변경
id: Mapped[int] = mapped_column(Integer, primary_key=True)
```

`os.getenv()` 반환값은 `or ''` 처리 또는 None 체크 후 `ValueError` 를 발생시키는 방식으로 통일

---

### 2. Python 정적 분석 도구 도입 (ruff, mypy, pytest)

**문제**

Java는 컴파일 타임에 타입 오류와 문법 오류를 잡아주지만 Python은 컴파일 개념이 없어 런타임에서야 오류를 발견하게 됨

팀 프로젝트 머지 후 서로 다른 방식으로 작성된 코드에서 타입 불일치, 미사용 import, 컨벤션 위반 등의 문제가 발견되었으나 실행 전까지 인지하지 못하는 경우가 많았다

**해결**

`ruff`, `mypy`, `pytest` 를 도입하여 코드 품질을 관리

- `ruff check .` : 코드 스타일 및 미사용 import 검사
- `mypy .` : 정적 타입 검사로 런타임 오류 사전 방지
- `pytest` : 레파짓토리, 서비스, 유틸 단위 테스트

머지 전 3가지 검사를 통과한 코드만 병합하는 방식으로 코드 품질 관리

---

### 3. 브랜치 머지 후 함수 시그니처 불일치

**문제**

브랜치를 나눠 개발하던 중 머지 후 `create_users`, `update_user`, `list_messages_by_room` 등 주요 함수의 시그니처가 서로 달라 테스트 전체가 실패하는 문제 발생

```
TypeError: create_users() takes 2 positional arguments but 4 were given
TypeError: update_user() missing 2 required positional arguments
TypeError: list_messages_by_room() missing 2 required positional arguments: 'offset' and 'limit'
```

**원인**

각자 브랜치에서 함수 시그니처를 변경하면서 상대방 코드와 불일치가 발생하였고 머지 전 사전 협의가 부족했다

**해결**

함수 시그니처를 `Users` 객체 하나를 받는 방식으로 통일하고 테스트 코드의 헬퍼 함수를 공통 방식으로 수정하여 해결

이후 주요 공용 함수의 시그니처 변경 시 사전 협의 후 진행하는 방식으로 개선

---

## 김민기

### 1. 파이썬 디자인 패턴 이해 부족

**문제**

처음 작업하는 python 프로젝트 작업으로 기본 python 지식으론 코딩 작업 한계에 부딪힘

**원인**

이전 프로젝트 설계는 모두 SpringBoot를 사용하였고, 
처음 python 프로그래밍 작업이라 언어에 대한 이해도가 낮은 상태


**해결**

MVC 패턴과 비슷한 MTV 패턴 이해. python 라이브러리 및 import 사용법 이해. 

crud를 시작으로 파이썬 프로그래밍에 천천히 익숙해지기 시작

---

### 2. OpenAI와 PdfReader 등 라이브러리 사용

**문제**

AI chat에 가장 중요한 AI 활용과 PDF 파싱 방법에 대한 이해도 부족

**원인**

처음 파이썬 프로젝트를 운영함으로 라이브러리에 대한 이해도가 부족

필요한 라이브러리 사용과 활용에 대해 이해도가 낮은 상태

**해결**

PdfReader를 통해 pdf 파싱에 대한 import를 선언하여 pdf를 text로 변환 성공

openAI 라이브러리를 활용하여 openAI API 연결하여 챗봇의 답변을 AI에 위임

---

### 3. 테스트 코드 실행과 테스트 방식 이해 부족

**문제**

파이썬의 테스트 코드 방식이 익숙하지 않아 테스트 통과가 되지 않는 문제 발생

**원인**

서비스 작업 후, 테스트시 dummy 데이터가 없는 상태에서 테스트를 시행.

DB(PostgeSQL)에 대한 이해도 부족으로 테스트 지속 실패

**해결**

테스트시 fake dummy 지정 후 테스트 시행.

DB에 데이터가 없더라도 테스트 통과시 정상 작동 확인

---

## 소감문

소감문 = [링크](https://docs.google.com/document/d/1BrK2Oh3BCMM_ngYjlO4e0K0qk4fLVD0JgxAZpNpgiB4/edit?usp=sharing)
