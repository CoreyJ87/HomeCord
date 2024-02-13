# Discord Integration for Home Assistant

This custom integration for Home Assistant enables communication between Home Assistant and Discord. It allows for sending updates to Discord when the state of any entity associated with a specified device changes, and it can send all entity details for a device upon demand.

## Features

- **State Change Notifications**: Automatically sends a message to a specified Discord channel when the state of any entity associated with the device changes.
- **Manual Trigger**: Provides a service to manually send all entity details of a specified device to Discord.

## Setup

1. **Installation**: To install this custom integration, copy the `discord_integration` folder into your `custom_components` directory in your Home Assistant configuration directory.
2. **Configuration**: Add the following to your `configuration.yaml` file:

```yaml
discord_integration:
```

3. **Services**: This integration adds a service called `discord_integration.send_to_discord` that you can call with a device ID to send all related entity states to Discord.

## Usage

### Sending Device Entity Updates to Discord

To manually trigger an update, call the `discord_integration.send_to_discord` service with the following payload:

```yaml
service: discord_integration.send_to_discord
data:
  device_id: "your_device_id_here"
```

### Automations

You can also use this integration within automations to react to specific Home Assistant events, like so:

```yaml
alias: Notify Discord on Device State Change
trigger:
  - platform: state
    entity_id: light.living_room
action:
  - service: discord_integration.send_to_discord
    data:
      device_id: "your_device_id_here"
```

## Development

This integration is developed to work with Home Assistant Core. If you encounter any issues or have feature requests, please submit them to the project's GitHub repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
