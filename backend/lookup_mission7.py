import asyncio
from sqlmodel import select
from app.core.db import SessionLocal
from app.models.models import Contact, Conversation, Workspace

async def lookup_data():
    async with SessionLocal() as db:
        workspaces = (await db.execute(select(Workspace))).scalars().all()
        print(f"Workspaces: {[str(w.id) for w in workspaces]}")
        
        if workspaces:
            w_id = workspaces[0].id
            contacts = (await db.execute(select(Contact).where(Contact.workspace_id == w_id))).scalars().all()
            print(f"Contacts in workspace {w_id}: {[str(c.id) for c in contacts]}")
            
            if contacts:
                c_id = contacts[0].id
                convs = (await db.execute(select(Conversation).where(Conversation.contact_id == c_id))).scalars().all()
                print(f"Conversations for contact {c_id}: {[str(cv.id) for cv in convs]}")

if __name__ == "__main__":
    asyncio.run(lookup_data())
