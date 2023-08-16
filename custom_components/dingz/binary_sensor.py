from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import api
from .const import DOMAIN
from .helpers import UserAssignedNameMixin
from .shared import Shared, StateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    shared: Shared = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[BinarySensorEntity] = []
    for index in range(len(shared.config.data.inputs)):
        entities.append(Input(shared.state, index=index))

    try:
        nr_pirs = len(shared.state.data["sensors"]["pirs"])
    except LookupError:
        nr_pirs = 0
    for index in range(nr_pirs):
        entities.append(Motion(shared.state, index=index))

    async_add_entities(entities)


class Input(
    CoordinatorEntity[StateCoordinator], BinarySensorEntity, UserAssignedNameMixin
):
    def __init__(self, coordinator: StateCoordinator, *, index: int) -> None:
        super().__init__(coordinator)

        self.__index = index

        self._attr_has_entity_name = True
        self._attr_unique_id = f"{self.coordinator.shared.mac_addr}-input-{index}"
        self._attr_device_info = self.coordinator.shared.device_info
        self._attr_translation_key = "input"

    @property
    def dingz_input(self) -> api.InputConfig:
        try:
            return self.coordinator.shared.config.data.inputs[self.__index]
        except LookupError:
            return api.InputConfig()

    @property
    def entity_registry_enabled_default(self) -> bool:
        return self.dingz_input.get("active", False)

    @property
    def comp_index(self) -> int:
        return self.__index

    @property
    def user_given_name(self) -> str | None:
        return self.dingz_input.get("name")

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        try:
            input_ty = self.dingz_input["input"]["type"]
        except LookupError:
            return None

        if input_ty.startswith("pir_"):
            return BinarySensorDeviceClass.MOTION
        elif input_ty == "garage_door_state":
            return BinarySensorDeviceClass.GARAGE_DOOR
        else:
            return None

    @property
    def is_on(self) -> bool | None:
        try:
            raw = self.coordinator.data["sensors"]["input_state"]
        except LookupError:
            return None

        try:
            invert = self.dingz_input["input"]["invert"]
        except LookupError:
            invert = False
        return raw != invert


class Motion(CoordinatorEntity[StateCoordinator], BinarySensorEntity):
    def __init__(self, coordinator: StateCoordinator, *, index: int) -> None:
        super().__init__(coordinator)

        self.__index = index

        self._attr_has_entity_name = True
        self._attr_unique_id = f"{self.coordinator.shared.mac_addr}-motion-{index}"
        self._attr_device_info = self.coordinator.shared.device_info
        self._attr_device_class = BinarySensorDeviceClass.MOTION
        self._attr_translation_key = f"motion_{index}"

    @property
    def dingz_pir(self) -> api.SensorPir:
        try:
            raw = self.coordinator.data["sensors"]["pirs"][self.__index]
        except LookupError:
            return api.SensorPir()
        if raw is None:
            return api.SensorPir()
        return raw

    @property
    def entity_registry_enabled_default(self) -> bool:
        return self.dingz_pir.get("enabled", False)

    @property
    def is_on(self) -> bool | None:
        return self.dingz_pir.get("motion")
