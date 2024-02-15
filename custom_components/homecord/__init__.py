import base64
import json
import logging

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.network import get_url
from homeassistant.helpers.aiohttp_client import async_get_clientsession


from .const import DOMAIN

# Setup logger
_LOGGER = logging.getLogger(__name__)

# Global variable to maintain WebSocket connection
ws_connection = None


async def async_setup(hass: HomeAssistant, config: dict):
    return True


async def send_to_discord(hass, discord_bot_url, device_id, entities, ws=None):
    # Prepare the data payload
    data_payload = {"device_id": device_id, "entities": []}

    for entity in entities:
        entity_data = entity.copy()  # Create a copy to avoid modifying the original dict
        if "camera" in entity["entity_id"]:
            snapshot_data = await fetch_camera_snapshot(hass, entity["entity_id"])
            if snapshot_data is not None:
                encoded_snapshot = encode_snapshot_data(snapshot_data)
                entity_data["snapshot"] = encoded_snapshot
            else:
                _LOGGER.debug(f"No snapshot data available for {entity['entity_id']}.")
        data_payload["entities"].append(entity_data)

    if ws:
        data = {"type": "update", "data": data_payload}
        _LOGGER.debug(f"Sending data via WebSocket: {data}")
        await send_data_via_websocket(ws, data)
    else:
        _LOGGER.debug("WebSocket not available, falling back to HTTP POST.")
        async with aiohttp.ClientSession() as session:
            await session.post(discord_bot_url + "/hacs/notify", json=data_payload)




async def fetch_camera_snapshot(hass, camera_entity_id):
    snapshot_url = f"{get_url(hass)}/api/camera_proxy/{camera_entity_id}"
    _LOGGER.debug(f"Fetching camera snapshot from {snapshot_url}")

    # Get an authenticated HTTP session
    session = async_get_clientsession(hass)
    async with session.get(snapshot_url) as response:
        _LOGGER.debug(f"Response Status: {response.status}, Response Body: {await response.text()}")

    async with session.get(snapshot_url) as response:
        if response.status == 200:
            snapshot_data = await response.read()
            _LOGGER.debug(f"Successfully fetched camera snapshot for {camera_entity_id}.")
            return snapshot_data
        else:
            _LOGGER.error(f"Failed to fetch camera snapshot: HTTP {response.status}")
            return None


async def get_entities_for_device(hass, device_id):
    entity_registry = er.async_get(hass)
    entities = []
    for entry in entity_registry.entities.values():
        if entry.device_id == device_id:
            entity_state = hass.states.get(entry.entity_id)
            entities.append({
                "entity_id": entry.entity_id,
                "original_name": entry.original_name or entry.entity_id,
                "platform": entry.platform,
                "entity_category": entry.entity_category,
                "state": entity_state.state if entity_state else "unknown",
            })
    return entities


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    global ws_connection
    discord_bot_url = entry.data["discord_bot_url"]
    discord_bot_ws_url = entry.data["discord_bot_ws_url"]
    device_id_of_interest = entry.data["device_id"]

    _LOGGER.debug("Setting up HomeCord entry")

    if discord_bot_ws_url:
        ws_connection = await establish_websocket_connection(hass, discord_bot_ws_url)
        _LOGGER.debug(f"WebSocket connection established to {discord_bot_ws_url}")
    else:
        _LOGGER.warning("Discord bot WebSocket URL not configured")

    async def state_change_listener(event):
        entity_id = event.data.get("entity_id")
        entity_entry = er.async_get(hass).async_get(entity_id)
        if entity_entry and entity_entry.device_id == device_id_of_interest:
            entities = await get_entities_for_device(hass, device_id_of_interest)
            _LOGGER.debug(f"Detected state change for device {device_id_of_interest}, sending to Discord")
            await send_to_discord(hass, discord_bot_url, device_id_of_interest, entities, ws=ws_connection)

    hass.bus.async_listen(EVENT_STATE_CHANGED, state_change_listener)
    _LOGGER.info("HomeCord integration setup completed")

    async def async_send_to_discord_service(call: ServiceCall):
        device_id = call.data.get("device_id")
        entities = await get_entities_for_device(call.hass, device_id)
        await send_to_discord(call.hass, discord_bot_url, device_id, entities, ws=ws_connection)

    hass.services.async_register(DOMAIN, "send_to_discord", async_send_to_discord_service)

    return True


async def establish_websocket_connection(hass, discord_bot_ws_url):
    _LOGGER.debug(f"Attempting to establish WebSocket connection to {discord_bot_ws_url}")
    try:
        session = aiohttp.ClientSession()
        ws = await session.ws_connect(discord_bot_ws_url)
        _LOGGER.debug("WebSocket connection successfully established")
        return ws
    except Exception as e:
        _LOGGER.error(f"Failed to establish WebSocket connection: {e}")
        return None


async def send_data_via_websocket(ws, data):
    await ws.send_str(json.dumps(data))


def encode_snapshot_data(binary_data):
    """Encode binary snapshot data to a Base64 string."""
    return base64.b64encode(binary_data).decode("utf-8")
