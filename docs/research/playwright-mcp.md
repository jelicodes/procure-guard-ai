# Playwright MCP — Research Notes

> Researched against primary sources only (as of 2026-08-15):
> official GitHub repo, official Playwright docs, official npm registry API, and GitHub releases.

## 1. What it is & official status

**Playwright MCP** is a Model Context Protocol (MCP) server that provides browser automation
capabilities using Playwright. It enables LLMs to interact with web pages through **structured
accessibility snapshots**, bypassing the need for screenshots or visually-tuned (vision) models.
([source: github.com/microsoft/playwright-mcp README](https://github.com/microsoft/playwright-mcp))
([source: playwright.dev/mcp/introduction](https://playwright.dev/mcp/introduction))

- **Official Microsoft project.** npm package `@playwright/mcp`, author `Microsoft Corporation`,
  license `Apache-2.0`, published from GitHub Actions with provenance attestation.
  ([source: registry.npmjs.org/@playwright/mcp/latest](https://registry.npmjs.org/@playwright/mcp/latest))
- **Listed in the official MCP ecosystem.** Since v0.0.73 (May 1, 2026) it is published to the
  **official MCP Registry** (`registry.modelcontextprotocol.io`) on every release; the registry
  entry is mirrored at `github.com/mcp/microsoft/playwright-mcp`.
  ([source: v0.0.73 release notes](https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.73))
  ([source: MCP Registry GitHub entry](https://github.com/mcp/microsoft/playwright-mcp))
- MCP server name/ID: `io.github.microsoft/playwright-mcp`.
  ([source: npm registry API](https://registry.npmjs.org/@playwright/mcp/latest))
- The Model Context Protocol spec itself lives at [modelcontextprotocol.io](https://modelcontextprotocol.io).

**Problem it solves:** LLMs can drive a real browser deterministically — read the accessibility
tree (~200–400 tokens/snapshot vs thousands for DOM/screenshots), get stable element `ref`s, and
act on them — without vision models. It supports Chrome/Chromium, Firefox, WebKit, and Edge.
([source: playwright.dev/mcp/introduction](https://playwright.dev/mcp/introduction))

> Note: the README now steers heavy **coding agents** toward the separate
> [Playwright CLI + Skills](https://github.com/microsoft/playwright-cli) (lower token cost), and
> keeps MCP for specialized agentic loops (exploratory automation, self-healing tests, long-running
> autonomous workflows). ([source: README](https://github.com/microsoft/playwright-mcp))

## 2. Architecture & transports

- **Default transport: stdio.** The MCP client spawns the server as a subprocess
  (`npx @playwright/mcp@latest`) and talks over stdin/stdout.
  ([source: README "Getting started"](https://github.com/microsoft/playwright-mcp))
- **HTTP transport (SSE/Streamable):** run the server standalone with `--port` and point the client
  at `url: http://localhost:PORT/mcp`. Host defaults to `localhost`; use `--host 0.0.0.0` to bind
  all interfaces. Useful when running headed browsers from IDE worker processes / headless machines.
  ([source: README "Standalone MCP server"](https://github.com/microsoft/playwright-mcp))
  ([source: playwright.dev/mcp/configuration/options](https://playwright.dev/mcp/configuration/options))
- **Programmatic embedding:** `createConnection()` from `@playwright/mcp` + an MCP SDK transport
  (e.g. `SSEServerTransport`) lets you host the server inside your own Node process.
  ([source: README "Programmatic usage"](https://github.com/microsoft/playwright-mcp))
- **Browser connection:** the server launches a persistent-context browser locally by default, but
  can also attach to an existing browser via CDP (`--cdp-endpoint`), a Playwright server endpoint
  (`--endpoint` / config `remoteEndpoint`), or the official browser extension (`--extension`).
  ([source: README options table](https://github.com/microsoft/playwright-mcp))

## 3. Installation & launch methods

Node requirement: npm `engines: node >=18`; the official docs recommend **Node 20+**.
([source: npm registry API](https://registry.npmjs.org/@playwright/mcp/latest))
([source: playwright.dev/mcp/installation](https://playwright.dev/mcp/installation))
Browsers are **downloaded automatically on first use**; use `PLAYWRIGHT_MCP_EXECUTABLE_PATH` or
`--executable-path` to point at a specific binary.
([source: playwright.dev/mcp/installation](https://playwright.dev/mcp/installation))

| Method | Command | Notes |
|---|---|---|
| **npx (recommended)** | `npx @playwright/mcp@latest` | No global install; browser auto-downloads. Standard config for every client. |
| **Direct node** | `npm i -D @playwright/mcp`, then `npx playwright-mcp` (bin: `playwright-mcp` → `cli.js`) | For pinned/local installs. ([source: npm registry API `bin`](https://registry.npmjs.org/@playwright/mcp/latest)) |
| **Docker** | `docker run -i --rm --init --pull=always mcr.microsoft.com/playwright/mcp` | Image `mcr.microsoft.com/playwright/mcp`. **Headless Chromium only.** ([source: README Docker](https://github.com/microsoft/playwright-mcp)) |
| **Standalone HTTP** | `npx @playwright/mcp@latest --port 8931` | Client uses `"url": "http://localhost:8931/mcp"`. |
| **Programmatic** | `import { createConnection } from '@playwright/mcp'` | Embed in your own Node server. |

([source: README](https://github.com/microsoft/playwright-mcp))
([source: playwright.dev/mcp/installation](https://playwright.dev/mcp/installation))

> **pip / uvx:** there is **no official uvx/pip distribution** of this server. `@playwright/mcp`
> is a Node package (author Microsoft, `engines: >=18`); the only official install paths are npx,
> npm/direct node, Docker, and programmatic. ([source: npm registry API](https://registry.npmjs.org/@playwright/mcp/latest))

## 4. Configuration options (CLI flags, defaults, env vars)

Every CLI option has a `PLAYWRIGHT_MCP_<NAME>` environment-variable equivalent. Full table:
([source: README options table](https://github.com/microsoft/playwright-mcp))

| Flag | Description | Default |
|---|---|---|
| `--browser <browser>` | Browser or Chrome channel: `chrome`, `firefox`, `webkit`, `msedge` (also `moz-firefox` BiDi since v0.0.76) | chromium |
| `--headless` | Run headless | **headed by default** |
| `--isolated` | Keep profile in memory; do not save to disk | off (persistent profile) |
| `--viewport-size <size>` | e.g. `"1280x720"` | Playwright default |
| `--device <device>` | Device emulation, e.g. `"iPhone 15"` | – |
| `--mobile` | Generic mobile emulation (Pixel 10 Chromium / iPhone 17 WebKit); cannot combine with `--device` | – |
| `--user-data-dir <path>` | Persistent profile directory (else temp dir) | temp dir / per-workspace cache |
| `--storage-state <path>` | Seed isolated sessions with cookies+localStorage file | – |
| `--user-agent <ua>` | Override UA string | – |
| `--executable-path <path>` | Path to browser executable | – |
| `--cdp-endpoint <url>` | Attach to existing Chrome/Edge via CDP | – |
| `--cdp-header <h...>` / `--cdp-timeout <ms>` | CDP headers / connect timeout | 30000ms |
| `--endpoint <url>` | Connect to an existing Playwright server | – |
| `--extension` | Connect to running Edge/Chrome via official browser extension | – |
| `--caps <caps>` | Opt-in tool groups: `vision`, `pdf`, `devtools`, `network`, `storage`, `testing`, `config` | core only |
| `--allowed-origins <o...>` | Trusted origins (semicolon-separated); **not a security boundary**, doesn't affect redirects | allow all |
| `--blocked-origins <o...>` | Origins to block (blocklist wins) | – |
| `--allowed-hosts <h...>` | Hosts server may serve from (DNS-rebinding guard) | bound host |
| `--timeout-action <ms>` | Per-action timeout | 5000ms |
| `--timeout-navigation <ms>` | Navigation timeout | 60000ms |
| `--timeout-settle <ms>` | Wait after each action for work to settle | 500ms |
| `--test-id-attribute <attr>` | Attribute used for test ids | `data-testid` |
| `--snapshot-mode <mode>` | `full` or `none` | `full` |
| `--snapshot-boxes` | Include `[box=x,y,width,height]` in snapshots | off |
| `--console-level <level>` | `error`/`warning`/`info`/`debug` | `info` |
| `--codegen <lang>` | `typescript`/`python`/`java`/`csharp`/`none` | `typescript` |
| `--image-responses <mode>` | `allow` or `omit` image responses | `allow` |
| `--port <port>` / `--host <host>` | HTTP transport bind | port none / `localhost` |
| `--shared-browser-context` | Share one context across HTTP clients | off |
| `--save-session` / `--output-dir <path>` / `--output-max-size <bytes>` | Session/tool output persistence | – |
| `--proxy-server <proxy>` / `--proxy-bypass <bypass>` | Proxy config | – |
| `--no-sandbox` / `--sandbox` | Toggle Chromium sandbox | sandbox on (default) |
| `--ignore-https-errors` | Ignore HTTPS errors | off |
| `--grant-permissions <p...>` | e.g. `geolocation`, `clipboard-read`, `clipboard-write` | – |
| `--init-page <path>` / `--init-script <path>` | Per-page setup TS file / init JS script | – |
| `--secrets <path>` | dotenv file; redacts matching text from tool output (**convenience, not security**) | – |
| `--block-service-workers` | Block service workers | off |
| `--allow-unrestricted-file-access` | Allow file access outside workspace roots + `file://` URLs | restricted |
| `--config <path>` | JSON config file | – |

Advanced settings are available as a JSON config file (`--config path/to/config.json`): `browser`
(`browserName`, `isolated`, `userDataDir`, `launchOptions`, `contextOptions`, `cdpEndpoint`,
`remoteEndpoint`, `initPage`, `initScript`), `server` (`port`, `host`, `allowedHosts`),
`capabilities`, `timeouts` (`action`, `navigation`, `expect`, `settle`), `network`
(`allowedOrigins`, `blockedOrigins`), `snapshot`, `secrets`, `outputDir`, `testIdAttribute`, etc.
([source: README config schema](https://github.com/microsoft/playwright-mcp))

## 5. Tools exposed by the server

Complete generated list from the README (source of truth, generated from code):
([source: README "Tools" section](https://github.com/microsoft/playwright-mcp))

**Core automation (always on):** `browser_click`, `browser_close`, `browser_console_messages`
(read-only), `browser_drag`, `browser_drop`, `browser_evaluate`, `browser_file_upload`,
`browser_fill_form`, `browser_find` (search snapshot cheaply), `browser_handle_dialog`,
`browser_hover`, `browser_navigate`, `browser_navigate_back`, `browser_network_request`,
`browser_network_requests`, `browser_press_key`, `browser_resize`, `browser_run_code_unsafe`
(**RCE-equivalent, use with caution**), `browser_select_option`, `browser_snapshot` (accessibility
snapshot — the primary way to "see" the page), `browser_take_screenshot`, `browser_type`,
`browser_wait_for`.

**Tab management:** `browser_tabs`.

**Capability groups (opt-in via `--caps=`):**
- `config` → `browser_get_config`
- `network` → `browser_network_state_set`, `browser_route`, `browser_route_list`, `browser_unroute`
- `storage` → cookie (`browser_cookie_*`), localStorage (`browser_localstorage_*`),
  sessionStorage (`browser_sessionstorage_*`), `browser_storage_state`, `browser_set_storage_state`
- `devtools` → `browser_annotate`, `browser_highlight`, `browser_hide_highlight`,
  `browser_start_tracing`, `browser_stop_tracing`, `browser_start_video`, `browser_stop_video`,
  `browser_video_chapter`, `browser_video_show_actions`, `browser_video_hide_actions`, `browser_resume`
- `vision` (coordinate-based) → `browser_mouse_click_xy`, `browser_mouse_down/up/move_xy`,
  `browser_mouse_drag_xy`, `browser_mouse_wheel`
- `pdf` → `browser_pdf_save`
- `testing` → `browser_generate_locator`, `browser_verify_element_visible`,
  `browser_verify_list_visible`, `browser_verify_text_visible`, `browser_verify_value`

The docs intro additionally lists `browser_navigate_forward`, `browser_reload`, `browser_check`,
`browser_uncheck` as core tools (docs may drift slightly from README).
([source: playwright.dev/mcp/introduction](https://playwright.dev/mcp/introduction))

> **Resources:** the current server exposes its functionality as **tools**, not resources. The
> README contains no resource definitions; `browser_console_messages` (historically a resource) is
> now a read-only tool. Verify resources on a live session if needed — nothing is documented
> currently. ([source: README](https://github.com/microsoft/playwright-mcp))

## 6. Authentication, headless behavior & best practices

- **Headed by default** so you can watch; pass `--headless` to hide the window.
  ([source: README](https://github.com/microsoft/playwright-mcp))
  ([source: playwright.dev/mcp/installation](https://playwright.dev/mcp/installation))
- **Persistent profile by default** — the server runs like a normal browser and keeps login state
  on disk; delete the profile dir to clear state. Profile locations (override with `--user-data-dir`):
  Windows `%USERPROFILE%\AppData\Local\ms-playwright\mcp-{channel}-{workspace-hash}`,
  macOS `~/Library/Caches/ms-playwright/mcp-{channel}-{workspace-hash}`,
  Linux `~/.cache/ms-playwright/mcp-{channel}-{workspace-hash}`. The `{workspace-hash}` derives from
  the client's workspace root, so different projects get separate profiles.
  ([source: README "User profile"](https://github.com/microsoft/playwright-mcp))
- **Isolated mode** (`--isolated`) keeps the profile in memory; state is lost when the browser
  closes. Seed it with `--storage-state=path/to/storage.json` or `contextOptions`.
  ([source: README](https://github.com/microsoft/playwright-mcp))
- **Recommended auth flow** (needs `--caps=storage`): log in once →
  `browser_storage_state` to save `auth-state.json` → next session `browser_set_storage_state`
  (or `--storage-state` at startup) → navigate straight to the dashboard.
  ([source: playwright.dev/mcp/tools/storage](https://playwright.dev/mcp/tools/storage))
- **Browser extension** lets the agent drive your *real, logged-in* browser (Edge/Chrome) with
  `--extension`; install the extension from
  [microsoft/playwright › packages/extension](https://github.com/microsoft/playwright/tree/main/packages/extension).
  ([source: README](https://github.com/microsoft/playwright-mcp))
- **Gotcha:** a persistent profile can only be used by one browser instance at a time — concurrent
  MCP clients sharing a workspace will conflict. Run additional clients with `--isolated` or a
  distinct `--user-data-dir`. ([source: README](https://github.com/microsoft/playwright-mcp))

## 7. Client configuration examples

**Standard config (Claude Desktop, VS Code, Cursor, Windsurf, Goose, etc.):**
([source: README](https://github.com/microsoft/playwright-mcp))

```jsonc
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

**Claude Desktop:** follow the standard MCP install guide — use the standard config above.
([source: README Claude Desktop section](https://github.com/microsoft/playwright-mcp))

**VS Code:** standard config, or CLI: `code --add-mcp '{"name":"playwright","command":"npx","args":["@playwright/mcp@latest"]}'`.
([source: README VS Code section](https://github.com/microsoft/playwright-mcp))

**opencode global install** (`~/.config/opencode/opencode.json`) — as documented in the official
README's opencode section:
([source: README opencode section](https://github.com/microsoft/playwright-mcp))

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "playwright": {
      "type": "local",
      "command": ["npx", "@playwright/mcp@latest"],
      "enabled": true
    }
  }
}
```

## 8. Gotchas & advanced topics

- **Docker image** `mcr.microsoft.com/playwright/mcp` only supports **headless Chromium**. For a
  long-lived service: `docker run -d -i --rm --init --pull=always --entrypoint node --name playwright -p 8931:8931 mcr.microsoft.com/playwright/mcp /app/cli.js --headless --browser chromium --no-sandbox --port 8931 --host 0.0.0.0`.
  ([source: README Docker](https://github.com/microsoft/playwright-mcp))
- **Remote/CDP:** `--cdp-endpoint <url>` attaches to a running Chrome/Edge; `--endpoint` /
  `remoteEndpoint` connects to an existing Playwright server (WebSocket URL or `ConnectOptions`
  object); `--extension` uses the browser extension. v0.0.76+ auto-reconnects after a remote
  disconnect. ([source: README + v0.0.76 notes](https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.76))
- **Security:** "Playwright MCP is **not** a security boundary." `browser_run_code_unsafe`
  executes arbitrary JS in the server process (RCE-equivalent); `--secrets` redaction is a
  convenience, not protection; `--allowed-origins` doesn't affect redirects.
  ([source: README Security section](https://github.com/microsoft/playwright-mcp))
- **Environment variables:** every CLI flag has a `PLAYWRIGHT_MCP_*` env var (e.g.
  `PLAYWRIGHT_MCP_HEADLESS`, `PLAYWRIGHT_MCP_BROWSER`, `PLAYWRIGHT_MCP_ALLOWED_ORIGINS`,
  `PLAYWRIGHT_MCP_CAPS`, `PLAYWRIGHT_MCP_EXECUTABLE_PATH`). Env vars and a `--config` JSON file can
  be combined; CLI args win. ([source: README options table](https://github.com/microsoft/playwright-mcp))
- **Mobile/device:** `--mobile` emulates a generic mobile device (Pixel 10 for Chromium, iPhone 17
  for WebKit), lighter pages save tokens; mutually exclusive with `--device`.
  ([source: v0.0.78 release notes](https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.78))
- **Sandbox:** Chromium sandbox is enabled by default for the default browser; use `--no-sandbox`
  in containers/CI. ([source: v0.0.78 release notes](https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.78))

## 9. Version / update status (as of 2026-08-15)

- **Latest release: v0.0.79** (released **Aug 6, 2026**), depends on
  `playwright 1.63.0-alpha-2026-08-05`. Highlight: `browser_take_screenshot` WebP/type option,
  `--codegen` now supports python/java/csharp, new `--timeout-settle` flag, `--snapshot-boxes`.
  ([source: GitHub releases](https://github.com/microsoft/playwright-mcp/releases))
  ([source: npm registry API](https://registry.npmjs.org/@playwright/mcp/latest))
- Release cadence is roughly monthly at a **0.0.x version** (0.0.70 Apr 1 → 0.0.79 Aug 6, 2026):
  v0.0.78 (Jul 9), v0.0.77 (Jun 29), v0.0.76 (Jun 10), v0.0.75 (May 7), v0.0.74 (May 6),
  v0.0.73 (May 1), v0.0.72 (Apr 30), v0.0.71 (Apr 27). ([source: GitHub releases](https://github.com/microsoft/playwright-mcp/releases))
- The server is published to the official **MCP Registry on every release** (since v0.0.73).
  ([source: v0.0.73 release notes](https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.73))
- **Recommendation:** pin `@latest` (or bump regularly) — 0.0.x moves fast; the README, docs, and
  config schema all target `@latest`.

## Key sources (primary)

- Official repo / README: https://github.com/microsoft/playwright-mcp
- Official docs: https://playwright.dev/mcp/introduction · https://playwright.dev/mcp/installation ·
  https://playwright.dev/mcp/configuration/options · https://playwright.dev/mcp/tools/storage ·
  https://playwright.dev/mcp/capabilities
- npm registry API (authoritative version/metadata): https://registry.npmjs.org/@playwright/mcp/latest
- GitHub releases: https://github.com/microsoft/playwright-mcp/releases
- MCP Registry entry: https://github.com/mcp/microsoft/playwright-mcp
- MCP Registry base: https://registry.modelcontextprotocol.io