import asyncio
import sys
from sqlmodel import select

from app.core.db import SessionLocal
from app.models.admin_models import AdminUser
from app.core.security import get_password_hash

async def seed_initial_admin(email: str, password: str, name: str):
    async with SessionLocal() as db:
        # Check if any admin exists
        result = await db.execute(select(AdminUser))
        if result.scalars().first():
            print("Admin users already exist. Skipping seed.")
            return

        admin = AdminUser(
            email=email,
            full_name=name,
            hashed_password=get_password_hash(password),
            is_superuser=True,
            is_active=True
        )
        db.add(admin)
        await db.commit()
        print(f"Initial SuperAdmin created: {email}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python seed_admin.py <email> <password> <name>")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    name = sys.argv[3]
    
    asyncio.run(seed_initial_admin(email, password, name))
