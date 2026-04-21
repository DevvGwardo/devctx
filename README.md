# devctx

**One command. Full project context. For AI agents.**

Stop your agents from burning tokens on discovery. `devctx` gives Claude Code, Hermes, and any AI agent a structured snapshot of your entire dev environment in a single call.

```bash
$ devctx
```

```json
{
  "services": {
    "hermes-gateway": { "port": 8642, "status": "listening", "pid": 4821 },
    "postgres-alt": { "port": 5433, "status": "listening" },
    "redis/dragonfly": { "port": 6379, "status": "listening" }
  },
  "git": {
    "hermes-agent": { "branch": "improve/cycle-13", "dirty": false, "ahead": 2 },
    "my-app": { "branch": "main", "dirty": true, "changed_files": 3 }
  },
  "deploy": {
    "railway": { "projects": [{ "name": "my-api", "id": "abc123" }] }
  },
  "env": {
    "set": ["ANTHROPIC_API_KEY", "GITHUB_TOKEN"],
    "missing": ["OPENAI_API_KEY"]
  },
  "hints": [
    "hermes-agent has 2 unpushed commit(s) on improve/cycle-13",
    "my-app has 3 uncommitted change(s)",
    "missing env vars: OPENAI_API_KEY"
  ]
}
```

---

## Why

AI agents waste tokens discovering your environment through trial and error — checking ports, running `git status` on every repo, probing for services, retrying when something's down. Each discovery call re-sends the full conversation history.

**devctx eliminates the discovery phase entirely.**

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#6366f1', 'primaryTextColor': '#f8fafc', 'lineColor': '#818cf8', 'secondaryColor': '#1e1b4b', 'tertiaryColor': '#312e81', 'background': '#0f172a', 'mainBkg': '#1e1b4b', 'nodeBorder': '#818cf8', 'clusterBkg': '#1e1b4b', 'edgeLabelBackground': '#1e1b4b', 'fontFamily': 'JetBrains Mono, monospace'}}}%%

flowchart TB
    subgraph BEFORE["<b>Without devctx</b> — N calls to orient"]
        direction TB
        A1([AI Agent]):::agent
        A1 -->|"1. git status"| B1[git]:::tool
        A1 -->|"2. docker ps"| B2[docker]:::tool
        A1 -->|"3. lsof ports"| B3[ports]:::tool
        A1 -->|"4. railway status"| B4[railway]:::tool
        A1 -->|"5. check envs"| B5[env vars]:::tool
        A1 -->|"6. more discovery..."| B6["...repeat"]:::tool

        B1 -.->|"partial"| A1
        B2 -.->|"partial"| A1
        B3 -.->|"partial"| A1
        B4 -.->|"partial"| A1
        B5 -.->|"partial"| A1
        B6 -.->|"partial"| A1
    end

    subgraph AFTER["<b>With devctx</b> — 1 call, full picture"]
        direction TB
        A2([AI Agent]):::agent
        A2 ==>|"devctx"| CTX{devctx}:::devctx

        CTX --> C1[Services]:::collector
        CTX --> C2[Git State]:::collector
        CTX --> C3[Deployments]:::collector
        CTX --> C4[Env Health]:::collector
        CTX --> C5["Hints"]:::collector

        C1 --> OUT[/"Structured JSON\n~500 tokens"/]:::output
        C2 --> OUT
        C3 --> OUT
        C4 --> OUT
        C5 --> OUT
        OUT ==> A2
    end

    classDef agent fill:#6366f1,stroke:#818cf8,color:#f8fafc,stroke-width:2px
    classDef tool fill:#1e293b,stroke:#475569,color:#94a3b8,stroke-width:1px
    classDef devctx fill:#6366f1,stroke:#a5b4fc,color:#f8fafc,stroke-width:3px
    classDef collector fill:#312e81,stroke:#6366f1,color:#c7d2fe,stroke-width:1px
    classDef output fill:#065f46,stroke:#34d399,color:#d1fae5,stroke-width:2px

    style BEFORE fill:#0f172a,stroke:#ef4444,color:#fca5a5,stroke-width:2px
    style AFTER fill:#0f172a,stroke:#22c55e,color:#86efac,stroke-width:2px
```

### The math

| | Without devctx | With devctx |
|---|---|---|
| **Tool calls to orient** | 5-15 | 1 |
| **Tokens on discovery** | 2,000-8,000+ | ~500 |
| **Retry loops from missing context** | Common | Eliminated |
| **Works across agents** | Manual per-agent | Universal |

---

## Install

```bash
pip install devctx
```

Or install from source:

```bash
git clone https://github.com/DevvGwardo/devctx.git
cd devctx
pip install .
```

---

## Usage

### CLI

```bash
# Full snapshot (default)
devctx

# Specific sections
devctx --services          # Running services & ports
devctx --git               # Git state across repos
devctx --deploy            # Railway, DigitalOcean status
devctx --env               # Environment variable health
devctx --hints             # Agent-friendly hints only

# Options
devctx --scan-dir ~/projects --scan-dir ~/work   # Custom scan directories
devctx --check-env MY_CUSTOM_VAR                  # Check additional env vars
devctx --compact                                  # Minified JSON output
```

### MCP Server (for Hermes, Claude Code, etc.)

`devctx` ships with a built-in MCP server so any MCP-compatible agent can call it as a tool.

**Add to Claude Code:**

```bash
claude mcp add devctx -- devctx-mcp
```

**Add to Hermes (`~/.hermes/config.yaml`):**

```yaml
mcp_servers:
  devctx:
    command: devctx-mcp
```

The MCP server exposes a single tool — `get_dev_context` — that returns the same structured JSON as the CLI.

**Note:** MCP subprocesses don't inherit interactive-shell environment variables. To ensure API keys and other secrets appear in the `env` section, put your exports in `~/.zshenv` (not `~/.zshrc`), or on macOS use `launchctl setenv VAR value` to persist them across login and non-login shells.

### In agent prompts

Add to your `CLAUDE.md` or agent system prompt:

```
At the start of every task, run `devctx` to understand the current environment.
Use the `hints` field to inform your approach before writing any code.
```

---

## Architecture

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#6366f1', 'primaryTextColor': '#f8fafc', 'lineColor': '#818cf8', 'secondaryColor': '#1e1b4b', 'tertiaryColor': '#312e81', 'background': '#0f172a', 'mainBkg': '#1e1b4b', 'nodeBorder': '#818cf8', 'fontFamily': 'JetBrains Mono, monospace'}}}%%

flowchart LR
    CLI["devctx CLI"]:::entry
    MCP["devctx-mcp\n(stdio server)"]:::entry

    CLI --> SNAP["snapshot()"]:::core
    MCP --> SNAP

    SNAP --> S["services\ncollector"]:::mod
    SNAP --> G["git\ncollector"]:::mod
    SNAP --> D["deploy\ncollector"]:::mod
    SNAP --> E["env\ncollector"]:::mod
    SNAP --> H["hints\ngenerator"]:::mod

    S -->|"socket scan\nlsof\ndocker ps"| SYS["System"]:::ext
    G -->|"git CLI"| SYS
    D -->|"railway CLI\ndoctl CLI"| SYS
    E -->|"os.environ"| SYS

    S --> H
    G --> H
    D --> H
    E --> H

    classDef entry fill:#6366f1,stroke:#818cf8,color:#f8fafc,stroke-width:2px
    classDef core fill:#312e81,stroke:#6366f1,color:#c7d2fe,stroke-width:2px
    classDef mod fill:#1e293b,stroke:#475569,color:#94a3b8,stroke-width:1px
    classDef ext fill:#065f46,stroke:#34d399,color:#d1fae5,stroke-width:1px
```

### Collectors

| Collector | What it checks | How |
|---|---|---|
| **services** | Running services on known ports, Docker containers | Socket probing, `lsof`, `docker ps` |
| **git** | Branch, dirty state, ahead/behind, last commit | `git` CLI across scanned directories |
| **deploy** | Railway projects, DigitalOcean droplets | Config files + CLI tools |
| **env** | Presence of expected environment variables | `os.environ` (values never exposed) |
| **hints** | Agent-actionable insights from all of the above | Aggregation + heuristics |

### Adding collectors

Drop a new file in `devctx/collectors/`, implement a `collect_*()` function that returns a dict, and wire it into `cli.py:snapshot()`. That's it.

---

## Principles

Inspired by [InsForge's context engineering approach](https://github.com/InsForge/InsForge):

1. **One call, full picture** — No sequential discovery. The agent gets everything it needs in ~500 tokens.
2. **Structured output** — JSON that agents can parse, not free text that needs interpretation.
3. **Hints, not just data** — The `hints` field tells the agent what to *do*, not just what *is*.
4. **Security by default** — Environment variables report presence only, never values. No secrets in output.
5. **Agent-agnostic** — Works with Claude Code, Hermes, any MCP client, or plain `bash`.

---

## License

MIT
