from pydantic import BaseModel

class AuthorizationBody(BaseModel):
    account_id: int
    two_fa_status: bool
    role: str

class AuthorizationResponse(BaseModel):
    access_token: str
    refresh_token: str

class CheckAuthorizationResponse(BaseModel):
    account_id: int
    two_fa_status: bool
    role: str
    message: str