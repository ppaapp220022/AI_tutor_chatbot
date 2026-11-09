from fastapi import status

class AppException(Exception):
    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code

class BadRequestException(AppException):
    def __init__(self, detail: str):
        super().__init__(detail, status.HTTP_400_BAD_REQUEST)

class NotFoundException(AppException):
    def __init__(self, detail: str):
        super().__init__(detail, status.HTTP_404_NOT_FOUND)

class DatabaseException(AppException):
    def __init__(self, detail: str = "데이터베이스 오류가 발생했습니다."):
        super().__init__(detail, status.HTTP_500_INTERNAL_SERVER_ERROR)

class ExternalServiceException(AppException):
    def __init__(self, detail: str = "외부 서비스 처리 중 오류가 발생했습니다."):
        super().__init__(detail, status.HTTP_502_BAD_GATEWAY)
class TooManyRequestsException(AppException):
    def __init__(self, detail: str):
        super().__init__(detail, status.HTTP_429_TOO_MANY_REQUESTS)
