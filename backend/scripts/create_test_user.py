import sys
import os
import asyncio
import logging

# Add the parent directory to sys.path to allow importing from 'app'
# This assumes the script is in backend/scripts/
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from app.core import security  # noqa: E402
from app.models.models import User, Workspace, WorkspaceMember, WorkspaceRole  # noqa: E402
from app.core.config import settings  # noqa: E402
from sqlmodel import select, SQLModel  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_test_user():
    # Use the same engine logic as the app
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        
    async with async_session() as session:
        # Check if user exists
        email = "test@example.com"
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        
        if user:
            logger.info(f"User {email} already exists.")
            return

        # Create user
        logger.info(f"Creating test user: {email}")
        db_user = User(
            email=email,
            hashed_password=security.get_password_hash("Password123!"),
            full_name="Test User",
            is_active=True,
            is_superuser=True
        )
        session.add(db_user)
        await session.flush()

        # Create workspace
        logger.info("Creating workspace for test user...")
        db_workspace = Workspace(name="Test Workspace")
        session.add(db_workspace)
        await session.flush()

        # Create membership
        logger.info("Creating workspace membership...")
        db_membership = WorkspaceMember(
            user_id=db_user.id,
            workspace_id=db_workspace.id,
            role=WorkspaceRole.OWNER
        )
        session.add(db_membership)
        
        # --- Mission 8: Zoho Integration Setup ---
        from app.models.models import Integration, ZohoLeadMapping
        
        logger.info("Setting up Zoho Integration for test user...")
        # Check if exists
        integ = await session.execute(select(Integration).where(Integration.workspace_id == db_workspace.id, Integration.provider == "zoho"))
        if not integ.scalars().first():
            db_integration = Integration(
                workspace_id=db_workspace.id,
                provider="zoho",
                status="connected",
                encrypted_config='{"refresh_token": "mock_refresh", "client_id": "mock_client", "client_secret": "mock_secret", "access_token": "mock_access", "expires_at": "2099-01-01T00:00:00"}'
            )
            session.add(db_integration)
            
        # Check mapping
        mapping = await session.execute(select(ZohoLeadMapping).where(ZohoLeadMapping.workspace_id == db_workspace.id))
        if not mapping.scalars().first():
            db_mapping = ZohoLeadMapping(
                workspace_id=db_workspace.id,
                dedupe_strategy="EMAIL_OR_PHONE",
                field_mappings={
                    "first_name": "First_Name",
                    "last_name": "Last_Name",
                    "email": "Email",
                    "phone": "Phone",
                    "company": "Company",
                    "description": "Description"
                }
            )
            session.add(db_mapping)

        await session.commit()
        logger.info("Test user and Zoho configuration created successfully.")

if __name__ == "__main__":
    asyncio.run(create_test_user())
