import requests
from pydantic import BaseModel, EmailStr, Field



class test_class(BaseModel):
    name: str | None = Field(default=None)
    email: EmailStr | None = Field(default=None)
    password: str | None = Field(default=None)
    id: str | None = Field(default=None)
    token: str | None = Field(default=None)
    role: str | None = Field(default=None)
    headers : dict | None = Field(default=None)
    
    
    def get_request(self, url, include_fields):
        pass

    def post_request(self, url, include_fields: set[str] | None = None, **kwargs):
        if include_fields:
            payload = self.model_dump(include=include_fields)
        else:
            payload = self.model_dump() 
        
        response = requests.post(url, json=payload)
        return response
    
    def request_get(self, url, include_fields: set[str] | None = None, 
                    params: set[dict] | None= None,
                    headers: set[dict] | None= None ):
        if include_fields:
            payload = self.model_dump(include=include_fields)
        else:
            pass
        response = requests.get(url, params=params, headers=headers)
        return response




