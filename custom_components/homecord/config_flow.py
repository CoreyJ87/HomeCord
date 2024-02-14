import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (  # Ensure you have a const.py defining DOMAIN and any other constants
    DOMAIN,
)


class DiscordIntegrationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Validation or additional steps can be added here
            return self.async_create_entry(
                title="HomeCord Integration", data=user_input
            )

        data_schema = vol.Schema(
            {
                vol.Required("discord_bot_url"): str,
                vol.Required("device_id"): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        # Options flow if you have additional settings to configure
        return self.async_create_entry(title="", data={})
