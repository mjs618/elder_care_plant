"""
契约注册表测试
测试契约的注册、发现、版本管理功能
"""
import pytest
from contracts.registry import ContractRegistry, ContractEntry, register_all_contracts, get_contract
from contracts.base import BaseContract, ContractVersion
from contracts.patient_contract import PatientContract, PatientListContract
from contracts.assessment_contract import AssessmentContract, AssessmentListContract


class TestContractRegistry:
    """契约注册表测试"""
    
    def setup_method(self):
        """每个测试方法前清空注册表"""
        ContractRegistry._contracts = {}
    
    def test_register_contract(self):
        """测试契约注册"""
        ContractRegistry.register(
            PatientContract,
            module_name="patient_mgmt",
            description="患者基础信息契约"
        )
        
        entry = ContractRegistry.get("PatientContract")
        
        assert entry is not None
        assert entry.contract_class == PatientContract
        assert entry.module_name == "patient_mgmt"
        assert entry.description == "患者基础信息契约"
        assert entry.deprecated is False
    
    def test_get_contract_class(self):
        """测试获取契约类"""
        ContractRegistry.register(
            PatientContract,
            module_name="patient_mgmt",
            description="患者契约"
        )
        
        contract_class = ContractRegistry.get_contract_class("PatientContract")
        
        assert contract_class == PatientContract
        assert issubclass(contract_class, BaseContract)
    
    def test_get_nonexistent_contract(self):
        """测试获取不存在的契约"""
        entry = ContractRegistry.get("NonExistentContract")
        assert entry is None
        
        contract_class = ContractRegistry.get_contract_class("NonExistentContract")
        assert contract_class is None
    
    def test_list_all_contracts(self):
        """测试列出所有契约"""
        ContractRegistry.register(PatientContract, "patient_mgmt", "患者契约")
        ContractRegistry.register(AssessmentContract, "assessment", "评估契约")
        
        contracts = ContractRegistry.list_contracts()
        
        assert len(contracts) == 2
        contract_names = [c.contract_class.__name__ for c in contracts]
        assert "PatientContract" in contract_names
        assert "AssessmentContract" in contract_names
    
    def test_list_contracts_by_module(self):
        """测试按模块列出契约"""
        ContractRegistry.register(PatientContract, "patient_mgmt", "患者契约")
        ContractRegistry.register(PatientListContract, "patient_mgmt", "患者列表")
        ContractRegistry.register(AssessmentContract, "assessment", "评估契约")
        
        patient_contracts = ContractRegistry.list_contracts(module_name="patient_mgmt")
        
        assert len(patient_contracts) == 2
        for entry in patient_contracts:
            assert entry.module_name == "patient_mgmt"
    
    def test_deprecate_contract(self):
        """测试废弃契约"""
        ContractRegistry.register(
            PatientContract,
            module_name="patient_mgmt",
            description="患者契约"
        )
        
        registry = ContractRegistry()
        result = registry.deprecate("PatientContract", successor="PatientContractV2")
        
        assert result is True
        entry = ContractRegistry.get("PatientContract")
        assert entry.deprecated is True
        assert entry.successor == "PatientContractV2"
    
    def test_deprecate_nonexistent_contract(self):
        """测试废弃不存在的契约"""
        registry = ContractRegistry()
        result = registry.deprecate("NonExistentContract")
        assert result is False
    
    def test_get_module_contracts(self):
        """测试获取模块的所有契约"""
        ContractRegistry.register(PatientContract, "patient_mgmt", "患者契约")
        ContractRegistry.register(PatientListContract, "patient_mgmt", "患者列表")
        ContractRegistry.register(AssessmentContract, "assessment", "评估契约")
        
        patient_contracts = ContractRegistry.get_module_contracts("patient_mgmt")
        
        assert len(patient_contracts) == 2
        assert "PatientContract" in patient_contracts
        assert "PatientListContract" in patient_contracts
    
    def test_contract_version(self):
        """测试契约版本"""
        ContractRegistry.register(
            PatientContract,
            module_name="patient_mgmt",
            description="患者契约"
        )
        
        entry = ContractRegistry.get("PatientContract")
        assert entry.version == ContractVersion.V1.value


class TestRegisterAllContracts:
    """注册所有契约测试"""
    
    def setup_method(self):
        """每个测试方法前清空注册表"""
        ContractRegistry._contracts = {}
    
    def test_register_all_contracts(self):
        """测试注册所有契约"""
        register_all_contracts()
        
        contracts = ContractRegistry.list_contracts()
        
        assert len(contracts) >= 4
        
        contract_names = [c.contract_class.__name__ for c in contracts]
        assert "PatientContract" in contract_names
        assert "PatientListContract" in contract_names
        assert "AssessmentContract" in contract_names
        assert "AssessmentListContract" in contract_names
    
    def test_get_contract_helper(self):
        """测试便捷获取契约函数"""
        register_all_contracts()
        
        patient_contract = get_contract("PatientContract")
        assessment_contract = get_contract("AssessmentContract")
        
        assert patient_contract == PatientContract
        assert assessment_contract == AssessmentContract


class TestContractEntry:
    """契约条目测试"""
    
    def test_contract_entry_creation(self):
        """测试契约条目创建"""
        entry = ContractEntry(
            contract_class=PatientContract,
            module_name="patient_mgmt",
            version="1.0",
            description="患者契约"
        )
        
        assert entry.contract_class == PatientContract
        assert entry.module_name == "patient_mgmt"
        assert entry.version == "1.0"
        assert entry.description == "患者契约"
        assert entry.deprecated is False
        assert entry.successor is None
    
    def test_contract_entry_with_deprecation(self):
        """测试带废弃信息的契约条目"""
        entry = ContractEntry(
            contract_class=PatientContract,
            module_name="patient_mgmt",
            version="1.0",
            description="患者契约",
            deprecated=True,
            successor="PatientContractV2"
        )
        
        assert entry.deprecated is True
        assert entry.successor == "PatientContractV2"


class TestContractRegistrySingleton:
    """契约注册表单例测试"""
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        registry1 = ContractRegistry()
        registry2 = ContractRegistry()
        
        assert registry1 is registry2
    
    def test_shared_state(self):
        """测试共享状态"""
        ContractRegistry._contracts = {}
        
        registry1 = ContractRegistry()
        registry2 = ContractRegistry()
        
        registry1.register(PatientContract, "patient_mgmt", "患者契约")
        
        entry = registry2.get("PatientContract")
        assert entry is not None
