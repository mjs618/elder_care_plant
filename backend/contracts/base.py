"""
模块契约基类
定义模块间通信的标准化接口规范
"""
from pydantic import BaseModel, Field
from typing import Optional, ClassVar
from datetime import datetime
from enum import Enum


class ContractVersion(str, Enum):
    """契约版本枚举"""
    V1 = "1.0"
    V2 = "2.0"


class BaseContract(BaseModel):
    """
    契约基类
    所有模块对外接口都应继承此类
    """
    
    contract_version: ClassVar[str] = ContractVersion.V1.value
    
    id: str = Field(..., description="资源唯一标识")
    
    tenant_id: Optional[str] = Field(None, description="租户ID")
    
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    class Config:
        extra = "allow"
        use_enum_values = True


class ContractClient:
    """
    契约客户端基类
    用于模块间HTTP调用
    """
    
    def __init__(self, base_url: str, module_name: str):
        self.base_url = base_url.rstrip("/")
        self.module_name = module_name
    
    async def _request(
        self, 
        method: str, 
        path: str, 
        **kwargs
    ) -> dict:
        """
        发送HTTP请求
        """
        import httpx
        
        url = f"{self.base_url}{path}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method, 
                url, 
                timeout=30.0,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
    
    async def get(self, path: str, **kwargs) -> dict:
        return await self._request("GET", path, **kwargs)
    
    async def post(self, path: str, **kwargs) -> dict:
        return await self._request("POST", path, **kwargs)
    
    async def put(self, path: str, **kwargs) -> dict:
        return await self._request("PUT", path, **kwargs)
    
    async def delete(self, path: str, **kwargs) -> dict:
        return await self._request("DELETE", path, **kwargs)
