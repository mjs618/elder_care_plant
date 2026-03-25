"""
模块契约包
提供模块间通信的标准化接口
"""
from typing import Dict, Type
from contracts.base import BaseContract, ContractClient


_contract_registry: Dict[str, Type[BaseContract]] = {}
_client_registry: Dict[str, Type[ContractClient]] = {}


def register_contract(module_slug: str, contract_class: Type[BaseContract]):
    """注册模块契约"""
    _contract_registry[module_slug] = contract_class


def register_client(module_slug: str, client_class: Type[ContractClient]):
    """注册模块客户端"""
    _client_registry[module_slug] = client_class


def get_contract(module_slug: str) -> Type[BaseContract]:
    """获取模块契约类"""
    if module_slug not in _contract_registry:
        raise KeyError(f"Contract not found for module: {module_slug}")
    return _contract_registry[module_slug]


def get_client(module_slug: str) -> Type[ContractClient]:
    """获取模块客户端类"""
    if module_slug not in _client_registry:
        raise KeyError(f"Client not found for module: {module_slug}")
    return _client_registry[module_slug]


from contracts.patient_contract import PatientContract, PatientClient
from contracts.assessment_contract import AssessmentContract, AssessmentClient

register_contract("patient_mgmt", PatientContract)
register_client("patient_mgmt", PatientClient)
register_contract("assessment", AssessmentContract)
register_client("assessment", AssessmentClient)

__all__ = [
    "BaseContract",
    "ContractClient",
    "PatientContract",
    "PatientClient",
    "AssessmentContract",
    "AssessmentClient",
    "register_contract",
    "register_client",
    "get_contract",
    "get_client",
]
