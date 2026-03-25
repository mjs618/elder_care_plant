"""
Elder Care Platform - Module Registry
The plugin/component registry is the heart of the modular architecture.
Each business module self-registers here with its slug, display name,
included permission codes, and its APIRouter.

The platform CoreEngine uses this registry to:
  - Dynamically mount routers
  - Validate tenant module licenses
  - Generate the frontend's navigation config payload
"""
from dataclasses import dataclass, field
from fastapi import APIRouter


@dataclass
class NavChild:
    title: str
    path: str


@dataclass
class UIMeta:
    icon: str
    path: str
    children: list[NavChild] = field(default_factory=list)


@dataclass
class ModuleDefinition:
    slug: str
    display_name: str
    description: str = ""
    version: str = "1.0.0"
    permissions: list[str] = field(default_factory=list)
    router: APIRouter | None = None
    router_prefix: str = ""
    router_tags: list[str] = field(default_factory=list)
    ui_meta: UIMeta | None = None


class ModuleRegistry:
    """Singleton registry for all pluggable business modules."""

    def __init__(self):
        self._modules: dict[str, ModuleDefinition] = {}

    def register(self, module: ModuleDefinition) -> None:
        if module.slug in self._modules:
            raise ValueError(f"Module '{module.slug}' is already registered")
        self._modules[module.slug] = module

    def get(self, slug: str) -> ModuleDefinition | None:
        return self._modules.get(slug)

    def all(self) -> list[ModuleDefinition]:
        return list(self._modules.values())

    def all_slugs(self) -> list[str]:
        return list(self._modules.keys())

    def all_permissions(self) -> list[str]:
        perms: list[str] = []
        for mod in self._modules.values():
            perms.extend(mod.permissions)
        return perms


# Global singleton — import this throughout the app
module_registry = ModuleRegistry()


# ── Built-in module definitions (will be auto-registered on startup) ──────────

CORE_MODULES: list[ModuleDefinition] = [
    ModuleDefinition(
        slug="patient_mgmt",
        display_name="患者管理",
        description="患者基本信息、健康档案、照护等级管理",
        permissions=["patient:read", "patient:write", "patient:delete"],
        router_prefix="/api/v1/patients",
        router_tags=["患者管理"],
        ui_meta=UIMeta(
            icon="User",
            path="/patients",
            children=[
                NavChild(title="患者列表", path="/patients/list"),
                NavChild(title="健康档案", path="/patients/health-records"),
            ],
        ),
    ),
    ModuleDefinition(
        slug="assessment",
        display_name="认知评估",
        description="MMSE、CDR、MoCA等专业量表评估与记录",
        permissions=["assessment:read", "assessment:write", "assessment:delete"],
        router_prefix="/api/v1/assessments",
        router_tags=["认知评估"],
        ui_meta=UIMeta(
            icon="EditPen",
            path="/assessments",
            children=[
                NavChild(title="评估列表", path="/assessments/list"),
                NavChild(title="新增评估", path="/assessments/new"),
            ],
        ),
    ),
    ModuleDefinition(
        slug="health_monitoring",
        display_name="健康监测",
        description="生命体征、用药记录、运动康复追踪",
        permissions=["health:read", "health:write"],
        router_prefix="/api/v1/health",
        router_tags=["健康监测"],
        ui_meta=UIMeta(
            icon="Monitor",
            path="/health",
            children=[
                NavChild(title="生命体征", path="/health/vitals"),
                NavChild(title="用药管理", path="/health/medications"),
            ],
        ),
    ),
    ModuleDefinition(
        slug="ai_chat",
        display_name="AI智能助理",
        description="基于大语言模型的健康问答与智能建议",
        permissions=["ai_chat:use"],
        router_prefix="/api/v1/ai",
        router_tags=["AI智能"],
        ui_meta=UIMeta(
            icon="ChatLineRound",
            path="/ai",
            children=[
                NavChild(title="AI健康问答", path="/ai/chat"),
            ],
        ),
    ),
    ModuleDefinition(
        slug="knowledge_base",
        display_name="知识库",
        description="护理文档审核、版本控制与向量检索",
        permissions=["knowledge:read", "knowledge:write", "knowledge:review"],
        router_prefix="/api/v1/knowledge",
        router_tags=["知识库"],
        ui_meta=UIMeta(
            icon="Reading",
            path="/knowledge",
            children=[
                NavChild(title="知识文档", path="/knowledge/docs"),
                NavChild(title="知识审核", path="/knowledge/review"),
            ],
        ),
    ),
    ModuleDefinition(
        slug="learning_center",
        display_name="学习中心",
        description="课程管理、考试系统与学习路径规划",
        permissions=["learning:read", "learning:write", "learning:manage"],
        router_prefix="/api/v1/learning",
        router_tags=["学习中心"],
        ui_meta=UIMeta(
            icon="Memo",
            path="/learning",
            children=[
                NavChild(title="课程中心", path="/learning/courses"),
                NavChild(title="考试中心", path="/learning/exams"),
            ],
        ),
    ),
    ModuleDefinition(
        slug="reservation",
        display_name="预约服务",
        description="养老机构参观预约与探视管理",
        permissions=["reservation:read", "reservation:write"],
        router_prefix="/api/v1/reservations",
        router_tags=["预约服务"],
        ui_meta=UIMeta(
            icon="Calendar",
            path="/reservations",
        ),
    ),
    ModuleDefinition(
        slug="care_facility",
        display_name="养老机构",
        description="机构信息展示、地图定位与PostGIS空间检索",
        permissions=["facility:read", "facility:write"],
        router_prefix="/api/v1/facilities",
        router_tags=["养老机构"],
        ui_meta=UIMeta(
            icon="OfficeBuilding",
            path="/facilities",
        ),
    ),
]
