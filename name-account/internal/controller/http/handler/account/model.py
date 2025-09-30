from pydantic import BaseModel, EmailStr
from typing import Optional


class RegisterBody(BaseModel):
    login: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "login": "user@example.com",
                "password": "securePassword123"
            }
        }


class LoginBody(BaseModel):
    login: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "login": "user@example.com",
                "password": "securePassword123"
            }
        }


class SetTwoFaBody(BaseModel):
    google_two_fa_key: str
    google_two_fa_code: str

    class Config:
        json_schema_extra = {
            "example": {
                "google_two_fa_key": "JBSWY3DPEHPK3PXP",
                "google_two_fa_code": "123456"
            }
        }


class DeleteTwoFaBody(BaseModel):
    google_two_fa_key: str

    class Config:
        json_schema_extra = {
            "example": {
                "google_two_fa_key": "123456"
            }
        }


class VerifyTwoFaBody(BaseModel):
    google_two_fa_code: str

    class Config:
        json_schema_extra = {
            "example": {
                "google_two_fa_code": "123456"
            }
        }


class RecoveryPasswordBody(BaseModel):
    new_password: str

    class Config:
        json_schema_extra = {
            "example": {
                "new_password": "newSecurePassword123"
            }
        }


class ChangePasswordBody(BaseModel):
    old_password: str
    new_password: str

    class Config:
        json_schema_extra = {
            "example": {
                "old_password": "oldPassword123",
                "new_password": "newSecurePassword123"
            }
        }


# Response models
class RegisterResponse(BaseModel):
    message: str
    account_id: int


class LoginResponse(BaseModel):
    message: str
    account_id: int


class TwoFaResponse(BaseModel):
    message: str


class VerifyTwoFaResponse(BaseModel):
    message: str
    is_valid: bool


class PasswordResponse(BaseModel):
    message: str