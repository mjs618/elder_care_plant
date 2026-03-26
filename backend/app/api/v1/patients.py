"""
患者管理API - 统一入口
从模块化路由导入，保持向后兼容
"""
from modules.patient_mgmt.api.routes import router

__all__ = ["router"]
