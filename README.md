# Claude Search Skill

[![GitHub stars](https://img.shields.io/github/stars/danwt/claude-search-skill?style=flat-square)](https://github.com/danwt/claude-search-skill/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/danwt/claude-search-skill?style=flat-square)](https://github.com/danwt/claude-search-skill/network/members)
[![GitHub issues](https://img.shields.io/github/issues/danwt/claude-search-skill?style=flat-square)](https://github.com/danwt/claude-search-skill/issues)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?style=flat-square&logo=docker)](https://www.docker.com/)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-blueviolet?style=flat-square)](https://claude.ai/claude-code)

> Self-hosted web search and scraping for Claude Code with smart LLM compression

A local Docker stack that gives Claude Code powerful web search and scraping capabilities without relying on external MCP servers. Uses SearXNG (meta-search across 70+ engines) and Crawl4AI (Playwright-based scraping) with an optional compression layer that lets Claude control how much detail to retrieve.

## Features

- **Privacy-first search** - SearXNG aggregates results without tracking
- **JavaScript-capable scraping** - Crawl4AI renders pages with Playwright
- **Smart compression** - Optional LLM layer (via OpenRouter) compresses results using natural language instructions
- **Claude Code integration** - Works as a skill, no MCP complexity
- **Fully local** - Everything runs on your machine via Docker

## Quick Start

```bash
# Clone
git clone https://github.com/danwt/claude-search-skill.git
cd claude-search-skill

# Configure (optional - only needed for compression)
cp .env.example .env
# Edit .env and add your OpenRouter API key

# Start
docker compose up -d

# Verify
curl -s "http://localhost:8001/health" | jq
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Claude Code                          │
│                         │                               │
│                    /web-search skill                    │
│                         │                               │
│                      curl/bash                          │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Proxy Service (port 8001)                  │
│         ┌───────────────┴───────────────┐               │
│         │                               │               │
│         ▼                               ▼               │
│    ┌─────────┐                   ┌───────────┐          │
│    │ SearXNG │                   │ Crawl4AI  │          │
│    │  :8080  │                   │   :8000   │          │
│    └─────────┘                   └───────────┘          │
│         │                               │               │
│         └───────────┬───────────────────┘               │
│                     ▼                                   │
│          ┌─────────────────────┐                        │
│          │  LLM Compression    │ (optional)             │
│          │   via OpenRouter    │                        │
│          └─────────────────────┘                        │
└─────────────────────────────────────────────────────────┘
```

## Usage

### Search

```bash
# Basic search
curl -s "http://localhost:8001/search?q=rust+async+tutorial&format=json" | jq '.results[:5]'

# With compression - natural language instruction controls output
curl -s "http://localhost:8001/search?q=rust+async+tutorial&format=json&compress=true&instruction=brief+summary+with+links"

# Detailed compression
curl -s "http://localhost:8001/search?q=climate+change+2025&format=json&compress=true&instruction=comprehensive+analysis+preserving+all+facts+and+sources"

# Minimal compression
curl -s "http://localhost:8001/search?q=weather+london&format=json&compress=true&instruction=just+temperature+today"
```

### Scrape

```bash
# Basic scrape
curl -s -X POST "http://localhost:8001/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' | jq '.markdown'

# With compression
curl -s -X POST "http://localhost:8001/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://docs.example.com", "compress": true, "instruction": "extract API endpoints and parameters"}'

# Target specific element
curl -s -X POST "http://localhost:8001/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "css_selector": "article"}'
```

### Search Options

| Parameter | Description |
|-----------|-------------|
| `q` | Search query (required) |
| `format` | Response format, use `json` |
| `compress` | Enable LLM compression (`true`/`false`) |
| `instruction` | Natural language instruction for compression |
| `categories` | Filter: `images`, `news`, `videos`, `science`, `files`, `it` |
| `time_range` | Filter: `day`, `week`, `month`, `year` |
| `pageno` | Page number for pagination |

## Claude Code Integration

### Install the Skill

Copy the skill file to your Claude skills directory:

```bash
mkdir -p ~/.claude/skills/web-search
cp skill/SKILL.md ~/.claude/skills/web-search/SKILL.md
```

Or create `~/.claude/skills/web-search/SKILL.md` with content from [skill/SKILL.md](skill/SKILL.md).

### Use It

Ask Claude to use the web-search skill:

- "use /web-search to find the latest React 19 features"
- "search for kubernetes best practices using web-search"
- "/web-search trump greenland controversy"

Claude will use the compression instruction to control how detailed the response is based on your needs.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | - | Required for compression |
| `OPENROUTER_MODEL` | `google/gemini-2.0-flash-lite-001` | Compression model |
| `COMPRESSION_PROMPT` | (see .env.example) | System prompt for compression |
| `SEARXNG_SECRET` | - | SearXNG secret key |

### Recommended Models for Compression

| Model | Cost (per 1M tokens) | Notes |
|-------|---------------------|-------|
| `google/gemini-2.0-flash-lite-001` | $0.075 in / $0.30 out | Best value |
| `google/gemini-2.0-flash-001` | $0.10 in / $0.40 out | Slightly smarter |
| `google/gemini-2.0-flash-exp:free` | Free (rate limited) | Testing only |

At ~$0.0024 per compression, you can do **~400 compressions per dollar**.

## Services

| Service | Port | Purpose |
|---------|------|---------|
| **Proxy** | 8001 | Main endpoint - use this |
| SearXNG | 8080 | Meta-search engine |
| Crawl4AI | 8000 | Web scraper |
| Redis | 6379 | Caching |

## Commands

```bash
# Start
docker compose up -d

# Stop
docker compose down

# View logs
docker logs search-proxy
docker logs searxng
docker logs crawl4ai-service

# Restart
docker compose restart

# Rebuild after changes
docker compose up -d --build
```

## Why Not MCP?

This project uses a Claude skill instead of MCP because:

1. **Simpler** - No separate MCP server process to manage
2. **Transparent** - Claude uses regular bash/curl, easy to debug
3. **Flexible** - The skill file is just markdown instructions you can customize

## Attribution

Based on [Bionic-AI-Solutions/open-search](https://github.com/Bionic-AI-Solutions/open-search), simplified and adapted for Claude Code skill-based usage.

## License

MIT
