from .const import DOMAIN
from .entity_manager import EntityManager
from .communicator import Communicator
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant, ServiceCall

from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval


import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    _LOGGER.info("HomeCord Integration: Setting up entry.")

    # Configuration extraction
    discord_bot_url = entry.data["discord_bot_url"]
    discord_bot_ws_url = entry.data["discord_bot_ws_url"]
    device_id_of_interest = entry.data["device_id"]
    access_token = entry.data.get("long_lived_token")
    entity_names = entry.data.get("entity_names", "")
    entity_names_list = [name.strip() for name in entity_names.split(',')] if entity_names else []

    # Entity Manager and Communicator initialization
    entity_manager = EntityManager(hass, access_token)
    communicator = Communicator(hass, discord_bot_url, discord_bot_ws_url)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN] = {
        "entity_manager": entity_manager,
        "communicator": communicator,
    }

    async def update_entities_periodically(now):
        """Periodically fetches entities and sends updates to Discord."""
        _LOGGER.debug("Periodic update of entities triggered.")
        entities = await entity_manager.get_entities_for_device(device_id_of_interest, entity_names_list)
        if entities:
            await communicator.send_to_discord(device_id_of_interest, entities)

    # Schedule periodic updates
    async_track_time_interval(hass, update_entities_periodically, timedelta(minutes=1))

    # State change listener for real-time updates
    async def state_change_listener(event):
        """Listens for state changes and sends updates to Discord."""
        _LOGGER.debug("State change detected, preparing to update entities.")
        entities = await entity_manager.get_entities_for_device(device_id_of_interest, entity_names_list)
        await communicator.send_to_discord(device_id_of_interest, entities)

    hass.bus.async_listen(EVENT_STATE_CHANGED, state_change_listener)

    _LOGGER.info("HomeCord Integration: Setup completed successfully.")
    return True
