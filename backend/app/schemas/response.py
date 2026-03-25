"""
Elder Care Platform - Unified API Response Schema
Standardizes all API responses to: {code, message, data, meta?}

Usage:
    from app.schemas.response import ok, created, error, paginated

    @router.get("/items")
    async def list_items():
        items = await get_items()
        return ok(items)

    @router.post("/items")
    async def create_item(body: ItemCreate):
        item = await create(body)
        return created(item)
"""
from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ResponseSchema(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: T | None = None


class PaginatedMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: list[T] = []
    meta: PaginatedMeta


def ok(data: Any = None, message: str = "success") -> dict:
    """成功响应"""
    return {"code": 200, "message": message, "data": data}


def created(data: Any = None, message: str = "created") -> dict:
    """创建成功响应"""
    return {"code": 201, "message": message, "data": data}


def error(code: int = 400, message: str = "error", data: Any = None) -> dict:
    """错误响应"""
    return {"code": code, "message": message, "data": data}


def paginated(items: list, total: int, page: int, page_size: int, message: str = "success") -> dict:
    """分页响应"""
    return {
        "code": 200,
        "message": message,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "size": page_size,
        },
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        },
    }


def deleted(message: str = "deleted") -> dict:
    """删除成功响应"""
    return {"code": 200, "message": message, "data": None}
