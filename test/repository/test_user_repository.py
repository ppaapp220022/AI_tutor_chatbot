import pytest
from loguru import logger

from app.backend.model.users import Users, Role
from app.backend.repository.user_repository import (
    create_users,
    find_user_id,
    update_user,
    update_users_active,
    delete_user,
    find_user_all,
    find_users_by_chat_message
)


# 테스트용 유저 생성 헬퍼
def make_user(login_id='test', password='1234', email='test@test.com') -> Users:
    return Users(login_id=login_id, password=password, email=email, role=Role.USER)


# 회원가입
def test_create_users(db):
    # given
    user = make_user()

    # when
    created = create_users(db, user)

    # then
    assert created.id is not None
    assert created.login_id == 'test'
    assert created.email == 'test@test.com'
    assert created.role == Role.USER
    assert created.is_active


# 단건 조회 - 존재하는 유저
def test_find_user_id(db):
    # given
    create_users(db, make_user())

    # when
    user = find_user_id(db, 'test')

    # then
    assert user is not None
    assert user.login_id == 'test'


# 단건 조회 - 존재하지 않는 유저
def test_find_user_id_not_found(db):
    # when
    user = find_user_id(db, '없는유저')

    # then
    assert user is None


# 회원 정보 수정
def test_update_user(db):
    # given
    create_users(db, make_user())
    update_data = Users(login_id='test', password='new_password', email='new@test.com')

    # when
    updated = update_user(db, update_data)

    # then
    assert updated is not None
    assert updated.password == 'new_password'
    assert updated.email == 'new@test.com'


# 회원 정보 수정 - 존재하지 않는 유저
def test_update_user_not_found(db):
    # given
    update_data = Users(login_id='없는유저', password='1234', email='test@test.com')

    # when & then
    with pytest.raises(ValueError):
        update_user(db, update_data)


# 활성화 상태 변경 - 단건
def test_update_users_active_single(db):
    # given
    user = create_users(db, make_user())

    # when
    count = update_users_active(db, [user.id], False)

    # then
    assert count == 1
    updated = find_user_id(db, 'test')
    assert updated is not None
    assert not updated.is_active


# 활성화 상태 변경 - 다건
def test_update_users_active_multiple(db):
    # given
    user1 = create_users(db, make_user('test1', '1234', 'test1@test.com'))
    user2 = create_users(db, make_user('test2', '1234', 'test2@test.com'))
    user3 = create_users(db, make_user('test3', '1234', 'test3@test.com'))

    # when
    count = update_users_active(db, [user1.id, user2.id, user3.id], False)

    # then
    assert count == 3
    user1_updated = find_user_id(db, 'test1')
    user2_updated = find_user_id(db, 'test2')
    user3_updated = find_user_id(db, 'test3')
    assert user1_updated is not None
    assert user2_updated is not None
    assert user3_updated is not None
    assert not user1_updated.is_active
    assert not user2_updated.is_active
    assert not user3_updated.is_active


# 회원 삭제
def test_delete_user(db):
    # given
    create_users(db, make_user())

    # when
    result = delete_user(db, 'test')

    # then
    assert result
    assert find_user_id(db, 'test') is None


# 회원 삭제 - 존재하지 않는 유저
def test_delete_user_not_found(db):
    # when
    result = delete_user(db, '없는유저')

    # then
    assert not result


def test_find_user_all(db):
    # given
    create_users(db, make_user('test1', '1234', 'test1@test.com'))
    create_users(db, make_user('test2', '1234', 'test2@test.com'))
    create_users(db, make_user('test3', '1234', 'test3@test.com'))

    user_all = find_user_all(db)
    for users in user_all:
        logger.info(users)

    assert user_all


def test_find_users_by_chat_message(db):
    user_messages = find_users_by_chat_message(db, 'test')
    logger.info(user_messages)
    assert user_messages