"""Private provider bridge CLI and public entrypoints."""
from __future__ import annotations

import argparse
import json
import sys
from .provider_common import (
    BASE_URL,
    CLIENT_VERSION,
    MAX_BODY,
    MAX_STREAM,
    MODEL_ID,
    UNENFORCED,
    ProviderError,
)
from .provider_http import (
    GatewayHandler,
    GatewayServer,
)
from .provider_protocol import (
    anthropic_completion,
    anthropic_to_chat,
    chat_completion,
    normalize_request,
    public_response,
    usage_counts,
)
from .provider_service import (
    ProviderBridge,
)
from .provider_transport import (
    CodexTransport,
    TokenSource,
    create_gateway_key,
    parse_sse,
    read_gateway_key,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    key = commands.add_parser("key", help="Create a private gateway key without printing it")
    key.add_argument("--file", required=True)
    for name in ("models", "serve"):
        sub = commands.add_parser(name)
        sub.add_argument("--token-file", required=True)
        sub.add_argument("--timeout", type=int, default=180)
        if name == "serve":
            sub.add_argument("--gateway-key-file", required=True)
            sub.add_argument("--port", type=int, default=8789)
            sub.add_argument("--max-concurrency", type=int, default=2)
            sub.add_argument("--requests-per-minute", type=int, default=20)
            sub.add_argument("--compatibility-policy", choices=("strict", "codex-native"), default="strict")
            sub.add_argument("--allowed-model", action="append")
    args = parser.parse_args(argv)
    try:
        if args.command == "key":
            create_gateway_key(args.file)
            return 0
        if not 1 <= args.timeout <= 900:
            raise ValueError("Timeout must be between 1 and 900 seconds")
        token = TokenSource(args.token_file)
        _, expiry = token.read()
        transport = CodexTransport(token, args.timeout)
        bridge = ProviderBridge(transport, **({"max_concurrency": args.max_concurrency,
                                "requests_per_minute": args.requests_per_minute, "policy": args.compatibility_policy,
                                "allowed_models": args.allowed_model} if args.command == "serve" else {}))
        if args.command == "models":
            print(json.dumps({**bridge.models(), "credential_expires_at": expiry}, indent=2))
            return 0
        key_value = read_gateway_key(args.gateway_key_file)
        server = GatewayServer(("127.0.0.1", args.port), bridge, key_value)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    except (ProviderError, ValueError, OSError) as exc:
        # Do not print generic exception strings: filesystem paths and provider details are private.
        print(json.dumps({"error": exc.code if isinstance(exc, ProviderError) else "gateway_configuration_error"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
