import base64
import json

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN  # Ensure DOMAIN is correctly imported from const.py

# Global variable to maintain WebSocket connection
ws_connection = None


async def async_setup(hass: HomeAssistant, config: dict):
    return True


async def send_to_discord(hass, discord_bot_url, device_id, entities, ws=None):
    # Prepare the data payload
    data_payload = {"device_id": device_id, "entities": entities}

    # If WebSocket connection is available, use it to send data
    if ws:
        data = {"type": "update", "data": data_payload}

        # For camera entities, add snapshot data
        for entity in entities:
            if "camera" in entity["entity_id"]:
                # Fetch camera snapshot
                snapshot_data = await fetch_camera_snapshot(hass, entity["entity_id"])
                encoded_snapshot = encode_snapshot_data(snapshot_data)
                # Append the snapshot data to the entity data
                entity["snapshot"] = encoded_snapshot

        # Send the complete data via WebSocket
        await send_data_via_websocket(ws, data)
    else:
        # Fallback to using the HTTP endpoint if WebSocket is not available
        async with aiohttp.ClientSession() as session:
            await session.post(discord_bot_url + "/hacs/notify", json=data_payload)


async def fetch_camera_snapshot(hass, camera_entity_id):
    snapshot_url = f"{hass.config.api.base_url}/api/camera_proxy/{camera_entity_id}"
    headers = {
        "Authorization": f"Bearer {hass.config.api.token}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(snapshot_url, headers=headers) as response:
            if response.status == 200:
                snapshot_data = await response.read()
                return snapshot_data
            else:
                hass.logger.error(f"Failed to fetch camera snapshot: {response.status}")
                return None


async def get_entities_for_device(hass, device_id):
    entity_registry = er.async_get(hass)
    entities = []
    for entry in entity_registry.entities.values():
        if entry.device_id == device_id:
            entity_state = hass.states.get(entry.entity_id)
            entities.append(
                {
                    "entity_id": entry.entity_id,
                    "original_name": entry.original_name or entry.entity_id,
                    "platform": entry.platform,
                    "entity_category": entry.entity_category,
                    "state": entity_state.state if entity_state else "unknown",
                }
            )
    return entities


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    global ws_connection
    discord_bot_url = entry.data["discord_bot_url"]
    discord_bot_ws_url = entry.data.get(
        "discord_bot_ws_url"
    )  # Ensure this is configured
    device_id_of_interest = entry.data["device_id"]

    # Establish WebSocket connection if URL is provided
    if discord_bot_ws_url:
        ws_connection = await establish_websocket_connection(discord_bot_ws_url)

    async def state_change_listener(event):
        entity_id = event.data.get("entity_id")
        entity_entry = er.async_get(hass).async_get(entity_id)
        if entity_entry and entity_entry.device_id == device_id_of_interest:
            entities = await get_entities_for_device(hass, device_id_of_interest)
            await send_to_discord(
                hass, discord_bot_url, device_id_of_interest, entities, ws=ws_connection
            )

    hass.bus.async_listen(EVENT_STATE_CHANGED, state_change_listener)

    async def async_send_to_discord_service(call: ServiceCall):
        device_id = call.data.get("device_id")
        entities = await get_entities_for_device(call.hass, device_id)
        await send_to_discord(
            call.hass, discord_bot_url, device_id, entities, ws=ws_connection
        )

    hass.services.async_register(
        DOMAIN, "send_to_discord", async_send_to_discord_service
    )

    return True


async def establish_websocket_connection(discord_bot_ws_url):
    session = aiohttp.ClientSession()
    ws = await session.ws_connect(discord_bot_ws_url)
    return ws


async def send_data_via_websocket(ws, data):
    await ws.send_str(json.dumps(data))


def encode_snapshot_data(binary_data):
    """Encode binary snapshot data to a Base64 string."""
    return base64.b64encode(binary_data).decode("utf-8")
