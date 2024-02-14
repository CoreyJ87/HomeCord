import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.helpers import device_registry as dr, entity_registry as er
from .const import DOMAIN  # Make sure DOMAIN is defined in your const.py


async def async_setup(hass: HomeAssistant, config: dict):
    # This method sets up your integration and returns True for successful setup
    return True


async def send_to_discord(hass, discord_bot_url, device_id, entities):
    # Adjusted to pass `hass` and `discord_bot_url` as parameters
    json_data = {"device_id": device_id, "entities": entities}
    endpoint = f"{discord_bot_url}/hacs/notify"
    async with aiohttp.ClientSession() as session:
        await session.post(endpoint, json=json_data)


async def get_entities_for_device(hass, device_id):
    # Moved to be a top-level function
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    entities = []

    for entry in entity_registry.async_entries_for_device(device_registry, device_id):
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

    @hass.bus.async_listen(EVENT_STATE_CHANGED)
    async def state_change_listener(event):
        entity_id = event.data.get("entity_id")
        entity_entry = er.async_get(hass).async_get(entity_id)

        if entity_entry and entity_entry.device_id == device_id_of_interest:
            entities = await get_entities_for_device(hass, device_id_of_interest)
            await send_to_discord(hass, discord_bot_url, device_id_of_interest, entities)

    async def async_send_to_discord_service(call):
        device_id = call.data.get("device_id")
        entities = await get_entities_for_device(call.hass, device_id)
        await send_to_discord(call.hass, discord_bot_url, device_id, entities)

    # Corrected service registration to use the function properly
    hass.services.async_register(DOMAIN, "send_to_discord", async_send_to_discord_service)

    return True
