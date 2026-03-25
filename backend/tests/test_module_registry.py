"""
模块注册和路由测试
验证模块注册中心的正确性和路由挂载
"""
import pytest
from unittest.mock import MagicMock

from app.core.module_registry import ModuleRegistry, ModuleDefinition, UIMeta, NavChild


class TestModuleRegistry:
    """模块注册中心测试"""
    
    def test_register_module(self):
        """测试模块注册"""
        registry = ModuleRegistry()
        module = ModuleDefinition(
            slug="test_module",
            display_name="测试模块",
            description="测试用模块",
        )
        
        registry.register(module)
        
        assert registry.get("test_module") == module
        assert "test_module" in registry.all_slugs()
    
    def test_register_duplicate_module_raises_error(self):
        """测试重复注册模块抛出异常"""
        registry = ModuleRegistry()
        module = ModuleDefinition(
            slug="test_module",
            display_name="测试模块",
        )
        
        registry.register(module)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register(module)
    
    def test_get_nonexistent_module(self):
        """测试获取不存在的模块"""
        registry = ModuleRegistry()
        
        result = registry.get("nonexistent")
        
        assert result is None
    
    def test_all_modules(self):
        """测试获取所有模块"""
        registry = ModuleRegistry()
        module1 = ModuleDefinition(slug="module1", display_name="模块1")
        module2 = ModuleDefinition(slug="module2", display_name="模块2")
        
        registry.register(module1)
        registry.register(module2)
        
        all_modules = registry.all()
        
        assert len(all_modules) == 2
        assert module1 in all_modules
        assert module2 in all_modules
    
    def test_all_permissions(self):
        """测试获取所有权限"""
        registry = ModuleRegistry()
        module1 = ModuleDefinition(
            slug="module1",
            display_name="模块1",
            permissions=["read", "write"],
        )
        module2 = ModuleDefinition(
            slug="module2",
            display_name="模块2",
            permissions=["admin"],
        )
        
        registry.register(module1)
        registry.register(module2)
        
        permissions = registry.all_permissions()
        
        assert "read" in permissions
        assert "write" in permissions
        assert "admin" in permissions
        assert len(permissions) == 3


class TestModuleDefinition:
    """模块定义测试"""
    
    def test_module_definition_defaults(self):
        """测试模块定义默认值"""
        module = ModuleDefinition(
            slug="test",
            display_name="测试模块",
        )
        
        assert module.description == ""
        assert module.version == "1.0.0"
        assert module.permissions == []
        assert module.router is None
        assert module.router_prefix == ""
        assert module.router_tags == []
        assert module.ui_meta is None
    
    def test_module_definition_with_ui_meta(self):
        """测试带UI元数据的模块定义"""
        module = ModuleDefinition(
            slug="test",
            display_name="测试模块",
            ui_meta=UIMeta(
                icon="User",
                path="/test",
                children=[
                    NavChild(title="子页面", path="/test/child"),
                ],
            ),
        )
        
        assert module.ui_meta is not None
        assert module.ui_meta.icon == "User"
        assert module.ui_meta.path == "/test"
        assert len(module.ui_meta.children) == 1
        assert module.ui_meta.children[0].title == "子页面"


class TestUIMeta:
    """UI元数据测试"""
    
    def test_ui_meta_creation(self):
        """测试UI元数据创建"""
        ui_meta = UIMeta(
            icon="EditPen",
            path="/assessments",
            children=[
                NavChild(title="评估列表", path="/assessments/list"),
                NavChild(title="新增评估", path="/assessments/new"),
            ],
        )
        
        assert ui_meta.icon == "EditPen"
        assert ui_meta.path == "/assessments"
        assert len(ui_meta.children) == 2
    
    def test_ui_meta_without_children(self):
        """测试无子菜单的UI元数据"""
        ui_meta = UIMeta(
            icon="Calendar",
            path="/reservations",
        )
        
        assert ui_meta.icon == "Calendar"
        assert ui_meta.path == "/reservations"
        assert ui_meta.children == []


class TestCORE_MODULES:
    """核心模块定义测试"""
    
    def test_core_modules_not_empty(self):
        """测试核心模块列表不为空"""
        from app.core.module_registry import CORE_MODULES
        
        assert len(CORE_MODULES) > 0
    
    def test_core_modules_have_required_fields(self):
        """测试核心模块包含必需字段"""
        from app.core.module_registry import CORE_MODULES
        
        for module in CORE_MODULES:
            assert module.slug, f"Module missing slug"
            assert module.display_name, f"Module {module.slug} missing display_name"
            assert module.permissions, f"Module {module.slug} missing permissions"
            assert module.ui_meta is not None, f"Module {module.slug} missing ui_meta"
    
    def test_core_modules_unique_slugs(self):
        """测试核心模块slug唯一"""
        from app.core.module_registry import CORE_MODULES
        
        slugs = [m.slug for m in CORE_MODULES]
        assert len(slugs) == len(set(slugs)), "Duplicate slugs found in CORE_MODULES"
    
    def test_core_modules_ui_meta_paths(self):
        """测试核心模块UI路径格式"""
        from app.core.module_registry import CORE_MODULES
        
        for module in CORE_MODULES:
            if module.ui_meta:
                assert module.ui_meta.path.startswith("/"), \
                    f"Module {module.slug} ui_meta.path should start with /"


class TestModuleRouterMounting:
    """模块路由挂载测试"""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires full app initialization with environment config")
    async def test_module_router_mounted(self):
        """测试模块路由正确挂载"""
        from app.main import create_app
        
        app = create_app()
        routes = [route.path for route in app.routes]
        
        assert "/api/v1/patients" in routes
        assert "/api/v1/assessments" in routes
        assert "/api/v1/auth/login" in routes
        assert "/api/v1/modules" in routes
    
    @pytest.mark.skip(reason="Requires full app initialization with environment config")
    def test_module_api_endpoint_exists(self):
        """测试模块API端点存在"""
        from app.main import create_app
        
        app = create_app()
        
        module_routes = [
            route for route in app.routes
            if hasattr(route, 'path') and route.path.startswith("/api/v1/patients")
        ]
        
        assert len(module_routes) > 0
