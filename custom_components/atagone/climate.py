"""
Adds Support for Atag One Thermostat

Author: herikw
https://github.com/herikw/home-assistant-custom-components

"""

import logging
from typing import Any
import voluptuous as vol

from .util import atag_date, atag_time
from . import AtagOneEntity

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import ServiceCall
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, PLATFORM_SCHEMA
from homeassistant.helpers import config_validation

from homeassistant.components.climate.const import (
    HVACMode,
    HVACAction,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_HOST,
    CONF_PORT,
    CONF_NAME,
    TEMP_CELSIUS,
)

from .const import (
    DOMAIN,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DEFAULT_NAME,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): config_validation.string,
        vol.Optional(CONF_HOST): config_validation.string,
        vol.Optional(CONF_PORT, default=10000): config_validation.positive_int,
    }
)

ATTR_END_DATE = "end_date"
ATTR_END_TIME = "end_time"
ATTR_HEAT_TEMP = "heat_temp"
ATTR_START_DATE = "start_date"
ATTR_START_TIME = "start_time"

SERVICE_CREATE_VACATION = "create_vacation"
SERVICE_CANCEL_VACATION = "cancel_vacation"

DEFAULT_RESUME_ALL = False

HA_HVAC_MODE_TO_ATAG = {HVACMode.AUTO: 1, HVACMode.HEAT: 0}
ATAG_HVAC_MODE_TO_HA = {v: k for k, v in HA_HVAC_MODE_TO_ATAG.items()}

HA_PRESETS_TO_ATAG = { 
    "Manual": 1,
    "Auto": 2,
    "Holiday": 3,
    "Extend": 4,
    "Fireplace": 5
}
ATAG_PRESETS_TO_HA = {v: k for k, v in HA_PRESETS_TO_ATAG.items()}

DTGROUP_INCLUSIVE_MSG = (
    f"{ATTR_START_DATE}, {ATTR_START_TIME}, {ATTR_END_DATE}, "
    f"and {ATTR_END_TIME} must be specified together"
)

CREATE_VACATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): config_validation.entity_id,
        vol.Required(ATTR_HEAT_TEMP): vol.Coerce(float),
        vol.Inclusive(ATTR_START_DATE, "dtgroup", msg=DTGROUP_INCLUSIVE_MSG): atag_date,
        vol.Inclusive(ATTR_START_TIME, "dtgroup", msg=DTGROUP_INCLUSIVE_MSG): atag_time,
        vol.Inclusive(ATTR_END_DATE, "dtgroup", msg=DTGROUP_INCLUSIVE_MSG): atag_date,
        vol.Inclusive(ATTR_END_TIME, "dtgroup", msg=DTGROUP_INCLUSIVE_MSG): atag_time,
    }
)

CANCEL_VACATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): config_validation.entity_id,
    }
)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Setup Atag One Thermostat"""

    entities = []
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities.append(AtagOneThermostat(coordinator, "climate"))

    async_add_entities(entities)

    @callback
    async def create_vacation_service(service: ServiceCall) -> None:
        """Create a vacation on the target thermostat."""
        entity_id = service.data[ATTR_ENTITY_ID]

        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                await thermostat.create_vacation(service.data)
                thermostat.schedule_update_ha_state(True)
                break

    @callback
    async def cancel_vacation_service(service: ServiceCall) -> None:
        """Cancel a vacation on the target thermostat."""
        entity_id = service.data[ATTR_ENTITY_ID]

        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                await thermostat.cancel_vacation()
                thermostat.schedule_update_ha_state(True)
                break

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_VACATION,
        create_vacation_service,
        schema=CREATE_VACATION_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CANCEL_VACATION,
        cancel_vacation_service,
        schema=CANCEL_VACATION_SCHEMA,
    )


class AtagOneThermostat(AtagOneEntity, ClimateEntity):
    """Representation of a Atag One device"""

    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.AUTO]
    _attr_preset_modes = list(HA_PRESETS_TO_ATAG.keys())
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )

    def __init__(self, coordinator, atagone_id) -> None:

        """Initialize"""
        super().__init__(coordinator, atagone_id)

        self.data = atagone_id
        self._icon = "mdi:thermostat"
        self._name = DEFAULT_NAME
        self._min_temp = DEFAULT_MIN_TEMP
        self._max_temp = DEFAULT_MAX_TEMP


    async def create_vacation(self, service_data) -> None:
        """Create a vacation with user-specified parameters."""

        await self.coordinator.data.async_create_vacation(
            service_data.get(ATTR_START_DATE),
            service_data.get(ATTR_START_TIME),
            service_data.get(ATTR_END_DATE),
            service_data.get(ATTR_END_TIME),
            service_data.get(ATTR_HEAT_TEMP),
        )

    async def cancel_vacation(self) -> None:
        """Delete a vacation with the specified name."""
        await self.coordinator.data.async_cancel_vacation()

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        return self.coordinator.data.current_temp

    @property
    def target_temperature(self) -> float:
        """Return the temperature we try to reach."""
        return self.coordinator.data.current_setpoint

    @property
    def hvac_action(self) -> str:
        """Return the current running hvac operation if supported"""
        if self.coordinator.data.heating:
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def should_poll(self) -> bool:
        """Return the polling state."""
        return True

    @property
    def name(self) -> str:
        """Return the name of the climate device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the binary sensor."""
        return self._name

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        if self._min_temp:
            return self._min_temp

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        if self._max_temp:
            return self._max_temp

    @property
    def hvac_modes(self) -> list[str]:
        """Return the list of available hvac operation modes. """
        return [HVACMode.HEAT, HVACMode.AUTO]

    @property
    def hvac_mode(self) -> str:
        atag_hvac = self.coordinator.data.mode
        return ATAG_HVAC_MODE_TO_HA.get(atag_hvac)
    
    @property
    def preset_mode(self) -> str:
        """Set new target hvac mode."""
        preset_mode = self.coordinator.data.preset
        return ATAG_PRESETS_TO_HA.get(preset_mode)

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        atag_hvac = HA_HVAC_MODE_TO_ATAG.get(hvac_mode, HVACMode.AUTO)
        
        status = await self.coordinator.data.send_dynamic_change("ch_control_mode", atag_hvac)
        if not status:
            _LOGGER.error("ch_control_mode: %s", status)
            
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        atag_preset = HA_PRESETS_TO_ATAG.get(preset_mode, "Auto" )
        status = await self.coordinator.data.send_dynamic_change("ch_mode", atag_preset)
        if not status:
            _LOGGER.error("ch_mode: %s", status)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""

        target_temp = kwargs.get(ATTR_TEMPERATURE)
        if target_temp is None:
            return
        else:
            status = await self.coordinator.data.send_dynamic_change("ch_mode_temp", target_temp)
            if not status:
                _LOGGER.error("ch_mode_temp: %s", status)