from .const import DOMAIN
from .entity_manager import EntityManager
from .communicator import Communicator
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from .const import (  # Ensure you have a const.py defining DOMAIN and any other constants
    DOMAIN,
)
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
import logging
listeners = []
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
        _LOGGER.debug("Periodic update started at %s", now)
        try:
            entities = await entity_manager.get_entities_for_device(device_id_of_interest, entity_names_list)
            # Fetch the state of 'current_stage' sensor directly from the Home Assistant state machine
            current_stage_state = hass.states.get('sensor.p1s_01p00a3c0300850_current_stage')

            if current_stage_state and current_stage_state.state == "printing":
                await communicator.send_to_discord(device_id_of_interest, entities)
            else:
                _LOGGER.info("Skipped sending update to Discord. 'current_stage' not in 'printing' state.")
        except Exception as e:
            _LOGGER.error("Error during get_entities_for_device or send_to_discord: %s", e)

    async def state_change_listener(event):
        """Listens for state changes and sends updates to Discord selectively based on the entity and state."""
        entity_id = event.data.get("entity_id")
        current_stage_entity_id = 'sensor.p1s_01p00a3c0300850_current_stage'
        current_stage_state = hass.states.get(current_stage_entity_id).state

        # Always send updates for the current stage entity itself
        if entity_id == current_stage_entity_id:
            await send_update_for_entity(entity_id)
        # For other entities, send updates only if the current stage is "printing"
        elif current_stage_state == "printing":
            await send_update_for_entity(entity_id)

    async def send_update_for_entity(entity_id):
        """Sends update for a given entity ID to Discord."""
        entity_entry = er.async_get(hass).async_get(entity_id)

        if entity_entry and entity_entry.device_id == device_id_of_interest:
            _LOGGER.debug(f"State change detected for {entity_id}, preparing to update entity.")

            # Fetch the state of the updated entity
            entity_state = hass.states.get(entity_id)
            if entity_state:
                entity_data = {
                    "entity_id": entity_state.entity_id,
                    "state": entity_state.state,
                    "attributes": entity_state.attributes,
                    "last_changed": entity_state.last_changed.isoformat(),
                }

                # Determine if this entity is a camera or image entity to fetch snapshot
                if "camera" in entity_id or "image" in entity_id:
                    snapshot_data = await entity_manager.fetch_entity_snapshot(entity_id)
                    if snapshot_data:
                        entity_data["snapshot"] = entity_manager.encode_snapshot_data(snapshot_data)

                # Now send only the updated entity's data
                await communicator.send_to_discord(device_id_of_interest, [entity_data])  # Wrap entity_data in a list

    async def shutdown():
        if "communicator" in hass.data[DOMAIN]:
            await hass.data[DOMAIN]["communicator"].close_websocket_connection()

            while listeners:
                deregister = listeners.pop()
                deregister()

            _LOGGER.info("HomeCord Integration: Resources cleaned up successfully.")

    async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
        if "communicator" in hass.data[DOMAIN]:
            await hass.data[DOMAIN]["communicator"].close_websocket_connection()


        while listeners:
            deregister = listeners.pop()
            deregister()

        _LOGGER.info("HomeCord Integration: Resources cleaned up successfully.")
        return True

    entry.async_on_unload(entry.add_update_listener(async_unload_entry))
    hass.bus.async_listen_once("homeassistant_stop", shutdown)
    listeners.append(hass.bus.async_listen(EVENT_STATE_CHANGED, state_change_listener))

    #_LOGGER.debug("Scheduling periodic updates.")
    #async_track_time_interval(hass, update_entities_periodically, timedelta(minutes=1))
    #_LOGGER.debug("Periodic updates scheduled.")

    _LOGGER.info("HomeCord Integration: Setup completed successfully.")
    return True
