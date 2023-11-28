"""
Adds Support for Atag One Thermostat

Author: herikw
https://github.com/herikw/home-assistant-custom-components

"""

from homeassistant.helpers.typing import StateType
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN, _LOGGER, 
    WEATHER_STATES, BOILER_STATES, 
    ATAG_SENSOR_ENTITIES, 
    AtagOneSensorEntityDescription
)

from . import AtagOneEntity

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Initialize sensor platform from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([AtagOneSensor(coordinator, sensor) for sensor in ATAG_SENSOR_ENTITIES])
    

class AtagOneSensor(AtagOneEntity, SensorEntity):
    """Representation of a AtagOne Sensor."""
    _attr_has_entity_name = True
    entity_description: AtagOneSensorEntityDescription
    
    def __init__(self, coordinator, description: AtagOneSensorEntityDescription) -> None:
        """Initialize the sensor."""

        super().__init__(coordinator, description)
 
        self.coordinator = coordinator
        
        self.entity_description = description
        self._sensor_prefix = "atag_one"

        self._attr_unique_id = f"{self._sensor_prefix}_{self.entity_description.key}"
        self._attr_name = f"{self.entity_description.name}"
        self._attr_translation_key = f"{self.entity_description.translation_key}"
        self._attr_device_class = self.entity_description.device_class
        self._attr_entity_category = self.entity_description.entity_category
        self._attr_native_unit_of_measurement = self.entity_description.native_unit_of_measurement
        
        """
        _LOGGER.error("sensor: %s %s", self._attr_unique_id,description)
        """
    
    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""

        state = self.entity_description.get_native_value(self, self.entity_description.key)
        
        if self.entity_description.key == "weather_status":
            self._attr_icon = WEATHER_STATES[state].get("icon")
            return WEATHER_STATES[state].get("state")
        elif self.entity_description.key == "boiler_status":
            cstate = int(state) & 14
            if BOILER_STATES[cstate] is None:
                _LOGGER.error("Unkown Boiler State %s", cstate)
            else:
                self._attr_icon = BOILER_STATES[cstate].get("icon")
            return BOILER_STATES[cstate].get("state")
        elif self.entity_description.key == "charge_status":
            if state == 1:
                return "Charging" 
            else:
                return "Idle"
            
        return state
