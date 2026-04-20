"""Public TypedDicts for blueprint return shapes.

These give IDE autocomplete on the keys of dicts returned by list/get
operations. All provider-specific extras are modelled as ``NotRequired``
so implementations can attach additional keys without failing static
checks.
"""

from __future__ import annotations

from typing import TypedDict

from typing_extensions import NotRequired


class MessageDict(TypedDict):
    """A single message returned from :meth:`QueueService.receive_messages`."""

    message_id: str
    body: str
    receipt_handle: str


class InstanceDict(TypedDict):
    """A compute instance summary returned from :meth:`ComputeService.list_instances` / :meth:`ComputeService.get_instance`."""

    instance_id: str
    name: str
    state: str
    instance_type: NotRequired[str | None]
    launch_time: NotRequired[str]
    public_ip: NotRequired[str | None]
    private_ip: NotRequired[str | None]


class ZoneDict(TypedDict):
    """A DNS zone summary returned from :meth:`DNSService.list_zones`."""

    zone_id: str
    name: str


class RecordDict(TypedDict):
    """A DNS record returned from :meth:`DNSService.list_records`."""

    name: str
    type: str
    ttl: int
    values: list[str]


class RoleDict(TypedDict):
    """An IAM role summary returned from :meth:`IAMService.list_roles`."""

    role_name: str
    role_id: str


class PolicyDict(TypedDict):
    """An IAM policy summary returned from :meth:`IAMService.list_policies`."""

    policy_name: str
    policy_identifier: str


class LogEntryDict(TypedDict):
    """A log entry returned from :meth:`LoggingService.read_logs`."""

    timestamp: str
    message: str
    severity: str


__all__ = [
    "MessageDict",
    "InstanceDict",
    "ZoneDict",
    "RecordDict",
    "RoleDict",
    "PolicyDict",
    "LogEntryDict",
]
