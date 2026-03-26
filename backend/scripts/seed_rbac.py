"""
Seed Script — Initialize RBAC (Role-Based Access Control) data.
Creates permissions, roles, and assigns roles to users.

Run:
    $env:PYTHONUTF8=1; python scripts/seed_rbac.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import get_settings
from app.models.user import User, Role, Permission, UserRole, RolePermission, UserScope
from app.models.tenant import Tenant
from app.core.module_registry import CORE_MODULES


async def seed_rbac():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("=== Seeding RBAC Data ===\n")
        
        # 1. Create all permissions from module registry
        print("1. Creating permissions...")
        for module_def in CORE_MODULES:
            for perm_code in module_def.permissions:
                existing = await session.execute(
                    select(Permission).where(Permission.code == perm_code)
                )
                if not existing.scalar_one_or_none():
                    perm = Permission(
                        code=perm_code,
                        module_slug=module_def.slug,
                        description=f"Permission: {perm_code} ({module_def.display_name})"
                    )
                    session.add(perm)
                    print(f"   Created permission: {perm_code}")
        
        await session.flush()
        
        # 2. Get test tenant
        tenant_result = await session.execute(
            select(Tenant).where(Tenant.name == "幸福养老院")
        )
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            print("\nError: Test tenant '幸福养老院' not found!")
            print("Please run seed_test_tenant.py first.")
            return
        
        print(f"\n2. Found tenant: {tenant.name} (id: {tenant.id})")
        
        # 3. Create tenant admin role with all permissions
        print("\n3. Creating roles...")
        
        # Tenant Admin role (full permissions)
        admin_role_result = await session.execute(
            select(Role).where(Role.name == "tenant_admin", Role.tenant_id == tenant.id)
        )
        admin_role = admin_role_result.scalar_one_or_none()
        
        if not admin_role:
            admin_role = Role(
                name="tenant_admin",
                display_name="租户管理员",
                description="租户管理员，拥有所有模块权限",
                tenant_id=tenant.id
            )
            session.add(admin_role)
            await session.flush()
            print(f"   Created role: {admin_role.display_name}")
        else:
            print(f"   Role already exists: {admin_role.display_name}")
        
        # Staff role (read/write permissions, no delete)
        staff_role_result = await session.execute(
            select(Role).where(Role.name == "tenant_staff", Role.tenant_id == tenant.id)
        )
        staff_role = staff_role_result.scalar_one_or_none()
        
        if not staff_role:
            staff_role = Role(
                name="tenant_staff",
                display_name="普通员工",
                description="普通员工，拥有读写权限",
                tenant_id=tenant.id
            )
            session.add(staff_role)
            await session.flush()
            print(f"   Created role: {staff_role.display_name}")
        else:
            print(f"   Role already exists: {staff_role.display_name}")
        
        # 4. Assign all permissions to admin role
        print("\n4. Assigning permissions to roles...")
        
        all_permissions = (await session.execute(select(Permission))).scalars().all()
        
        for perm in all_permissions:
            existing_rp = await session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == admin_role.id,
                    RolePermission.permission_id == perm.id
                )
            )
            if not existing_rp.scalar_one_or_none():
                rp = RolePermission(
                    role_id=admin_role.id,
                    permission_id=perm.id
                )
                session.add(rp)
                print(f"   Assigned {perm.code} to {admin_role.display_name}")
        
        # Assign read/write permissions to staff (no delete)
        for perm in all_permissions:
            if ":delete" not in perm.code:
                existing_rp = await session.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == staff_role.id,
                        RolePermission.permission_id == perm.id
                    )
                )
                if not existing_rp.scalar_one_or_none():
                    rp = RolePermission(
                        role_id=staff_role.id,
                        permission_id=perm.id
                    )
                    session.add(rp)
                    print(f"   Assigned {perm.code} to {staff_role.display_name}")
        
        # 5. Assign admin role to test user
        print("\n5. Assigning roles to users...")
        
        user_result = await session.execute(
            select(User).where(User.email == "tenant@eldercare.com")
        )
        user = user_result.scalar_one_or_none()
        
        if user:
            existing_ur = await session.execute(
                select(UserRole).where(UserRole.user_id == user.id)
            )
            if not existing_ur.scalar_one_or_none():
                ur = UserRole(user_id=user.id, role_id=admin_role.id)
                session.add(ur)
                print(f"   Assigned role '{admin_role.display_name}' to user {user.email}")
            else:
                print(f"   User {user.email} already has a role assigned")
        else:
            print("   Warning: Test user 'tenant@eldercare.com' not found!")
        
        await session.commit()
        
        print("\n=== RBAC Seeding Complete ===")
        print("\nSummary:")
        print(f"  - Permissions created: {len(all_permissions)}")
        print(f"  - Roles created: 2 (tenant_admin, tenant_staff)")
        print(f"  - Test user: tenant@eldercare.com")
        print(f"  - User role: tenant_admin (full permissions)")
        print("\nYou can now log in with:")
        print("  Email: tenant@eldercare.com")
        print("  Password: Tenant123!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_rbac())
