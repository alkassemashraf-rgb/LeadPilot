import asyncio
from sqlmodel import select

from app.core.db import SessionLocal
from app.models.admin_models import AdminRole, AdminPermission, AdminRolePermission

DEFAULT_PERMISSIONS = [
    {"key": "users.read", "description": "View product users"},
    {"key": "users.write", "description": "Manage product users (toggle active)"},
    {"key": "workspaces.read", "description": "View workspaces"},
    {"key": "workspaces.write", "description": "Manage workspaces"},
    {"key": "modules.read", "description": "View module status"},
    {"key": "modules.write", "description": "Toggle system modules"},
    {"key": "audit.read", "description": "View admin audit logs"},
    {"key": "monitoring.read", "description": "View integrations, webhooks, and execution logs"},
]

DEFAULT_ROLES = [
    {
        "name": "SuperAdmin",
        "description": "Full system access (bypasses permission checks)",
        "permissions": [] # is_superuser handles this
    },
    {
        "name": "Support",
        "description": "Standard support access",
        "permissions": ["users.read", "workspaces.read", "monitoring.read"]
    },
    {
        "name": "Admin",
        "description": "Administrative access with management capabilities",
        "permissions": ["users.read", "users.write", "workspaces.read", "workspaces.write", "modules.read", "monitoring.read", "audit.read"]
    }
]

async def seed_rbac():
    async with SessionLocal() as db:
        # 1. Seed Permissions
        perm_map = {}
        for p_data in DEFAULT_PERMISSIONS:
            result = await db.execute(select(AdminPermission).where(AdminPermission.key == p_data["key"]))
            perm = result.scalars().first()
            if not perm:
                perm = AdminPermission(**p_data)
                db.add(perm)
                await db.flush()
            perm_map[p_data["key"]] = perm.id
        
        # 2. Seed Roles
        for r_data in DEFAULT_ROLES:
            result = await db.execute(select(AdminRole).where(AdminRole.name == r_data["name"]))
            role = result.scalars().first()
            if not role:
                role = AdminRole(name=r_data["name"], description=r_data["description"])
                db.add(role)
                await db.flush()
            
            # 3. Link Permissions
            for p_key in r_data["permissions"]:
                p_id = perm_map[p_key]
                link_result = await db.execute(
                    select(AdminRolePermission).where(
                        AdminRolePermission.role_id == role.id,
                        AdminRolePermission.permission_id == p_id
                    )
                )
                if not link_result.scalars().first():
                    link = AdminRolePermission(role_id=role.id, permission_id=p_id)
                    db.add(link)
        
        await db.commit()
        print("Admin RBAC seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed_rbac())
