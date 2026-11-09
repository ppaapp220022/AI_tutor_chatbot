import pytest
from loguru import logger

from app.backend.repository.user_repository import create_users, find_user_id
from app.backend.model.users import Users, Role
from app.backend.schema.users_schema import UserRequest, UsersActiveRequest
from app.backend.service.user_service import (
    add_user,
    modify_user,
    modify_active_user,
    get_user_all,
    pwd_encoding,
)


# 테스트용 유저 생성 헬퍼
def make_user_request(login_id='test', password='password123', email='test@test.com') -> UserRequest:
    return UserRequest(login_id=login_id, password=password, email=email)


def make_user(db, login_id='test', password='hashed_password', email='test@test.com'):
    user = Users(login_id=login_id, password=password, email=email, role=Role.USER)
    return create_users(db, user)


# 회원가입 - 성공
def test_add_user(db):
    # given
    request = make_user_request()

    # when
    user = add_user(db, request)

    # then
    assert user is not None
    assert user.login_id == 'test'
    assert user.email == 'test@test.com'
    assert user.is_active


# 회원가입 - 중복 아이디
def test_add_user_duplicate(db):
    # given
    add_user(db, make_user_request())

    # when & then
    with pytest.raises(ValueError, match='이미 존재 하는 아이디 입니다.'):
        add_user(db, make_user_request())


# 회원가입 - 비밀번호 암호화 확인
def test_add_user_password_encrypted(db):
    # given
    request = make_user_request()

    # when
    add_user(db, request)

    # then - DB에서 직접 조회해서 암호화 확인
    db_user = find_user_id(db, 'test')
    assert db_user.password != 'password123'  # 암호화 됐는지 확인


# 회원 정보 수정 - 성공
def test_modify_user(db):
    # given
    add_user(db, make_user_request())
    update_request = UserRequest(login_id='test', password='new_password123', email='new@test.com')

    # when
    updated = modify_user(db, update_request)

    # then
    assert updated is not None
    assert updated.email == 'new@test.com'


# 회원 정보 수정 - 존재하지 않는 유저
def test_modify_user_not_found(db):
    # given
    request = UserRequest(login_id='없는유저', password='1234', email='test@test.com')

    # when & then
    with pytest.raises(ValueError):
        modify_user(db, request)


# 회원 정보 수정 - 비밀번호는 그대로, 이메일만 변경
def test_modify_user_same_password(db):
    # given
    add_user(db, make_user_request())
    same_password_request = UserRequest(login_id='test', password='password123', email='new@test.com')

    # when
    updated = modify_user(db, same_password_request)

    # then
    assert updated.email == 'new@test.com'
    assert pwd_encoding.verify('password123', find_user_id(db, 'test').password)


# 회원 정보 수정 - 이메일은 그대로, 비밀번호만 변경
def test_modify_user_same_email(db):
    # given
    add_user(db, make_user_request())
    same_email_request = UserRequest(login_id='test', password='new_password123', email='test@test.com')

    # when
    updated = modify_user(db, same_email_request)

    # then
    assert updated.email == 'test@test.com'
    assert pwd_encoding.verify('new_password123', find_user_id(db, 'test').password)


# 회원 정보 수정 - 비밀번호와 이메일 모두 그대로
def test_modify_user_nothing_changed(db):
    # given
    add_user(db, make_user_request())
    same_request = UserRequest(login_id='test', password='password123', email='test@test.com')

    # when & then
    with pytest.raises(ValueError):
        modify_user(db, same_request)


# 활성화 상태 변경 - 단건
def test_modify_active_user_single(db):
    # given
    user = make_user(db)
    request = UsersActiveRequest(user_idx=[user.id], is_active=False)

    # when
    count = modify_active_user(db, request)

    # then
    assert count == 1
    updated = find_user_id(db, 'test')
    assert updated is not None
    assert not updated.is_active


# 활성화 상태 변경 - 다건
def test_modify_active_user_multiple(db):
    # given
    user1 = make_user(db, 'test1', 'pw1', 'test1@test.com')
    user2 = make_user(db, 'test2', 'pw2', 'test2@test.com')
    request = UsersActiveRequest(user_idx=[user1.id, user2.id], is_active=False)

    # when
    count = modify_active_user(db, request)

    # then
    assert count == 2
    user1_updated = find_user_id(db, 'test1')
    user2_updated = find_user_id(db, 'test2')
    assert user1_updated is not None
    assert user2_updated is not None
    assert not user1_updated.is_active
    assert not user2_updated.is_active


def test_get_user_all(db):
    make_user(db, 'test1', 'pw1', 'test1@test.com')
    make_user(db, 'test2', 'pw2', 'test2@test.com')
    users = get_user_all(db)
    for u in users:
        logger.info(u)
    assert users