from pydantic import BaseModel


class UploadImageResponse(BaseModel):
    message: str
    user_id: int
    profile_image: str


class UserProfileResponse(BaseModel):
    user_id: int
    username: str
    name: str
    email: str
    profile_image: str

class UpdateUserRequest(BaseModel):
    username: str | None = None
    name: str | None = None

class UserProfileResponse(BaseModel):
    user_id: int
    username: str
    name: str
    email: str        
    profile_image: str | None = None