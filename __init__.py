import asyncio

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_entry_flow
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

DOMAIN = "discord_integration"


class MyIntegrationConfigFlow(config_entry_flow.DiscoveryFlowHandler):
    VERSION = 1
    CONNECTION_CLASS = config_entry_flow.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="My Integration", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("discord_bot_url"): str,
                    vol.Required("device_id"): str,
                }
            ),
        )


class MyIntegration:
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        self._hass = hass
        self._config_entry = config_entry
        self._config = config_entry.data

    async def async_setup(self):
        # Access configuration options
        discord_bot_url = self._config.get("discord_bot_url")
        device_id_of_interest = self._config.get("device_id")

        # Use configuration options in integration
        # (e.g., connect to Discord bot using the provided URL)


async def async_setup(hass: HomeAssistant, config: dict):
    async def send_to_discord(device_id, entities):
        # Logic to build and send the JSON object to Discord
        json_data = {"device_id": device_id, "entities": entities}

        # Retrieve discord_bot_url from configuration
        discord_bot_url = config.get("discord_bot_url")

        # Example: Sending the message to a Discord webhook or bot endpoint
        # Ensure you replace this URL with your actual Discord bot's endpoint URL
        endpoint = (
            f"http://{discord_bot_url}/hacs/notify"  # Use the provided Discord bot URL
        )
        async with aiohttp.ClientSession() as session:
            await session.post(endpoint, json=json_data)

    async def get_entities_for_device(device_id: str):
        """Fetch all entities for a given device ID."""
        dev_reg = dr.async_get(hass)
        ent_reg = er.async_get(hass)

        # Find the device in the device registry
        device = dev_reg.async_get(device_id)
        if not device:
            return []

        # Get all entities for this device
        entities = []
        for entry in er.async_entries_for_device(ent_reg, device_id):
            entity = {
                "entity_id": entry.entity_id,
                "original_name": entry.original_name,
                "platform": entry.platform,
                "entity_category": entry.entity_category,
            }
            entities.append(entity)

        return entities

    @callback
    def state_change_listener(event):
        """Handle the state change event."""
        entity_id = event.data.get("entity_id")

        # Get the device ID from configuration
        device_id_of_interest = config.get("device_id")

        # Find the entity in the entity registry
        entity_entry = er.async_get(hass, entity_id)
        if entity_entry and entity_entry.device_id == device_id_of_interest:
            # This part ensures we fetch updated entities info for the device
            asyncio.create_task(
                send_to_discord(
                    device_id_of_interest,
                    asyncio.run(get_entities_for_device(device_id_of_interest)),
                )
            )

    # Listen for state change events
    hass.bus.async_listen(EVENT_STATE_CHANGED, state_change_listener)

    # Register a service to manually send all entities for a device to Discord
    async def handle_send_to_discord(call):
        device_id = call.data.get("device_id")
        entities = await get_entities_for_device(device_id)
        await send_to_discord(device_id, entities)

    hass.services.async_register(DOMAIN, "send_to_discord", handle_send_to_discord)

    return True
