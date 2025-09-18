"""The conversation platform for the Ollama integration."""

from __future__ import annotations

from typing import Literal

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import CONF_LLM_HASS_API, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import OllamaConfigEntry
from .const import CONF_PROMPT, CONF_WEB_SEARCH_ENABLED, DOMAIN
from .entity import OllamaBaseLLMEntity
from .web_search import WebSearchClient, format_search_results, should_trigger_search


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: OllamaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up conversation entities."""
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != "conversation":
            continue

        async_add_entities(
            [OllamaConversationEntity(config_entry, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


class OllamaConversationEntity(
    conversation.ConversationEntity,
    conversation.AbstractConversationAgent,
    OllamaBaseLLMEntity,
):
    """Ollama conversation agent."""

    _attr_supports_streaming = True

    def __init__(self, entry: OllamaConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize the agent."""
        super().__init__(entry, subentry)
        if self.subentry.data.get(CONF_LLM_HASS_API):
            self._attr_supported_features = (
                conversation.ConversationEntityFeature.CONTROL
            )

        # Initialize web search client if enabled
        self._web_search_client = None
        if self.subentry.data.get(CONF_WEB_SEARCH_ENABLED, False):
            self._web_search_client = WebSearchClient(self.hass, self.subentry.data)

    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from Home Assistant."""
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Call the API."""
        settings = {**self.entry.data, **self.subentry.data}

        # Check if we should perform a web search
        search_results = None
        import logging
        _LOGGER = logging.getLogger(__name__)

        # Debug logging
        _LOGGER.info(f"Web search client available: {self._web_search_client is not None}")
        _LOGGER.info(f"User input: '{user_input.text}'")

        if self._web_search_client and should_trigger_search(user_input.text):
            _LOGGER.info("Triggering web search...")
            try:
                search_results = await self._web_search_client.search(user_input.text)
                _LOGGER.info(f"Search returned {len(search_results) if search_results else 0} results")
            except Exception as e:
                # Log error but continue with conversation
                _LOGGER.error("Web search failed: %s", e, exc_info=True)
        else:
            if not self._web_search_client:
                _LOGGER.info("Web search not enabled or client not initialized")
            else:
                _LOGGER.info("Search trigger not activated")

        try:
            # Prepare the context with optional search results
            llm_context = user_input.as_llm_context(DOMAIN)

            # Add search results to the system prompt if available
            extra_system_prompt = user_input.extra_system_prompt
            if search_results:
                search_context = format_search_results(search_results)
                search_instruction = "IMPORTANT: Use the following current web search results to inform your response. These are real-time search results that provide current information:\n\n"
                full_search_context = search_instruction + search_context

                if extra_system_prompt:
                    extra_system_prompt = f"{extra_system_prompt}\n\n{full_search_context}"
                else:
                    extra_system_prompt = full_search_context

                _LOGGER.info("Search results added to conversation context")

            await chat_log.async_provide_llm_data(
                llm_context,
                settings.get(CONF_LLM_HASS_API),
                settings.get(CONF_PROMPT),
                extra_system_prompt,
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()

        await self._async_handle_chat_log(chat_log)

        return conversation.async_get_result_from_chat_log(user_input, chat_log)
