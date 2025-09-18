# Ollama Enhanced

Enhance your Home Assistant Ollama conversations with web search capabilities, just like OpenWebUI!

## What This Integration Does

This enhanced version replaces the official Home Assistant Ollama integration while maintaining full compatibility and adding intelligent web search functionality. When you ask questions that would benefit from current information, it automatically searches the web and includes relevant results in the conversation context.

## Key Features

- **Smart Search Detection**: Automatically detects when your questions need web search
- **Multiple Search Providers**: SearXNG, DuckDuckGo, Google, Bing, or custom APIs
- **Privacy-Focused**: Use self-hosted SearXNG for complete privacy
- **Easy Configuration**: Simple setup through the Home Assistant UI
- **Seamless Integration**: Drop-in replacement for the official Ollama integration

## Quick Start

1. Install this integration
2. Configure your Ollama server connection
3. Set up a search provider (SearXNG recommended)
4. Create a conversation agent with web search enabled
5. Start asking questions with current information needs!

## Example Usage

Ask questions like:
- "What's the latest news about Home Assistant?"
- "Tell me about recent AI developments"
- "Search for information about solar panel efficiency"
- "What happened today in technology?"

The integration will automatically search the web and provide your LLM with current, relevant information to answer your questions.

## Requirements

- Home Assistant 2024.4.0 or later
- Running Ollama server
- Internet connection for web searches
- Optional: Self-hosted SearXNG instance (recommended for privacy)

Perfect for getting up-to-date information in your Home Assistant conversations without leaving the comfort of your smart home interface!