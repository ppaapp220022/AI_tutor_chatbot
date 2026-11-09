import os

import pytest
from pathlib import Path
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.backend.database import Base

# 테스트용 DB. 로컬 포트가 다르면 TEST_DATABASE_URL로 바꾼다
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ai_tutor_chatbot_test"
)
engine = create_engine(TEST_DATABASE_URL)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine, checkfirst=True)
    session = TestSessionLocal()
    try :
        yield session # 테스트 세션 전달
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine, checkfirst=True) # 테스트 끝나면 테이블 삭제


@pytest.fixture
def upload_dir():
    upload_path = Path("uploads")
    upload_path.mkdir(parents=True, exist_ok=True)

    for child in upload_path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    try:
        yield upload_path
    finally:
        for child in upload_path.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
