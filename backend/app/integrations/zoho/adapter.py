import logging
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from app.models.models import Integration

logger = logging.getLogger(__name__)

class ZohoAdapter:
    BASE_URL = "https://www.zohoapis.com/crm/v2" # Adjust for EU/CN/etc if needed
    AUTH_URL = "https://accounts.zoho.com/oauth/v2/token" # Adjust for region

    def __init__(self, integration: Integration, config: Optional[Dict] = None):
        self.integration = integration
        # In a real app, we'd decrypt here. For MVP, assuming stored as JSON or simple dict.
        # But wait, the model says encrypted_config is a string. 
        # For this MVP step, we'll assume the caller (service) handles decryption 
        # OR we just implement a placeholder for decryption.
        # Let's assume the integration object PASSED IN already has a .config dict 
        # attached to it by the service layer, or we parse it here.
        # For simplicity in this file, we expect `integration.config` to be available/injected.
        if config:
            self.config = config
        elif hasattr(integration, "config"):
             self.config = integration.config
        else:
             # Try to decrypt/parse if possible or assume it's just a dict attribute added dynamically (which failed)
             # For now, require injection
             raise ValueError("Integration must have config injected")

    async def get_valid_access_token(self) -> str:
        """
        Returns a valid access token, refreshing if necessary.
        Updates self.integration.config if refreshed (caller must save).
        """
        expires_at = self.config.get("expires_at")
        if expires_at:
            # Check if expired (with 5 min buffer)
            exp_dt = datetime.fromisoformat(expires_at)
            if datetime.utcnow() < exp_dt - timedelta(minutes=5):
                return self.config["access_token"]

        # Refresh
        return await self._refresh_token()

    async def _refresh_token(self) -> str:
        logger.info(f"Refreshing Zoho token for integration {self.integration.id}")
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.AUTH_URL, params={
                "refresh_token": self.config["refresh_token"],
                "client_id": self.config["client_id"],
                "client_secret": self.config["client_secret"],
                "grant_type": "refresh_token"
            })
            
            if resp.status_code != 200:
                logger.error(f"Failed to refresh Zoho token: {resp.text}")
                raise Exception("Zoho token refresh failed")
            
            data = resp.json()
            if "access_token" not in data:
                 raise Exception(f"Invalid refresh response: {data}")

            # Update config
            self.config["access_token"] = data["access_token"]
            # Zoho usually returns expires_in (seconds)
            expires_in = data.get("expires_in", 3600)
            self.config["expires_at"] = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
            
            # Note: The caller of this adapter needs to persist the updated config to DB!
            return data["access_token"]

    async def _request(self, method: str, endpoint: str, json: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict:
        token = await self.get_valid_access_token()
        headers = {
            "Authorization": f"Zoho-oauthtoken {token}",
            "Content-Type": "application/json"
        }
        url = f"{self.BASE_URL}/{endpoint}"
        
        async with httpx.AsyncClient() as client:
            resp = await client.request(method, url, headers=headers, json=json, params=params)
            
            if resp.status_code == 401:
                # Retry once if 401 (token might have seemingly valid expiry but be revoked)
                logger.warning("Got 401 from Zoho, forcing refresh and retrying")
                token = await self._refresh_token()
                headers["Authorization"] = f"Zoho-oauthtoken {token}"
                resp = await client.request(method, url, headers=headers, json=json, params=params)

            if resp.status_code >= 400:
                logger.error(f"Zoho API Error {resp.status_code}: {resp.text}")
                # Parse Zoho error for better details?
                raise Exception(f"Zoho API Error: {resp.status_code} - {resp.text}")
            
            return resp.json()

    async def search_lead(self, email: Optional[str] = None, phone: Optional[str] = None) -> Optional[str]:
        """
        Search for a lead by email or phone. Returns Zoho Lead ID if found.
        """
        # Zoho Search API: /coql or /Leads/search?criteria=((Email:equals:x)OR(Phone:equals:y))
        # Lets use simple criteria search
        
        criteria = []
        if email:
            criteria.append(f"(Email:equals:{email})")
        if phone:
            criteria.append(f"(Phone:equals:{phone})")
        
        if not criteria:
            return None
            
        criteria_str = " OR ".join(criteria)
        if len(criteria) > 1:
            criteria_str = f"({criteria_str})"
            
        try:
            # Using v2/Leads/search
            resp = await self._request("GET", "Leads/search", params={"criteria": criteria_str})
            if "data" in resp and resp["data"]:
                # Return first match
                return resp["data"][0]["id"]
            return None
        except Exception as e:
            logger.warning(f"Zoho search failed: {e}")
            return None

    async def create_lead(self, payload: Dict[str, Any]) -> str:
        resp = await self._request("POST", "Leads", json={"data": [payload]})
        # Response format: {"data": [{"code": "SUCCESS", "details": {"id": "..."}}]}
        if "data" in resp and resp["data"]:
            item = resp["data"][0]
            if item.get("code") in ["SUCCESS", "created"]:
                return item["details"]["id"]
            else:
                raise Exception(f"Zoho create failed: {item.get('message')}")
        raise Exception("Invalid Zoho create response")

    async def update_lead(self, lead_id: str, payload: Dict[str, Any]):
        # Zoho Update: PUT /Leads/{lead_id} or POST /Leads/upsert
        # We use explicit update here
        payload["id"] = lead_id
        resp = await self._request("PUT", "Leads", json={"data": [payload]})
        if "data" in resp and resp["data"]:
            item = resp["data"][0]
            if item.get("code") in ["SUCCESS", "updated"]:
                return
            else:
                raise Exception(f"Zoho update failed: {item.get('message')}")

    async def upsert_lead(
        self, 
        payload: Dict[str, Any], 
        dedupe_strategy: str = "EMAIL_OR_PHONE",
        existing_zoho_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Upserts a lead.
        Returns: (zoho_lead_id, action_taken)
        action_taken: "created" | "updated"
        """
        
        lead_id = existing_zoho_id
        
        # 1. Search if not provided
        if not lead_id:
            email = payload.get("Email")
            phone = payload.get("Phone")
            
            # Adjust search based on strategy
            search_email = email if "EMAIL" in dedupe_strategy else None
            search_phone = phone if "PHONE" in dedupe_strategy else None
            
            lead_id = await self.search_lead(email=search_email, phone=search_phone)

        # 2. Update or Create
        if lead_id:
            await self.update_lead(lead_id, payload)
            return lead_id, "updated"
        else:
            new_id = await self.create_lead(payload)
            return new_id, "created"

    async def get_fields(self, module: str = "Leads") -> List[Dict[str, str]]:
        """
        Get simplified list of fields for the module.
        """
        resp = await self._request("GET", f"settings/fields?module={module}")
        fields = []
        if "fields" in resp:
            for f in resp["fields"]:
                if f.get("api_name") and f.get("field_label"):
                    fields.append({
                        "api_name": f["api_name"],
                        "label": f["field_label"],
                        "data_type": f.get("data_type")
                    })
        return fields
