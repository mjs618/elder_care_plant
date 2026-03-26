"""
契约注册表
集中管理所有模块契约的注册与发现
"""
from typing import Dict, Type, Optional, List
from dataclasses import dataclass
import structlog

from contracts.base import BaseContract, ContractVersion

logger = structlog.get_logger()


@dataclass
class ContractEntry:
    """契约注册条目"""
    contract_class: Type[BaseContract]
    module_name: str
    version: str
    description: str
    deprecated: bool = False
    successor: Optional[str] = None


class ContractRegistry:
    """
    契约注册表
    提供契约的注册、发现、版本管理功能
    """
    
    _instance: Optional['ContractRegistry'] = None
    _contracts: Dict[str, ContractEntry] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register(
        cls,
        contract_class: Type[BaseContract],
        module_name: str,
        description: str = "",
        deprecated: bool = False,
        successor: Optional[str] = None
    ) -> None:
        """
        注册契约
        
        Args:
            contract_class: 契约类
            module_name: 所属模块名
            description: 契约描述
            deprecated: 是否已废弃
            successor: 废弃后的替代契约名称
        """
        contract_name = contract_class.__name__
        version = getattr(contract_class, 'contract_version', ContractVersion.V1.value)
        
        entry = ContractEntry(
            contract_class=contract_class,
            module_name=module_name,
            version=version,
            description=description,
            deprecated=deprecated,
            successor=successor
        )
        
        cls._contracts[contract_name] = entry
        
        logger.info(
            "contract_registered",
            contract_name=contract_name,
            module=module_name,
            version=version,
            deprecated=deprecated
        )
    
    @classmethod
    def get(cls, contract_name: str) -> Optional[ContractEntry]:
        """获取契约条目"""
        return cls._contracts.get(contract_name)
    
    @classmethod
    def get_contract_class(cls, contract_name: str) -> Optional[Type[BaseContract]]:
        """获取契约类"""
        entry = cls._contracts.get(contract_name)
        return entry.contract_class if entry else None
    
    @classmethod
    def list_contracts(cls, module_name: Optional[str] = None) -> List[ContractEntry]:
        """
        列出所有契约
        
        Args:
            module_name: 可选，按模块过滤
        """
        if module_name:
            return [e for e in cls._contracts.values() if e.module_name == module_name]
        return list(cls._contracts.values())
    
    def deprecate(self, contract_name: str, successor: Optional[str] = None) -> bool:
        """
        标记契约为废弃
        
        Args:
            contract_name: 契约名称
            successor: 替代契约名称
        """
        entry = self._contracts.get(contract_name)
        if entry:
            entry.deprecated = True
            entry.successor = successor
            logger.warning(
                "contract_deprecated",
                contract_name=contract_name,
                successor=successor
            )
            return True
        return False
    
    @classmethod
    def get_module_contracts(cls, module_name: str) -> Dict[str, Type[BaseContract]]:
        """获取模块的所有契约"""
        return {
            name: entry.contract_class
            for name, entry in cls._contracts.items()
            if entry.module_name == module_name
        }


def register_all_contracts():
    """注册所有契约"""
    from contracts.patient_contract import PatientContract, PatientListContract
    from contracts.assessment_contract import AssessmentContract, AssessmentListContract
    
    ContractRegistry.register(
        PatientContract,
        module_name="patient_mgmt",
        description="患者基础信息契约"
    )
    
    ContractRegistry.register(
        PatientListContract,
        module_name="patient_mgmt",
        description="患者列表契约"
    )
    
    ContractRegistry.register(
        AssessmentContract,
        module_name="assessment",
        description="评估记录契约"
    )
    
    ContractRegistry.register(
        AssessmentListContract,
        module_name="assessment",
        description="评估列表契约"
    )
    
    logger.info("all_contracts_registered", count=len(ContractRegistry._contracts))


def get_contract(contract_name: str) -> Optional[Type[BaseContract]]:
    """便捷函数：获取契约类"""
    return ContractRegistry.get_contract_class(contract_name)
