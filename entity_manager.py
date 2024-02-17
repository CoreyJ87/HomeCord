import base64
import logging
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.network import get_url
from homeassistant.helpers.aiohttp_client import async_get_clientsession


_LOGGER = logging.getLogger(__name__)

class EntityManager:
    def __init__(self, hass: HomeAssistant, access_token: str):
        self.hass = hass
        self.access_token = access_token

    def encode_snapshot_data(self, binary_data):
        """Encode binary snapshot data to a string using base64."""
        return base64.b64encode(binary_data).decode('utf-8')

    async def get_entities_for_device(self, device_id: str, entity_names: list = None):
        """Fetches entities for a specific device, optionally filtered by a list of entity names."""
        entity_registry = er.async_get(self.hass)
        entities = []
        for entry in entity_registry.entities.values():
            if entry.device_id == device_id:
                if not entity_names or entry.original_name in entity_names or entry.entity_id in entity_names:
                    entity_state = self.hass.states.get(entry.entity_id)
                    entity_data = {
                        "entity_id": entry.entity_id,
                        "original_name": entry.original_name or entry.entity_id,
                        "platform": entry.platform,
                        "entity_category": entry.entity_category,
                        "state": entity_state.state if entity_state else "unknown",
                    }
                    # Fetch snapshot data for camera and image entities
                    if "camera" in entry.entity_id or "image" in entry.entity_id:
                        snapshot_data = await self.fetch_entity_snapshot(entry.entity_id)
                        if snapshot_data:
                            entity_data["snapshot"] = self.encode_snapshot_data(snapshot_data)
                    entities.append(entity_data)
        return entities

    async def fetch_entity_snapshot(self, entity_id: str):
        """Fetches snapshot data for an entity based on its type."""
        snapshot_url = ""
        if "camera" in entity_id:
            snapshot_url = f"{get_url(self.hass)}/api/camera_proxy/{entity_id}"
        elif "image" in entity_id:
            # This assumes image entities are fetched similarly, adjust as needed
            snapshot_url = f"{get_url(self.hass)}/api/image_proxy/{entity_id}"

        _LOGGER.debug(f"Fetching snapshot for {entity_id} from {snapshot_url}")
        headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json",}
        session = await async_get_clientsession(self.hass)
        async with session.get(snapshot_url, headers=headers) as response:
            if response.status == 200:
                _LOGGER.debug(f"Successfully fetched snapshot for {entity_id}.")
                return await response.read()
            else:
                _LOGGER.error(f"Failed to fetch snapshot for {entity_id}: HTTP {response.status}")
                return None
