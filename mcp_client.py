#!/usr/bin/env python3
"""Read-only, zero-dependency Agent Bounty Feed MCP client (Python 3.10+)."""
import argparse
import json
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://agent-bounty-feed.dailydollar.workers.dev/mcp"
PROTOCOL = "2025-06-18"
EXCLUDE = "kyc,stake,bond,purchase,human_only"

class MCPError(Exception):
    pass

class Client:
    def __init__(self, endpoint=ENDPOINT, opener=None):
        if not endpoint.startswith("https://"):
            raise ValueError("MCP endpoint must use HTTPS")
        self.endpoint = endpoint
        self.opener = opener or urllib.request.urlopen
        self.request_id = 0

    def rpc(self, method, params=None):
        self.request_id += 1
        payload = {"jsonrpc": "2.0", "id": self.request_id, "method": method}
        if params is not None:
            payload["params"] = params
        req = urllib.request.Request(
            self.endpoint, data=json.dumps(payload).encode("utf-8"),
            headers={"content-type": "application/json",
                     "accept": "application/json, text/event-stream",
                     "mcp-protocol-version": PROTOCOL,
                     "user-agent": "ABF-Python-MCP-Client/1.0"},
            method="POST")
        try:
            with self.opener(req, timeout=15) as response:
                kind = response.headers.get("Content-Type", "application/json")
                body = response.read(2_000_000).decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise MCPError("Network request failed: " + str(exc)) from exc
        if "text/event-stream" in kind:
            reply = None
            for line in body.splitlines():
                if line.startswith("data: "):
                    try:
                        event = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    if isinstance(event, dict) and event.get("id") == self.request_id:
                        reply = event
                        break
            if reply is None:
                raise MCPError("No matching JSON-RPC response in stream")
        else:
            try:
                reply = json.loads(body)
            except json.JSONDecodeError as exc:
                raise MCPError("Invalid JSON-RPC response") from exc
        if not isinstance(reply, dict) or reply.get("jsonrpc") != "2.0" or reply.get("id") != self.request_id:
            raise MCPError("Invalid JSON-RPC envelope or response ID")
        if "error" in reply:
            raise MCPError("JSON-RPC error: " + str(reply["error"]))
        return reply.get("result", {})

    def initialize(self):
        result = self.rpc("initialize", {
            "protocolVersion": PROTOCOL, "capabilities": {},
            "clientInfo": {"name": "abf-python-client", "version": "1.0.0"}
        })
        if result.get("serverInfo", {}).get("name") != "agent-bounty-feed":
            raise MCPError("Unexpected server identity")
        return result

    def tool(self, name, arguments=None):
        result = self.rpc("tools/call", {"name": name, "arguments": arguments or {}})
        if result.get("isError"):
            messages = [x.get("text", "") for x in result.get("content", [])
                        if x.get("type") == "text"]
            raise MCPError("; ".join(messages) or "MCP tool failed")
        if isinstance(result.get("structuredContent"), dict):
            return result["structuredContent"]
        for part in result.get("content", []):
            if part.get("type") == "text":
                try:
                    parsed = json.loads(part.get("text", ""))
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    return parsed
        raise MCPError("MCP tool returned no structured JSON")

def filter_items(items, min_usd=1):
    output = []
    denied = set(EXCLUDE.split(","))
    for item in items:
        if not isinstance(item, dict) or item.get("kind", "bounty") != "bounty":
            continue
        if denied.intersection(item.get("requires") or []):
            continue
        amount = item.get("est_usd")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < min_usd:
            continue
        if item.get("slots_left") == 0 or item.get("stale") or (item.get("verified") or {}).get("degraded"):
            continue
        if not isinstance(item.get("url"), str) or not item["url"].startswith("https://"):
            continue
        output.append(item)
    return output

def new_pages(client, since, limit=20):
    """Honor both timestamp and ID cursor so equal timestamps are not skipped."""
    after_id = None
    while True:
        args = {"since": since, "limit": limit, "exclude_requires": EXCLUDE, "min_usd": 1}
        if after_id:
            args["after_id"] = after_id
        page = client.tool("get_new_bounties", args)
        yield page
        if not page.get("has_more"):
            return
        new_since, new_id = page.get("next_since"), page.get("next_after_id")
        if not new_since or not new_id or (new_since, new_id) == (since, after_id):
            raise MCPError("Invalid pagination cursor")
        since, after_id = new_since, new_id

def main(argv=None):
    parser = argparse.ArgumentParser(description="Free Agent Bounty Feed MCP client")
    parser.add_argument("command", choices=["list", "stats", "tools", "new", "get"])
    parser.add_argument("--min-usd", type=float, default=1)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--since")
    parser.add_argument("--id")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--endpoint", default=ENDPOINT)
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 100 or args.min_usd < 0:
        parser.error("--limit must be 1..100 and --min-usd >= 0")
    if args.command == "new" and not args.since:
        parser.error("new requires --since")
    if args.command == "get" and not args.id:
        parser.error("get requires --id")
    try:
        c = Client(args.endpoint)
        c.initialize()
        if args.command == "stats":
            result = c.tool("get_feed_stats")
        elif args.command == "tools":
            result = c.rpc("tools/list")
        elif args.command == "get":
            result = c.tool("get_bounty", {"id": args.id})
        elif args.command == "list":
            result = c.tool("list_bounties", {
                "limit": args.limit, "min_usd": args.min_usd,
                "exclude_requires": EXCLUDE, "sort": "first_seen"})
            result["items"] = filter_items(result.get("items", []), args.min_usd)
        else:
            pages = list(new_pages(c, args.since, args.limit))
            result = {"pages": len(pages),
                      "items": filter_items(
                          [item for page in pages for item in page.get("items", [])], args.min_usd),
                      "next_since": pages[-1].get("next_since")}
        if args.json or args.command in ("stats", "tools", "get"):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("MCP:", args.endpoint)
            print("Filtered bounties:", len(result["items"]), "(not payment guarantees)")
            for item in result["items"]:
                print("$" + str(item["est_usd"]), "[" + item.get("source", "?") + "]", item.get("title", "?"))
                print(" ", item["url"])
            if args.command == "new":
                print("Next polling timestamp:", result["next_since"])
    except (MCPError, ValueError) as exc:
        print("Error:", exc, file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
