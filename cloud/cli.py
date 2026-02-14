"""Cloudjack CLI — quick cloud operations from the command line.

Usage examples::

    cloudjack --provider aws --service storage list-buckets
    cloudjack --provider gcp --service secret_manager get-secret --name my-secret
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the ``cloudjack`` CLI.

    Returns:
        Configured :class:`~argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="cloudjack",
        description="Unified multi-cloud CLI",
    )
    parser.add_argument(
        "--provider", "-p",
        required=True,
        choices=["aws", "gcp"],
        help="Cloud provider",
    )
    parser.add_argument(
        "--service", "-s",
        required=True,
        choices=[
            "secret_manager", "storage", "queue",
            "compute", "dns", "iam", "logging",
        ],
        help="Cloud service",
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="{}",
        help='JSON config string (e.g. \'{"region_name":"us-east-1"}\')',
    )
    parser.add_argument(
        "operation",
        help="Operation to perform (method name, e.g. list-buckets)",
    )
    parser.add_argument(
        "args",
        nargs="*",
        help="Positional arguments for the operation",
    )
    parser.add_argument(
        "--kwargs", "-k",
        type=str,
        default="{}",
        help="JSON keyword arguments for the operation",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """CLI entry point.

    Parses arguments, creates a service client via the universal factory,
    and invokes the requested operation.  Results are printed as JSON
    (dicts/lists) or plain text.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = _build_parser()
    ns = parser.parse_args(argv)

    try:
        config: dict[str, Any] = json.loads(ns.config)
    except json.JSONDecodeError as e:
        print(f"Invalid --config JSON: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        kwargs: dict[str, Any] = json.loads(ns.kwargs)
    except json.JSONDecodeError as e:
        print(f"Invalid --kwargs JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Lazy-import to avoid loading all SDKs unconditionally
    from cloud.factory import universal_factory

    try:
        svc = universal_factory(ns.service, ns.provider, config)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Convert operation-name to method_name
    method_name = ns.operation.replace("-", "_")
    method = getattr(svc, method_name, None)
    if method is None or not callable(method):
        print(
            f"Unknown operation '{ns.operation}' for {ns.provider}/{ns.service}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        result = method(*ns.args, **kwargs)
    except Exception as e:
        print(f"Operation failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Pretty-print result
    if result is None:
        print("OK")
    elif isinstance(result, (dict, list)):
        print(json.dumps(result, indent=2, default=str))
    else:
        print(result)


if __name__ == "__main__":
    main()
