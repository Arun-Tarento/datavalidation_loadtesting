from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Set, Any
from playwright.sync_api import APIRequestContext

class test_class(BaseModel):
    name: Optional[str] = Field(default=None)
    email: Optional[EmailStr] = Field(default=None)
    password: Optional[str] = Field(default=None)
    id: Optional[str] = Field(default=None)
    token: Optional[str] = Field(default=None)
    role: Optional[str] = Field(default=None)
    headers: Optional[dict] = Field(default=None)
    api_key: Optional[str] = Field(default=None)

    def get_request(self, request_ctx: APIRequestContext, url:str,include_fields: Optional[Set[str]] = None,
                    params: Optional[dict] = None,
                    headers: Optional[dict] = None): 
        if include_fields:
            payload = self.model_dump(include=include_fields)
        else:
            payload = self.model_dump()
        response = request_ctx.get(url, params=params, headers=headers)
        return response

    def post_request(self, request_ctx: APIRequestContext, url: str,
                     include_fields: Optional[Set[str]] = None,
                     headers: Optional[dict] = None, json_body: Any | None = None, **kwargs):
        if json_body is not None:
            payload = json_body
        elif include_fields:
            payload = self.model_dump(include=include_fields)
        else:
            payload = self.model_dump()
        response = request_ctx.post(url, data=payload, headers=headers, **kwargs)
        return response