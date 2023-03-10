"""Gaspy sensors"""
from datetime import datetime, timedelta

import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_MAXIMUM, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.helpers.entity import Entity

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .api import GaspyApi

from .const import (
    DOMAIN,
    SENSOR_NAME
)

NAME = DOMAIN
ISSUEURL = "https://github.com/codyc1515/hacs_gaspy/issues"

STARTUP = f"""
-------------------------------------------------------------------
{NAME}
This is a custom component
If you have any issues with this you need to open an issue here:
{ISSUEURL}
-------------------------------------------------------------------
"""

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_MAXIMUM): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=100.0)),
    vol.Required(CONF_LATITUDE): cv.string,
    vol.Required(CONF_LONGITUDE): cv.string
})

SCAN_INTERVAL = timedelta(minutes=60)

async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    distance = config.get(CONF_MAXIMUM)
    latitude = config.get(CONF_LATITUDE)
    longitude = config.get(CONF_LONGITUDE)

    api = GaspyApi(username, password, distance, latitude, longitude)

    _LOGGER.debug('Setting up sensor(s)...')

    sensors = []
    sensors .append(GaspyFuelPriceSensor(SENSOR_NAME, api))
    async_add_entities(sensors, True)

class GaspyFuelPriceSensor(Entity):
    def __init__(self, name, api):
        self._name = name
        self._icon = "mdi:gas-station"
        self._state = ""
        self._state_attributes = {}
        self._state_class = "measurement"
        self._unit_of_measurement = '$'
        self._unique_id = DOMAIN
        self._api = api

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def state_class(self):
        """Return the state class of the device."""
        return self._state_class

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self._state_attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    def update(self):
        _LOGGER.debug('Checking login validity')
        if self._api.login():
            # Get todays date
            _LOGGER.debug('Fetching prices')
            data = []
            response = self._api.get_prices()
            if response['data']:
                _LOGGER.debug(response['data'])
                for station in response['data']:
                    # Avoid updating the price (state) if the price is still the same or we will get duplicate notifications
                    if self._state == float(station['current_price']) / 100:
                        break
                    
                    self._state = float(station['current_price']) / 100
                    
                    self._state_attributes['Fuel Type Name'] = station['fuel_type_name']
                    self._state_attributes['Station Name'] = station['station_name']
                    self._state_attributes['Distance'] = station['distance']
                    self._state_attributes['Last Updated'] = station['date_updated']
                    
                    # Because we are ordering by lowest price in the API call, to get the lowest price we only ever need the first result
                    break
            else:
                self._state = "None"
                _LOGGER.debug('Found no prices on refresh')
        else:
            _LOGGER.error('Unable to log in')
