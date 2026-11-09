import os

import pytest
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.backend.database import Base
from app.backend.service import uploaded_files_service

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


@pytest.fixture(autouse=True)
def upload_dir(tmp_path, monkeypatch):
    # 테스트에서 올린 파일은 실제 uploads 폴더가 아니라 테스트용 임시 폴더에 저장하고, 끝나면 비운다
    upload_path = tmp_path / "uploads"
    upload_path.mkdir()
    monkeypatch.setattr(uploaded_files_service, "UPLOAD_DIR", upload_path)

    try:
        yield upload_path
    finally:
        shutil.rmtree(upload_path, ignore_errors=True)
