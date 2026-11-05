import json
import unittest
import mcp_client as m

def response(value, request_id=1):
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "result": value}).encode("utf-8")

class FakeHTTPResponse:
    headers = {"Content-Type": "application/json"}
    def __init__(self, data): self.data = data
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def read(self, _limit): return self.data

def item(**changes):
    row = {"kind": "bounty", "title": "Example", "source": "direct",
           "requires": [], "est_usd": 5, "slots_left": 1,
           "url": "https://example.com/example", "verified": {}}
    row.update(changes)
    return row

class MCPClientTests(unittest.TestCase):
    def test_initialize(self):
        seen = []
        def opener(req, timeout):
            seen.append(json.loads(req.data))
            return FakeHTTPResponse(response({"serverInfo": {"name": "agent-bounty-feed"}}))
        client = m.Client(opener=opener)
        client.initialize()
        self.assertEqual(seen[0]["method"], "initialize")
        self.assertEqual(seen[0]["params"]["protocolVersion"], m.PROTOCOL)

    def test_structured(self):
        client = m.Client(opener=lambda req, timeout: FakeHTTPResponse(
            response({"isError": False, "structuredContent": {"count": 3}})))
        self.assertEqual(client.tool("get_feed_stats")["count"], 3)

    def test_text_fallback(self):
        client = m.Client(opener=lambda req, timeout: FakeHTTPResponse(
            response({"content": [{"type": "text", "text": "{\"count\": 2}"}]})))
        self.assertEqual(client.tool("get_feed_stats")["count"], 2)

    def test_server_tool_error(self):
        client = m.Client(opener=lambda req, timeout: FakeHTTPResponse(
            response({"isError": True, "content": [{"type": "text", "text": "no access"}]})))
        with self.assertRaisesRegex(m.MCPError, "no access"):
            client.tool("get_bounty")

    def test_response_id_mismatch(self):
        client = m.Client(opener=lambda req, timeout: FakeHTTPResponse(response({}, 99)))
        with self.assertRaises(m.MCPError):
            client.rpc("ping")

    def test_non_https(self):
        with self.assertRaises(ValueError):
            m.Client("http://invalid")

    def test_accept_valid(self):
        self.assertEqual(len(m.filter_items([item()])), 1)

    def test_reject_kyc(self):
        self.assertEqual(m.filter_items([item(requires=["kyc"])]), [])

    def test_reject_bond(self):
        self.assertEqual(m.filter_items([item(requires=["bond"])]), [])

    def test_reject_human_only(self):
        self.assertEqual(m.filter_items([item(requires=["human_only"])]), [])

    def test_reject_expired_slots(self):
        self.assertEqual(m.filter_items([item(slots_left=0)]), [])

    def test_reject_degraded(self):
        self.assertEqual(m.filter_items([item(verified={"degraded": True})]), [])

    def test_reject_stale(self):
        self.assertEqual(m.filter_items([item(stale=True)]), [])

    def test_reject_non_bounty(self):
        self.assertEqual(m.filter_items([item(kind="audit_contest")]), [])

    def test_reject_invalid_url(self):
        self.assertEqual(m.filter_items([item(url="http://example.com")]), [])

    def test_pagination(self):
        class FakeClient:
            def __init__(self): self.calls = []
            def tool(self, name, args):
                self.calls.append(args)
                if len(self.calls) == 1:
                    return {"has_more": True, "next_since": "2026-11-04T00:00:00Z",
                            "next_after_id": "b", "items": [{"id": "a"}]}
                return {"has_more": False, "next_since": "2026-11-05T00:00:00Z",
                        "items": [{"id": "b"}]}
        fake = FakeClient()
        pages = list(m.new_pages(fake, "2026-11-03T00:00:00Z"))
        self.assertEqual(len(pages), 2)
        self.assertEqual(fake.calls[1]["after_id"], "b")
        self.assertEqual(fake.calls[1]["since"], "2026-11-04T00:00:00Z")

    def test_invalid_cursor(self):
        class FakeClient:
            def tool(self, name, args):
                return {"has_more": True, "next_since": args["since"], "next_after_id": None}
        with self.assertRaises(m.MCPError):
            list(m.new_pages(FakeClient(), "2026-11-03T00:00:00Z"))

if __name__ == "__main__":
    unittest.main()
