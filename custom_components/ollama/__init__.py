"""The Ollama Enhanced integration."""

from __future__ import annotations

import asyncio
import logging
from types import MappingProxyType

import httpx
import ollama

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.ssl import get_default_context

from .const import (
    CONF_KEEP_ALIVE,
    CONF_MAX_HISTORY,
    CONF_MODEL,
    CONF_NUM_CTX,
    CONF_PROMPT,
    CONF_SEARCH_PROVIDER,
    CONF_SEARCH_RESULTS_COUNT,
    CONF_SEARCH_URL,
    CONF_THINK,
    CONF_WEB_SEARCH_ENABLED,
    DEFAULT_AI_TASK_NAME,
    DEFAULT_NAME,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "CONF_KEEP_ALIVE",
    "CONF_MAX_HISTORY",
    "CONF_MODEL",
    "CONF_NUM_CTX",
    "CONF_PROMPT",
    "CONF_SEARCH_PROVIDER",
    "CONF_SEARCH_RESULTS_COUNT",
    "CONF_SEARCH_URL",
    "CONF_THINK",
    "CONF_URL",
    "CONF_WEB_SEARCH_ENABLED",
    "DOMAIN",
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = (Platform.AI_TASK, Platform.CONVERSATION)

type OllamaConfigEntry = ConfigEntry[ollama.AsyncClient]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Ollama Enhanced."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: OllamaConfigEntry) -> bool:
    """Set up Ollama Enhanced from a config entry."""
    settings = {**entry.data, **entry.options}
    client = ollama.AsyncClient(host=settings[CONF_URL], verify=get_default_context())
    try:
        async with asyncio.timeout(DEFAULT_TIMEOUT):
            await client.list()
    except (TimeoutError, httpx.ConnectError) as err:
        raise ConfigEntryNotReady(err) from err

    entry.runtime_data = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Ollama Enhanced."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    return True


async def async_update_options(hass: HomeAssistant, entry: OllamaConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


def _add_ai_task_subentry(hass: HomeAssistant, entry: OllamaConfigEntry) -> None:
    """Add AI Task subentry to the config entry."""
    # Add AI Task subentry with default options. We can only create a new
    # subentry if we can find an existing model in the entry. The model
    # was removed in the previous migration step, so we need to
    # check the subentries for an existing model.
    existing_model = next(
        iter(
            model
            for subentry in entry.subentries.values()
            if (model := subentry.data.get(CONF_MODEL)) is not None
        ),
        None,
    )
    if existing_model:
        hass.config_entries.async_add_subentry(
            entry,
            ConfigSubentry(
                data=MappingProxyType({CONF_MODEL: existing_model}),
                subentry_type="ai_task_data",
                title=DEFAULT_AI_TASK_NAME,
                unique_id=None,
            ),
        )
