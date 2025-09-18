# ollama enhanced for home assistant

![hacs custom badge](https://img.shields.io/badge/hacs-custom-orange.svg)
![mit license badge](https://img.shields.io/badge/license-mit-yellow.svg)

an enhanced fork of the home assistant ollama integration that mirrors openwebui's searxng behaviour and adds flexible web search support.

## features

- multiple search providers: searxng, duckduckgo, google custom search, bing, or any json api
- smart search triggers that react to phrases like "search for", "look up", "latest news", and year references
- configurable result counts and provider urls per conversation agent
- seamless injection of search snippets into the llm prompt so conversations stay current
- graceful fallbacks when a provider fails so the chat still replies

## installation

### option 1: hacs (recommended)

1. open hacs in home assistant
2. go to "integrations"
3. click the three dots menu and choose "custom repositories"
4. add `https://github.com/sudoxnym/ollama-enhanced`
5. select "integration" as the category
6. click "add"
7. search for "ollama enhanced" and install
8. restart home assistant

### option 2: manual install

1. download the latest release from https://github.com/sudoxnym/ollama-enhanced/releases
2. copy `custom_components/ollama` into your home assistant `custom_components` directory
3. restart home assistant

## configuration

### prerequisites

- a running ollama server
- optionally a self-hosted searxng instance (recommended for privacy)
- alternatively an api key for another provider (duckduckgo, google, bing, custom)

### setup steps

1. install the integration: settings → devices & services → add integration → "ollama enhanced"
2. configure the ollama server url (for example `http://localhost:11434`) and test the connection
3. create a conversation agent, pick your model, and adjust history or prompt settings
4. enable web search, choose the provider, enter its base url, and set how many results to include (1-20)

## searxng setup tips

searxng must allow json output or the integration will receive 403 responses.

1. run searxng (docker example):
   ```bash
   docker run -d \
     --name searxng \
     -p 8080:8080 \
     -v ${PWD}/searxng:/etc/searxng \
     searxng/searxng:latest
   ```
2. edit `settings.yml` and ensure:
   ```yaml
   search:
     formats:
       - html
       - json
   ```
   common locations:
   - debian/ubuntu packages: `/etc/searxng/settings.yml`
   - docker/systemd installs: the path mounted via `SEARXNG_SETTINGS_PATH`
3. restart searxng to apply the change
4. use the base url (for example `http://your-searxng-instance:8080`) in the integration

## usage tips

ask questions that imply fresh information, such as:
- "what's new with home assistant this week?"
- "search for recent ai model releases"
- "look up the latest news on smart homes"
- "find information about solar incentives in 2025"

when the trigger logic fires, the integration fetches results, merges them into the system prompt, and the llm responds with the latest context it can see.

## troubleshooting

- if you get 403 errors with searxng, double-check that json is enabled and the url includes any required tokens.
- verify home assistant can reach the provider url by running curl from the same host.
- enable debug logging by adding to `configuration.yaml`:
  ```yaml
  logger:
    logs:
      custom_components.ollama.web_search: debug
  ```

## contributing

issues and pull requests are welcome at https://github.com/sudoxnym/ollama-enhanced/issues

## license

released under the mit license. see [license](LICENSE) for details.
