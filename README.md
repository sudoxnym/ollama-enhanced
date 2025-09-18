# Ollama Enhanced for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An enhanced version of the official Home Assistant Ollama integration with web search capabilities, similar to OpenWebUI's search functionality. This replaces the official integration while maintaining full compatibility and adding powerful web search features.

## Features

✅ **Multiple Search Providers**
- SearXNG (self-hosted search)
- DuckDuckGo (official API)
- Google Custom Search (API key required)
- Bing Search (API key required)
- Custom providers (any JSON-based search API)

✅ **Smart Search Triggering**
Automatically detects when to perform web searches based on keywords:
- "search for", "look up", "find information about"
- "what is", "tell me about", "latest news"
- "current events", "recent", "today", "this week"
- Year references (2024, 2025)

✅ **Configurable Settings**
- Enable/disable web search per conversation agent
- Choose search provider and URL
- Set number of search results (1-20)
- Works alongside the official Ollama integration

✅ **Seamless Integration**
- Search results are automatically included in conversation context
- LLM receives both user query and relevant web search results
- Graceful error handling - conversations continue even if search fails

## Installation

### Option 1: HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots menu and select "Custom repositories"
4. Add this repository URL: `https://github.com/sudoxnym/ollama-enhanced`
5. Select "Integration" as the category
6. Click "Add"
7. Search for "Ollama Enhanced" and install it
8. Restart Home Assistant

### Option 2: Manual Installation

1. Download the latest release from [GitHub releases](https://github.com/sudoxnym/ollama-enhanced/releases)
2. Extract the `custom_components/ollama` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

### Prerequisites

1. **Ollama Server**: You need a running Ollama server
2. **Search Provider**: Choose one of the supported search providers:
   - **SearXNG**: Self-hosted search engine (recommended for privacy)
   - **DuckDuckGo**: Uses the free official API (limited results)
   - **Custom**: Any JSON-based search API

### Setup Steps

1. **Install the Integration**
   - Go to Settings → Devices & Services
   - Click "Add Integration"
   - Search for "Ollama Enhanced"
   - Click to add it

2. **Configure Ollama Connection**
   - Enter your Ollama server URL (e.g., `http://localhost:11434`)
   - Test the connection

3. **Add Conversation Agent**
   - Click "Add conversation agent"
   - Choose your model
   - Configure conversation settings

4. **Enable Web Search**
   - Toggle "Enable web search" to ON
   - Select your search provider
   - Enter the search URL:
     - SearXNG: `http://your-searxng-instance:8080`
     - DuckDuckGo: Leave default (uses official API)
     - Custom: Your custom search API endpoint
   - Set the number of search results (default: 5)

## Search Providers Setup

### SearXNG (Recommended)

SearXNG is a privacy-respecting metasearch engine that you can self-host:

1. **Docker Setup**:
   ```bash
   docker run -d \
     --name searxng \
     -p 8080:8080 \
     -v ${PWD}/searxng:/etc/searxng \
     searxng/searxng:latest
   ```

2. **Enable JSON output**: SearXNG must allow JSON responses or the integration will receive HTTP 403 errors. In your `settings.yml`, ensure the following block is present:
   ```yaml
   search:
     formats:
       - html
       - json
   ```
   Typical locations:
   - Debian/Ubuntu packages: `/etc/searxng/settings.yml`
   - Docker/systemd installs: the path you mounted into the container (`SEARXNG_SETTINGS_PATH`)

3. **Restart SearXNG** to apply the configuration change.

4. **Configuration**: Use `http://localhost:8080` as your search URL

### DuckDuckGo

Uses the official DuckDuckGo Instant Answer API (free but limited):
- No setup required
- Limited to instant answers and related topics
- Good for quick facts and definitions

### Custom Provider

For any JSON-based search API:
1. Set your API endpoint as the search URL
2. The integration expects JSON responses with `results` array
3. Each result should have `title`, `url`, and `content` fields

## Usage Examples

Once configured, simply ask questions that would benefit from web search:

**Examples that trigger web search:**
- "What's the latest news about AI?"
- "Tell me about recent developments in Home Assistant"
- "Search for information about electric vehicles"
- "What happened today in technology?"
- "Look up the weather in Tokyo"

**The integration will:**
1. Detect search triggers in your question
2. Perform a web search using your configured provider
3. Include relevant results in the conversation context
4. Let the LLM provide an informed response with current information

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| **Web Search Enabled** | Enable/disable web search functionality | `false` |
| **Search Provider** | Choose search provider (SearXNG, DuckDuckGo, etc.) | `searxng` |
| **Search URL** | Base URL for your search provider | `http://localhost:8080` |
| **Search Results Count** | Number of search results to include (1-20) | `5` |

## Troubleshooting

### Common Issues

**1. Search Not Working**
- Check if web search is enabled in conversation agent settings
- Verify search provider URL is accessible
- Check Home Assistant logs for error messages

**2. SearXNG Connection Issues**
- Ensure SearXNG is running and accessible
- Check firewall settings
- Verify the URL format (include `http://` or `https://`)

**3. No Search Results**
- Try different search providers
- Check if the search query contains trigger words
- Verify the search provider is returning JSON responses

### Logs

Enable debug logging by adding to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.ollama.web_search: debug
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 🐛 [Report a Bug](https://github.com/sudoxnym/ollama-enhanced/issues)
- 💡 [Request a Feature](https://github.com/sudoxnym/ollama-enhanced/issues)
