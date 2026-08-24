import json
import unittest

from chainstatelens.core import parse_spec
from chainstatelens.rpc import JsonRpc, RpcError, collect


class Response:
    def __init__(self, value):
        self.value = value
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return json.dumps(self.value).encode()


class FakeOpener:
    def __init__(self):
        self.calls = []
    def __call__(self, request, timeout):
        payload = json.loads(request.data)
        self.calls.append(payload)
        method, params = payload["method"], payload["params"]
        if method == "eth_chainId": value = "0x1"
        elif method == "eth_getBlockByNumber":
            value = {"number":"0xa","hash":"0x"+"a"*64,"timestamp":"0x64","gasUsed":"0x5","gasLimit":"0xa","baseFeePerGas":"0x1","transactions":[]}
        elif method == "eth_getBalance": value = "0x2"
        elif method == "eth_getTransactionCount": value = "0x0"
        elif method == "eth_getCode": value = "0x"
        else: value = "0x" + "0" * 64
        return Response({"jsonrpc":"2.0","id":payload["id"],"result":value})


class RpcTests(unittest.TestCase):
    def test_collect_uses_only_allowlisted_block_pinned_reads(self):
        spec = parse_spec({"blocks":[10],"targets":[{"label":"x","address":"0x"+"1"*40,"storage_slots":["0x"+"0"*64]}]})
        opener = FakeOpener()
        evidence = collect(spec, JsonRpc("http://example.invalid", opener))
        self.assertEqual(evidence["chain_id"], "0x1")
        methods = [call["method"] for call in opener.calls]
        self.assertEqual(methods[0], "eth_chainId")
        self.assertEqual(methods.count("eth_getBlockByNumber"), 2)
        for call in opener.calls[2:-1]:
            self.assertEqual(call["params"][-1], "0xa")

    def test_rejects_non_http_rpc(self):
        with self.assertRaisesRegex(RpcError, "http"):
            JsonRpc("file:///tmp/socket")

    def test_rejects_write_method(self):
        rpc = JsonRpc("https://example.invalid", FakeOpener())
        with self.assertRaisesRegex(RpcError, "not read-only"):
            rpc.call("eth_sendRawTransaction", ["0x00"])
