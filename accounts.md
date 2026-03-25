# Elder Care Platform - System Test Accounts

(系统测试账号说明文档)

以下列出了您当前本地开发与测试环境中已预置的几组开箱即用的测试账号凭据。
本系统采用了 **SaaS 多租户架构隔离 (Row-Level Security)** 设计，平台级别超管与机构级别管理员的权限边界严密隔绝。

---

## 1. 平台运营超级管理员 (Platform Super Admin)

此账号是“软件提供商 (SaaS运营方)”的顶级账号，有权创建、启停下属的租户机构。**此账号无法也不能越权直接干涉下辖养老院的具体长者业务数据。**

* **登录地址 (URL)**: `http://localhost:5173/login`
* **登录邮箱 (Email)**: `admin@eldercare.com`
* **登录密码 (Password)**: `Admin123!`
* **可访问控制台**: 【系统运营总览】 (`/admin/dashboard`)
* **核心功能**:
  * 租户注册与续费管理 (Tenants)
  * 订阅套餐 (Pricing / Plans)
  * 系统模块注册表监控 (Module Registry)

---

## 2. 模拟机构管理员 (Mock Tenant Admin)

我们为您预制了一家购买了最高级别企业版（全模块授权）的虚拟养老机构——**“幸福养老院 (Xingfu Care Home)”**。此账号等同于该养老院的院长。

* **登录地址 (URL)**: `http://localhost:5173/login`
* **登录邮箱 (Email)**: `tenant@eldercare.com`
* **登录密码 (Password)**: `Tenant123!`
* **可访问控制台**: 【机构工作台】 (`/dashboard`)
* **核心功能** (日常测试用这组账号)：
  * **患者管理**: 长者入退院录入、健康档案汇总大屏。
  * **认知评估**: MMSE、MoCA 等失智量表评测与追踪管理。
  * **健康监测** *(开发中)*: 实时生命体征折线图、用药干预记录等。
  * **其他所有通过 `seed_test_tenant.py` 授予最高权限授权的核心功能。**

---

### ⚠️ 关于增加新用户的提示

后续如果需要增加普通级别的护工或主治医生（Tenant Member），必须在“模拟机构管理员”的【系统设置】页，通过此机构自己内部的角色和组织架构 (Role Based Access Control) 独立创建完成。平台超管无法为其指派。
