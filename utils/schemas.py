from pydantic import BaseModel

class Response(BaseModel):
    data: str | list | dict | None = None
    error: str | None = None

class Token(BaseModel):
    token: str | None = None
    error: str | None = None