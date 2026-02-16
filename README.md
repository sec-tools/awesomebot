# AwesomeBot

![awesomebot-logo](https://github.com/user-attachments/assets/20304c2a-6669-4d55-b4d8-a3c8855ce946)

> **This application was created exclusively for security education and research. It is NOT a chatbot platform. Do not deploy on public networks or use with real user data.**

AwesomeBot is an AI chatbot that contains many bugs and built for the purpose of bug hunting and security research. It is a full-stack chat application powered by a local LLM that contains security vulnerabilities for you to discover, exploit, and learn from in a local test environment.

The platform runs entirely on a local machine via Docker with no cloud accounts, no API keys, no external dependencies. Just clone, build and get started.

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- At least **8 GB RAM** allocated to Docker (for the default model `qwen2.5:7b`)
- ~5 GB free disk space (~4.7 GB for the default model + container images)

The platform was developed and tested with **Qwen 2.5 7B** as the default model. You can use a smaller model to reduce RAM and disk requirements, but this will affect how the platform behaves -- see [Changing the Model](#changing-the-model) for details.

### Automated Setup

Clone the repo and run the setup script. It handles everything -- building containers, waiting for health checks, pulling the AI model, and verifying the install:

```bash
git clone https://github.com/sec-tools/awesomebot.git
cd awesomebot
bash setup.sh
```

The script will:

1. Check that Docker and Docker Compose are installed and running
2. Build and start all three services (ollama, backend, frontend)
3. Wait for all services to pass health checks
4. Pull the default AI model (`qwen2.5:7b`, ~4.7 GB one-time download)
5. Verify the health endpoint and frontend are responding

When it finishes you will see:

```
=== Setup Complete ===

NAME                  STATUS                   PORTS
awesomebot-backend    Up 8 minutes (healthy)   0.0.0.0:8000->8000/tcp
awesomebot-frontend   Up 8 minutes (healthy)   0.0.0.0:3000->3000/tcp
awesomebot-ollama     Up 8 minutes (healthy)   0.0.0.0:11434->11434/tcp

Open http://localhost:3000 in your browser.
Login: admin / Password1
```

Open **http://localhost:3000** and log in:

| Username | Password   |
|----------|------------|
| `admin`  | `Password1` |

You can also create additional non-admin accounts via the signup page. That's it -- you're running.

If you run `bash setup.sh` again while services are already running, it will skip the build, check if the model is downloaded, and verify everything is healthy.

### Manual Setup

If you prefer to run the steps yourself:

```bash
# 1. Build and start
git clone https://github.com/sec-tools/awesomebot.git
cd awesomebot
docker compose up -d --build

# 2. Wait for healthy (all three should show "healthy")
docker compose ps

# 3. Pull the AI model (one-time ~4.7 GB download)
docker exec awesomebot-ollama ollama pull qwen2.5:7b

# 4. Verify
curl -s http://localhost:8000/health
```

Expected health output:

```json
{
    "status": "healthy",
    "services": {
        "api": "running",
        "ollama": "connected",
        "database": "connected",
        "model": "qwen2.5:7b"
    }
}
```

## What Is This

> **Note:** This platform was primarily vibe coded. Features have varying levels of testing and may work fully, partially, or not at all. Treat this as a beta-quality educational platform with no planned maintenance or support.

AwesomeBot is an AI chat application with:

- A **React frontend** served by nginx on port 3000
- A **Python FastAPI backend** on port 8000 with JWT auth, tool execution, and streaming chat
- A **local Ollama LLM** (Qwen 2.5 7B) on port 11434 -- no external API keys
- A **SQLite database** auto-created on first run
- **13 chat tools** that the AI can invoke (math, code execution, file I/O, HTTP requests, product search, conversation history, MCP tools, and more)
- A **product catalog** (AwesomeGear) with 21 items the AI can search
- A **guard rails system** with 10 toggleable prompt defense techniques
- An **admin panel** for managing the system prompt, AI settings, users, and guard rails
- **MCP (Model Context Protocol) server support** with a built-in MCP server and the ability to add custom ones
- **RAG support** -- upload documents for AI-augmented context
- An **API testing page** built into the frontend

The application is designed to look and feel like a real product with lots of bugs for security research and educational purposes.

## Bug Hunting

You can read the code, interact with the chat, the API, the admin panel, and so on.

Think about:

- How does the AI decide what tools to use and what permissions to enforce?
- How does authentication and authorization work?
- How does user input flow through the system?
- What happens when the AI talks to the database?
- What is it not checking/blocking that can lead to bugs?

The value is in the process of finding, understanding, and exploiting the issues in a local test environment to learn.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend   │────▶│   Backend   │────▶│   Ollama    │
│  React/TS    │     │  FastAPI    │     │  LLM Engine │
│  Port 3000   │     │  Port 8000  │     │  Port 11434 │
│  (nginx)     │     │  (uvicorn)  │     │  (qwen2.5)  │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │   SQLite    │
                    │  Database   │
                    └─────────────┘
```

The frontend proxies all `/api/` requests to the backend via nginx. The backend communicates with Ollama for LLM inference. All state is stored in a SQLite database inside a Docker volume.

## Project Structure

```
AwesomeBot/
├── docker-compose.yml          # Orchestrates all three services
├── setup.sh                    # Automated setup (build, pull model, verify)
├── reset.sh                    # Full reset (tear down and rebuild from scratch)
├── SYSTEM_PROMPT.txt # The AI's system prompt
├── backend/
│   ├── Dockerfile
│   ├── main.py                 # FastAPI entry point
│   ├── requirements.txt
│   ├── awesome_mcp_server.py   # Built-in MCP server
│   └── app/
│       ├── api/                # Route handlers (auth, chat, admin, etc.)
│       ├── core/               # Auth, config, database, initialization
│       ├── models/             # SQLAlchemy models
│       ├── services/           # Business logic (chat, products, RAG, etc.)
│       └── tools/              # 13 chat tool plugins
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    └── src/                    # React + TypeScript application
```

## Platform Features

> **Note:** This platform was primarily vibe coded. Individual features have varying levels of testing and may work fully, partially, or not at all. This is a beta-quality educational platform with no planned maintenance or support.

### Admin Panel

*Vibe coded -- may work fully, partially, or not at all.*

Log in as admin to access:

- **System Prompt Editor** -- view and modify the AI's system prompt in real time
- **AI Settings** -- adjust temperature, max tokens, toggle RAG
- **Guard Rails** -- enable or disable 10 prompt defense techniques
- **User Management** -- view and delete users
- **AwesomeGear Toggle** -- enable or disable the product catalog

### Guard Rails

*Vibe coded -- may work fully, partially, or not at all.*

The admin panel provides 10 guard rail techniques that can be independently toggled:

- Delimiter Defense
- Instruction Hierarchy
- Output Encoding Warning
- Sandwich Defense
- XML Tag Defense
- Instruction Repetition
- Role Reminder
- Prompt Signature
- Instruction Isolation
- Meta-Prompt Defense

These have not been tested and may or may not work. However they are meant to highlight and experiment with various prompt protections for chatbot systems.

### Chat Tools

*Vibe coded -- may work fully, partially, or not at all.*

The AI has access to 13 tools that execute automatically based on message patterns. You can list them through the API:

```bash
curl -s http://localhost:3000/api/chat/tools -H "Authorization: Bearer <token>" | python3 -m json.tool
```

### MCP Server

*Vibe coded -- may work fully, partially, or not at all.*

A built-in MCP server provides three tools out of the box (weather, datetime, system updates). You can manage MCP servers from the MCP page in the UI.

### API Documentation

*Vibe coded -- may work fully, partially, or not at all.*

Interactive Swagger docs are available at **http://localhost:8000/docs** with every endpoint documented.

## Configuration

> **Note:** Configuration options are minimally tested. Changes may work fully, partially, or not at all.

### Changing the Model

The platform was developed and tested on **`qwen2.5:7b`**. You can switch to a smaller or larger model, but this will change how the platform works.

Edit `docker-compose.yml` and change `DEFAULT_MODEL`:

```yaml
environment:
  - DEFAULT_MODEL=qwen2.5:3b   # Smaller, faster, less RAM
```

Then pull the new model and restart:

```bash
docker exec awesomebot-ollama ollama pull qwen2.5:3b
docker compose restart backend
```

#### Impact of Using a Different Model

The AI's ability to use tools, follow instructions, and respond to prompts depends heavily on the model. Smaller models are faster and use less RAM but are less capable:

| Model | Size | RAM Needed | Tool Use | Instruction Following | Notes |
|-------|------|------------|----------|----------------------|-------|
| `qwen2.5:7b` | ~4.7 GB | ~6 GB | Good | Good | **Default. Tested.** |
| `qwen2.5:3b` | ~2 GB | ~4 GB | Partial | Moderate | May miss tool triggers or ignore constraints |
| `qwen2.5:1.5b` | ~1 GB | ~3 GB | Weak | Weak | Often fails to invoke tools correctly |
| `qwen2.5:0.5b` | ~500 MB | ~2 GB | Poor | Poor | Chat works but tools are unreliable |

With a smaller model you may see:

- **Tools not triggering** -- the AI may not recognize when to invoke tools like product search, code execution, or MCP tools, or may format tool calls incorrectly
- **Guard rails behaving differently** -- prompt defense techniques rely on the model following system prompt instructions; weaker models may ignore them entirely or follow them too rigidly
- **Prompt injection being easier or harder** -- smaller models are less predictable; some attacks may work more easily because the model ignores restrictions, while others may fail because the model doesn't follow injected instructions either
- **Lower quality responses** -- shorter, less coherent, or off-topic answers
- **Security vulnerabilities still present** -- the code-level bugs (SQL injection, auth issues, MCP command injection, etc.) exist regardless of model choice; only the AI-behavioral attack surface changes

If you just want to explore the platform with lower hardware requirements, `qwen2.5:3b` is a reasonable compromise. For the full experience as tested, use `qwen2.5:7b`.

### GPU Support

If you have an NVIDIA GPU and nvidia-docker installed, uncomment the GPU section in `docker-compose.yml`:

```yaml
devices:
  - driver: nvidia
    count: 1
    capabilities: [gpu]
```

## Stopping and Cleanup

```bash
# Stop all services (data is preserved)
docker compose down

# Stop and delete all data (database, model downloads, volumes)
docker compose down --volumes

# Also remove built images
docker compose down --volumes --rmi all

# Full reset back to fresh state (interactive script -- rebuilds and re-pulls model)
bash reset.sh
```

## Troubleshooting

### "Waiting for Ollama" / backend restarts

The backend waits for Ollama to be healthy before starting. If Ollama is slow to initialize, the backend will retry for up to 60 seconds. Check Ollama logs:

```bash
docker logs awesomebot-ollama
```

### Chat returns errors after first start

You need to pull the model after the first `docker compose up`. Run:

```bash
docker exec awesomebot-ollama ollama pull qwen2.5:7b
```

### Out of memory

The default model (`qwen2.5:7b`) needs ~6 GB RAM. If Docker is constrained, switch to a smaller model -- see [Changing the Model](#changing-the-model) for options and trade-offs. The quick fix:

```yaml
- DEFAULT_MODEL=qwen2.5:3b   # ~2 GB download, needs ~4 GB RAM
```

### Check service status

```bash
docker compose ps                        # Container health
docker logs awesomebot-backend           # Backend logs
curl -s http://localhost:8000/health     # API health
```

## FAQ

### What is MCP, RAG and all of these LLM-related concepts?

There's a ton of great resources online, including videos and blogs to learn about these concepts and related security research.

Attacking AI
https://www.youtube.com/watch?v=uOHRi1JktPE

AI Red Teaming in 2025 and Beyond
https://www.youtube.com/watch?v=nzfPUeB6UjM

Red, Blue, and Purple AI
https://www.youtube.com/watch?v=XHeTn7uWVQM

Prompt Engineer and AI Red Teaming
https://www.youtube.com/watch?v=_BRhRh7mOX0

Building Web Hacking Micro Agents
https://www.youtube.com/watch?v=3y8dyeKmJQI

Augmenting Your Offensiveness With AI for Fun and Job Security
https://www.youtube.com/watch?v=9BCK5-bGRTE

Prompt Injection Methodology for GenAI Application Pentesting - Greet & Repeat Method
https://www.youtube.com/watch?v=e2x5hRJ0FA8

Cyber and Dev #2: MCP
https://zkorman.com/posts/cyberdev-mcp/11

The Arcanum Prompt Injection Taxonomy
https://github.com/Arcanum-Sec/arc_pi_taxonomy/


### Do I need to have AI/ML expertise to play with it?

No. Many of the vulnerabilities are classic web application security issues that happen to be wired through an AI chatbot. If you can find bugs in a normal web app, you can find bugs here.

### Is AwesomeBot actively maintained?

No. It was built as a project for learning about the security of AI platforms with no planned support or maintenance.

### How do I reset the platform?

There's a reset script to tear everything down and rebuild from scratch as if you had just cloned the repo for the first time:

```bash
bash reset.sh
```

The script will:

1. Stop all containers and remove all volumes (database, uploaded files, downloaded models)
2. Remove all built Docker images
3. Rebuild everything from scratch
4. Wait for all services to become healthy
5. Re-pull the AI model

It asks for confirmation before proceeding. The full reset takes a few minutes depending on your machine and network speed (the model re-download is the slowest part).

If you prefer to do it manually:

```bash
docker compose down --volumes --rmi all
docker compose up -d --build
docker exec awesomebot-ollama ollama pull qwen2.5:7b
```

### Can I use a different LLM?

Yes. Any model available through Ollama works. Change `DEFAULT_MODEL` in `docker-compose.yml`, pull the model, and restart. However, the platform was built and tested on `qwen2.5:7b`. Smaller models use less RAM but may not trigger tools correctly, may ignore guard rail instructions, and may behave unpredictably with prompt injection attempts. Code-level vulnerabilities (SQL injection, auth bypass, MCP command injection, etc.) are unaffected by model choice. See [Changing the Model](#changing-the-model) for a detailed comparison.

### Are there any walkthroughs or write-ups available?

Yes. Two companion blog posts cover specific attack categories in detail. See the [Blog Posts & Further Reading](#blog-posts--further-reading) section below. Be aware that reading them will spoil parts of the challenge.

### Can I use this for a CTF or training session?

Yes. That is one of the intended uses. You are free to fork, modify, and use this for workshops, courses, CTF challenges, or self-study under the MIT license.

## Blog Posts & Further Reading

Two companion blog posts walk through real vulnerability research performed against this platform:

### [AwesomeBot Meets Prompt Injection](https://aivr.hashnode.dev/awesomebot-meets-prompt-injection)

Explores prompt injection attack vectors in AwesomeBot. The post covers how the platform's authorization model relies on string matching inside system-role messages, and how that design opens up multiple privilege escalation paths. Topics include conversation memory injection (planting payloads in chat history that are later retrieved as system context), RAG document poisoning, SQL injection as a prompt injection primitive, and techniques for bypassing the guard rails system. If you are interested in how prompt injection works in a realistic application with tools, memory, and role-based access, start here.

### [AwesomeBot Meets MCP](https://aivr.hashnode.dev/awesomebot-meets-mcp)

Examines the security implications of AwesomeBot's Model Context Protocol implementation. The post investigates what happens when users can register arbitrary MCP servers -- including how the platform handles (or fails to handle) command parameters, argument sanitization, and process execution. It covers direct command injection via the MCP server registration API, malicious MCP server payloads disguised as legitimate tool providers, and the broader question of what trust boundaries should exist between an AI platform and its external tool integrations.

## License

MIT License -- see [LICENSE](LICENSE) for details.

---

**This project is for security education and research only. Do not deploy on a public network or use with real user data.**
