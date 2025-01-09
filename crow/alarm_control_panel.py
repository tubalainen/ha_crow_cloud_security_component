"""
Interfaces with Crow alarm control panel.
"""
import logging

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.alarm_control_panel import AlarmControlPanelState, AlarmControlPanelEntityFeature
from homeassistant.core import HomeAssistant
from .consts import DOMAIN
import crow_security as crow


_LOGGER = logging.getLogger(__name__)

# State mappings (using AlarmControlPanelState)
state_map = {
    'armed': AlarmControlPanelState.ARMED_AWAY,
    'arm in progress': AlarmControlPanelState.ARMING,
    'stay arm in progress': AlarmControlPanelState.ARMING,
    'stay_armed': AlarmControlPanelState.ARMED_HOME,
    'disarmed': AlarmControlPanelState.DISARMED,
}

set_state_map = {
    "ARMED_HOME": "stay",
    "ARMED_AWAY": "arm",
    "DISARM": "disarm",
}

async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities,
):
    hub = hass.data[DOMAIN]
    alarms = []
    areas = await hub.panel.get_areas()
    alarms.extend([CrowAlarm(hub.panel, area) for area in areas])
    async_add_entities(alarms)


class CrowAlarm(alarm.AlarmControlPanelEntity):
    """Representation of a Crow alarm status."""

    def __init__(self, panel: crow.Panel, area):
        """Initialize the Crow alarm panel."""
        self._panel = panel
        self._area = area
        # Use DISARMED as the fallback state if not found in state_map
        self._state = state_map.get(self._area.get('state'), AlarmControlPanelState.DISARMED)

    @property
    def name(self):
        """Return the name of the device."""
        return '{} {}'.format(self._panel.name, self._area.get('name'))

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def alarm_state(self):
        """Return the current state of the alarm."""
        return self._state

    async def async_update(self):
        """Update alarm status."""
        tmp = await self._panel.get_area(self._area.get('id'))
        _LOGGER.debug("Area type is %s" % type(tmp))
        if tmp is not None and isinstance(tmp, dict):
            self._area = tmp
        _LOGGER.debug("Updating Crow area %s" % self._area.get('name'))

        # Use DISARMED as fallback state if the state is unknown
        self._state = state_map.get(self._area.get('state'), AlarmControlPanelState.DISARMED)
        if self._state == AlarmControlPanelState.DISARMED:
            _LOGGER.error('Unknown alarm state %s', self._area.get('state'))

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        await self._async_set_arm_state(AlarmControlPanelState.DISARMED, code)

    async def async_alarm_arm_home(self, code=None):
        """Send arm home command."""
        await self._async_set_arm_state(AlarmControlPanelState.ARMED_HOME, code)

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        await self._async_set_arm_state(AlarmControlPanelState.ARMED_AWAY, code)

    async def async_alarm_trigger(self, code=None):
        """Trigger alarm."""
        pass

    async def async_alarm_arm_custom_bypass(self, code=None):
        """Custom bypass command."""
        pass

    async def _async_set_arm_state(self, state, code=None):
        """Send set arm state command."""
        _LOGGER.info('Crow set arm state %s', state)
        try:
            area = await self._panel.set_area_state(self._area.get('id'), set_state_map.get(state, "disarm"))
            if area:
                self._area = area
        except crow.crow.ResponseError as err:
            _LOGGER.error(err)
            if err.status_code != 408:
                raise err

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return (
            AlarmControlPanelEntityFeature.ARM_HOME |
            AlarmControlPanelEntityFeature.ARM_AWAY |
            AlarmControlPanelEntityFeature.ARM_CUSTOM_BYPASS |
            AlarmControlPanelEntityFeature.TRIGGER
        )
