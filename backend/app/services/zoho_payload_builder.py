from typing import Dict, Any, Optional
from uuid import UUID
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Contact, ZohoLeadMapping, ChannelIdentity

async def build_zoho_payload(
    session: AsyncSession,
    contact_id: UUID,
    mapping: ZohoLeadMapping,
    contact: Optional[Contact] = None,
    overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Constructs a Zoho CRM Lead payload based on contact data and mapping configuration.
    
    Args:
        session: Database session
        contact_id: ID of the contact to sync
        mapping: ZohoLeadMapping configuration
        contact: Optional pre-fetched contact object
        overrides: Optional dictionary of values to override (e.g., from node config)
        
    Returns:
        Dict[str, Any]: Payload ready for Zoho API
    """
    if not contact:
        contact = await session.get(Contact, contact_id)
        if not contact:
            raise ValueError("Contact not found")

    # 1. Base Data Gathering
    # Flatten contact attributes
    contact_data = {
        "first_name": contact.first_name,
        "last_name": contact.last_name or "Unknown", # Last Name is mandatory in Zoho
        "email": None,
        "phone": None,
        "company": contact.additional_metadata.get("company"),
        "description": contact.additional_metadata.get("notes"),
    }
    
    # 2. Fetch Identity for Email/Phone
    # (Only if not already present in metadata, but we check identity first as per original logic)
    id_query = select(ChannelIdentity).where(ChannelIdentity.contact_id == contact_id)
    id_result = await session.execute(id_query)
    identity = id_result.scalars().first()
    
    if identity:
        # Naive mapping based on provider
        if identity.provider == "email":
            contact_data["email"] = identity.provider_user_id
        elif identity.provider == "whatsapp":
            contact_data["phone"] = identity.provider_user_id
            
    # 3. Direct Overrides from Contact Metadata (Higher Priority)
    if contact.additional_metadata.get("email"): contact_data["email"] = contact.additional_metadata["email"]
    if contact.additional_metadata.get("phone"): contact_data["phone"] = contact.additional_metadata["phone"]

    # 4. Node Config Overrides (Highest Priority for specific fields)
    if overrides:
        # Example: notes_template might map to description
        if overrides.get("notes_template"):
             contact_data["description"] = overrides["notes_template"]
        # Allow direct field overrides if needed
        for k, v in overrides.items():
            if k in contact_data:
                contact_data[k] = v

    # 5. Apply Field Mapping
    zoho_payload = {}
    for lp_field, zoho_field in mapping.field_mappings.items():
        # Only include if value exists and is truthy (or we want to allow empty strings? Original logic checked truthiness)
        if lp_field in contact_data and contact_data[lp_field]:
            val = contact_data[lp_field]
            
            # 6. Safety Caps
            # Description length cap (approx 32k limit, safe 5k)
            if zoho_field == "Description" and isinstance(val, str) and len(val) > 5000:
                val = val[:5000] + "... (truncated)"
                
            zoho_payload[zoho_field] = val
            
    return zoho_payload
