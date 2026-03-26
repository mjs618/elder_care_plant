# 组件化架构文档

## 概述

本文档描述了养老护理平台的组件化架构设计，包括模块结构、契约定义、事件驱动通信和部署方式。

## 架构概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                         主应用 (Main App)                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │ patient_mgmt│  │ assessment  │  │  其他模块   │                   │
│  │   模块      │  │    模块     │  │             │                   │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘                  │
│         │                │                                          │
│         ▼                ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    契约层 (Contracts)                         │   │
│  │  PatientContract, AssessmentContract, ...                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│         │                │                                          │
│         ▼                ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    事件总线 (Event Bus)                        │   │
│  │  RabbitMQ / 内存队列                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## 模块结构

### 患者管理模块 (patient_mgmt)

**目录结构：**
```
backend/modules/patient_mgmt/
├── __init__.py
├── main.py              # 模块入口，可独立运行
├── api/
│   ├── __init__.py
│   └── routes.py        # API路由定义
└── subscribers/
    ├── __init__.py
    └── event_handlers.py # 事件订阅处理器
```

**API端点：**
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/v1/patients | 获取患者列表 |
| GET | /api/v1/patients/{id} | 获取单个患者 |
| POST | /api/v1/patients | 创建患者 |
| PUT | /api/v1/patients/{id} | 更新患者 |
| DELETE | /api/vatients/{id} | 删除患者 |
| GET | /health | 健康检查 |

**独立运行：**
```bash
cd backend
python -m modules.patient_mgmt.main
# 服务运行在 http://localhost:8001
```

### 评估管理模块 (assessment)

**目录结构：**
```
backend/modules/assessment/
├── __init__.py
├── main.py              # 模块入口
├── api/
│   ├── __init__.py
│   └── routes.py        # API路由定义
└── subscribers/
    ├── __init__.py
    └── event_handlers.py # 事件订阅处理器
```

**API端点：**
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/v1/assessments | 获取评估列表 |
| GET | /api/v1/assessments/{id} | 获取单个评估 |
| POST | /api/v1/assessments | 创建评估 |
| PUT | /api/v1/assessments/{id} | 更新评估 |
| DELETE | /api/v1/assessments/{id} | 删除评估 |
| GET | /health | 健康检查 |

**独立运行：**
```bash
cd backend
python -m modules.assessment.main
# 服务运行在 http://localhost:8002
```

## 契约层

### 契约基类

所有契约继承自 `BaseContract`：

```python
from contracts.base import BaseContract, ContractVersion

class MyContract(BaseContract):
    contract_version: ClassVar[str] = ContractVersion.V1.value
    # ... 字段定义
```

### 患者契约

```python
from contracts.patient_contract import PatientContract, PatientListContract

# 单个患者契约
patient = PatientContract(
    id="uuid",
    full_name="张三",
    gender="M",
    age=75,
    room_number="A101",
    bed_number="1"
)

# 患者列表契约
patient_list = PatientListContract(
    items=[patient],
    total=100,
    page=1,
    size=20
)
```

### 评估契约

```python
from contracts.assessment_contract import AssessmentContract, AssessmentListContract

# 单个评估契约
assessment = AssessmentContract(
    id="uuid",
    patient_id="patient_uuid",
    assessment_type="MMSE",
    evaluation_date="2024-01-15",
    total_score=25,
    status_diagnosis="MCI"
)
```

### 契约注册表

```python
from contracts.registry import ContractRegistry, register_all_contracts, get_contract

# 注册所有契约
register_all_contracts()

# 获取契约类
PatientContract = get_contract("PatientContract")

# 列出模块的所有契约
patient_contracts = ContractRegistry.get_module_contracts("patient_mgmt")

# 标记契约为废弃
registry = ContractRegistry()
registry.deprecate("OldContract", successor="NewContract")
```

## 事件驱动通信

### 事件类型

```python
from shared.event_bus import EventType

class EventType(str, Enum):
    PATIENT_CREATED = "patient.created"
    PATIENT_UPDATED = "patient.updated"
    PATIENT_DELETED = "patient.deleted"
    ASSESSMENT_CREATED = "assessment.created"
    ASSESSMENT_UPDATED = "assessment.updated"
    ASSESSMENT_DELETED = "assessment.deleted"
```

### 发布事件

```python
from shared.event_bus import Event, EventType, OutboxService

async def create_patient(patient_data, db):
    patient = Patient(**patient_data)
    db.add(patient)
    await db.flush()
    
    outbox_service = OutboxService(db)
    event = Event(
        event_type=EventType.PATIENT_CREATED,
        source_module="patient_mgmt",
        payload={"patient_id": str(patient.id)},
        idempotency_key=f"patient_created_{patient.id}"
    )
    await outbox_service.save_to_outbox(event)
    
    await db.commit()
```

### 订阅事件

```python
from shared.event_bus import get_event_bus, EventType

async def setup_subscribers(event_bus):
    @event_bus.subscribe(EventType.PATIENT_CREATED)
    async def handle_patient_created(event):
        print(f"Patient created: {event.payload['patient_id']}")
```

## 前端组件

### 患者管理组件

```
frontend/src/views/tenant/patients/
├── components/
│   ├── PatientSearchBar.vue   # 搜索栏
│   ├── PatientTable.vue       # 数据表格
│   ├── PatientForm.vue        # 表单弹窗
│   ├── PatientProfileCard.vue # 档案卡片
│   ├── PatientSelector.vue    # 患者选择器
│   └── AssessmentTimeline.vue # 评估时间线
├── composables/
│   └── usePatients.ts         # 数据管理逻辑
├── PatientList.vue            # 列表页
└── HealthRecords.vue          # 档案页
```

### 使用示例

```vue
<template>
  <PatientSearchBar
    v-model="searchQuery"
    @search="handleSearch"
    @add="openDialog()"
  />
  
  <PatientTable
    :patients="patients"
    :loading="loading"
    @edit="openDialog"
    @delete="handleDelete"
  />
  
  <PatientForm
    v-model:visible="dialogVisible"
    :patient="editingPatient"
    :loading="submitLoading"
    @submit="handleSubmit"
  />
</template>

<script setup>
import { usePatients } from './composables/usePatients'

const {
  patients, loading, fetchList, handleDelete
} = usePatients()

onMounted(() => fetchList())
</script>
```

### 评估管理组件

```
frontend/src/views/tenant/assessments/
├── components/
│   ├── AssessmentSearchBar.vue # 搜索栏
│   ├── AssessmentTable.vue     # 数据表格
│   └── AssessmentForm.vue      # 表单弹窗
├── composables/
│   └── useAssessments.ts       # 数据管理逻辑
└── AssessmentList.vue          # 列表页
```

## 监控与日志

### Prometheus指标

```python
from shared.monitoring import setup_monitoring

# 在模块入口设置监控
app = FastAPI()
setup_monitoring(app, module_name="patient_mgmt")

# 访问指标
GET /metrics
```

**可用指标：**
- `http_requests_total` - 请求总数
- `http_request_duration_seconds` - 请求延迟
- `http_requests_active` - 活跃请求数
- `http_errors_total` - 错误总数

### 结构化日志

```python
from shared.logging_config import setup_logging, get_logger, LogContext

# 初始化日志
setup_logging(service_name="patient_mgmt", json_output=True)

# 使用日志
logger = get_logger(__name__)
logger.info("patient_created", patient_id=str(patient.id))

# 上下文日志
with LogContext(user_id="123", tenant_id="456"):
    logger.info("operation_completed")
```

## 本地缓存

```python
from shared.cache import LocalCache, cached, patient_cache

# 直接使用
patient_cache.set("patient:123", patient_data, ttl=300)
data = patient_cache.get("patient:123")

# 装饰器方式
@cached(patient_cache, "patient_info", ttl=60)
async def get_patient_info(patient_id: str):
    return await db.get(Patient, patient_id)

# 获取统计
stats = patient_cache.get_stats()
# {"hits": 100, "misses": 20, "hit_rate": 83.33, ...}
```

## 部署

### Docker部署

```bash
# 构建患者模块镜像
docker build -f backend/modules/patient_mgmt/Dockerfile -t patient-mgmt:latest ./backend

# 构建评估模块镜像
docker build -f backend/modules/assessment/Dockerfile -t assessment:latest ./backend
```

### Docker Compose示例

```yaml
version: '3.8'
services:
  patient-mgmt:
    build:
      context: ./backend
      dockerfile: modules/patient_mgmt/Dockerfile
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379/0
  
  assessment:
    build:
      context: ./backend
      dockerfile: modules/assessment/Dockerfile
    ports:
      - "8002:8002"
    environment:
      - DATABASE_URL=postgresql://...
      - PATIENT_SERVICE_URL=http://patient-mgmt:8001
```

## 测试

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_contract_registry.py -v
pytest tests/test_module_communication.py -v

# 运行覆盖率测试
pytest tests/ --cov=modules --cov=contracts --cov=shared
```

### 测试覆盖率目标

| 模块 | 目标覆盖率 |
|------|-----------|
| 契约层 | 90%+ |
| 模块API | 80%+ |
| 事件总线 | 85%+ |
| 缓存层 | 80%+ |

## 最佳实践

1. **契约优先**：模块间通信必须通过契约定义
2. **事件驱动**：使用事件总线进行异步通信
3. **版本管理**：契约变更需更新版本号
4. **向后兼容**：新版本契约必须兼容旧版本
5. **独立部署**：每个模块可独立部署和扩展
