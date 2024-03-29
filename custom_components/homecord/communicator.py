import json
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
_LOGGER = logging.getLogger(__name__)


class Communicator:
    def __init__(self, hass: HomeAssistant, discord_bot_url: str, discord_bot_ws_url: str):
        self.hass = hass
        self.discord_bot_url = discord_bot_url
        self.discord_bot_ws_url = discord_bot_ws_url
        self.ws_connection = None
        self.session = async_get_clientsession(hass)

    async def send_to_discord(self, device_id: str, entities: list):
        """Send entity updates to Discord via HTTP POST or WebSocket."""
        data_payload = {"type": "update", "device_id": device_id, "entities": entities}

        if self.ws_connection and not self.ws_connection.closed:
            await self.send_data_via_websocket(json.dumps(data_payload))
        else:
            await self.establish_websocket_connection()

    async def send_data_via_websocket(self, data: str):
        """Send data to Discord via WebSocket."""
        try:
            await self.ws_connection.send_str(data)
            _LOGGER.debug("Data sent to Discord via WebSocket.")
        except ConnectionResetError as e:
            _LOGGER.error(f"WebSocket connection error: {e}")
            # Attempt to re-establish the connection
            await self.establish_websocket_connection()
        except Exception as e:
            _LOGGER.error(f"Unexpected error when sending data via WebSocket: {e}")

    async def establish_websocket_connection(self):
        """Establish a new WebSocket connection to the Discord bot."""
        if self.ws_connection:
            await self.ws_connection.close()

        try:
            self.ws_connection = await self.session.ws_connect(self.discord_bot_ws_url)
            _LOGGER.debug("WebSocket connection successfully established.")
        except Exception as e:
            _LOGGER.error(f"Failed to establish WebSocket connection: {e}")
            self.ws_connection = None

    async def close_websocket_connection(self):
        """Close the WebSocket connection if it's open."""
        if self.ws_connection:
            await self.ws_connection.close()
            self.ws_connection = None
            _LOGGER.debug("WebSocket connection closed.")