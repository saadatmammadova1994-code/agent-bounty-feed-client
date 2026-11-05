# Agent Bounty Feed — Free MCP CLI for AI agents

A **read-only, zero-dependency** Python 3.10+ client that calls the free [Agent Bounty Feed](https://github.com/dailydollar-bot/agent-bounty-feed)'s **actual MCP server**, using JSON-RPC 2.0 over Streamable HTTP. Finds paid work, filters tasks with costly/KYC prerequisites, and supports gap-free polling. No API key, subscription, or wallet needed to discover work.

**Upstream endpoint:** `https://agent-bounty-feed.dailydollar.workers.dev/mcp`

## Quickstart (< 5 minutes)

```sh
python3 mcp_client.py stats
python3 mcp_client.py tools
python3 mcp_client.py list --limit 5 --min-usd 1
```

No `pip install` step. The program sends an MCP `initialize` request and then `tools/call` requests to the free server. `list` calls `list_bounties` with the official `exclude_requires` filter for `kyc,stake,bond,purchase,human_only`, sorts by newly seen items, and checks each returned item again.

For AI pipeline integrations:

```sh
python3 mcp_client.py list --limit 10 --json
python3 mcp_client.py new --since 2026-11-01T00:00:00Z --limit 50 --json
python3 mcp_client.py get --id 'direct:example' --json  # Replace with a real ID returned by list
```

`new` uses the MCP `get_new_bounties` tool and follows the server's `next_since` **and** `next_after_id` to avoid missing ties across pages. The final `next_since` is printed so a future cron poll can resume. `get` looks up a record by the ID found using `list`.

### Example output format (illustrative only)

```text
MCP: https://agent-bounty-feed.dailydollar.workers.dev/mcp
Found 2 filtered bounty entries. Listings are NOT payment guarantees.
$50 [direct] Example: dataset validation
  https://example.com/example-one
$5 [taskmarket] Example: API smoke test
  https://example.com/example-two
```

The above entries are **not real current bounty offers**. The real CLI output is fetched from the upstream MCP server at runtime. The CLI uses no secrets and never signs or spends money.

## Tests

```sh
python3 -m unittest discover -v
```

The suite tests MCP `initialize`, `tools/call`, structured-data and text fallback, error handling, ID validation, network restrictions, client-side filters, and cursor pagination. Tests use simulated responses to avoid relying on a live network. Upstream live end-to-end execution is not claimed: the build environment could not resolve external DNS.

## Protocol verification and security

The MCP endpoint and four tool names were confirmed by reading upstream [paid-worker/mcp.js](https://github.com/dailydollar-bot/agent-bounty-feed/blob/main/paid-worker/mcp.js) on 2026-11-05; the server explicitly implements `initialize`, `tools/list`, `tools/call`, and JSON responses. Supports `list_bounties`, `get_new_bounties`, `get_bounty`, and `get_feed_stats`. All requests use HTTPS and read-only tools. The client does not handle the paid x402 endpoint; trust-layer evidence remains paywalled and should be checked on the source board when deciding to apply.

**Payment caveat:** Listed rewards are opportunities, not earned funds. Always verify the original task, country eligibility, deadline, availability, escrow, and deliverable acceptance before doing work. This code does not apply for bounties or submit Taskmarket transactions.

## Bounty context

Created in response to [dailydollar-bot/agent-bounty-feed issue #3](https://github.com/dailydollar-bot/agent-bounty-feed/issues/3), which accepts a public GitHub repo containing a working MCP client with README and sample output. A valid *reward* submission also requires an issue comment **and** a wallet-signed submission on the escrowed Taskmarket task. Publishing a repository alone is not a payment claim.

MIT License. AI-assisted engineering; human account holder responsible for publication, contracts and any wallet operations.
