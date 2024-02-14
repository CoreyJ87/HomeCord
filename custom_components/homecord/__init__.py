import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.helpers import device_registry as dr, entity_registry as er
from .const import DOMAIN  # Ensure DOMAIN is correctly imported from const.py

async def async_setup(hass: HomeAssistant, config: dict):
    # This method sets up your integration and returns True for successful setup
    return True

async def send_to_discord(hass, discord_bot_url, device_id, entities):
    # Function to send data to Discord
    json_data = {"device_id": device_id, "entities": entities}
    endpoint = f"{discord_bot_url}/hacs/notify"
    async with aiohttp.ClientSession() as session:
        await session.post(endpoint, json=json_data)

async def get_entities_for_device(hass, device_id):
    entity_registry = er.async_get(hass)
    # The device_id is passed directly to async_entries_for_device
    entries = entity_registry.async_entries_for_device(device_id)
    entities = []

    for entry in entries:
        entities.append({
            "entity_id": entry.entity_id,
            "original_name": entry.original_name or entry.entity_id,
            "platform": entry.platform,
            "entity_category": entry.entity_category,
        })
    return entities


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    discord_bot_url = entry.data["discord_bot_url"]
    device_id_of_interest = entry.data["device_id"]

    async def state_change_listener(event):
        # Listener for state changes
        entity_id = event.data.get("entity_id")
        entity_entry = er.async_get(hass).async_get(entity_id)

        if entity_entry and entity_entry.device_id == device_id_of_interest:
            entities = await get_entities_for_device(hass, device_id_of_interest)
            await send_to_discord(hass, discord_bot_url, device_id_of_interest, entities)

    # Register the event listener for state changes
    hass.bus.async_listen(EVENT_STATE_CHANGED, state_change_listener)

    async def async_send_to_discord_service(call):
        # Service to manually send data to Discord
        device_id = call.data.get("device_id")
        entities = await get_entities_for_device(call.hass, device_id)
        await send_to_discord(call.hass, discord_bot_url, device_id, entities)

    # Register 'send_to_discord' service within Home Assistant
    hass.services.async_register(DOMAIN, "send_to_discord", async_send_to_discord_service)

    return True
