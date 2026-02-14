"""
Cloudjack exception hierarchy.

Every cloud service has a top-level error that inherits from
:class:`CloudjackError` and provider-specific sub-exceptions
for common failure modes (not-found, already-exists, etc.).
"""


# ── Base ──────────────────────────────────────────────────────────────
class CloudjackError(Exception):
    """Root exception for all Cloudjack errors."""


# ── Secret Manager ────────────────────────────────────────────────────
class SecretManagerError(CloudjackError):
    """Base exception for secret manager operations."""


class SecretNotFoundError(SecretManagerError):
    """Secret not found."""


class SecretAlreadyExistsError(SecretManagerError):
    """Secret already exists."""


# ── Storage ───────────────────────────────────────────────────────────
class StorageError(CloudjackError):
    """Base exception for cloud storage operations."""


class BucketNotFoundError(StorageError):
    """Bucket not found."""


class BucketAlreadyExistsError(StorageError):
    """Bucket already exists."""


class ObjectNotFoundError(StorageError):
    """Object not found."""


# ── Queue / Messaging ────────────────────────────────────────────────
class QueueError(CloudjackError):
    """Base exception for queue/messaging operations."""


class QueueNotFoundError(QueueError):
    """Queue or topic does not exist."""


class QueueAlreadyExistsError(QueueError):
    """Queue or topic already exists."""


class MessageError(QueueError):
    """Failed to send, receive, or delete a message."""


# ── Compute ───────────────────────────────────────────────────────────
class ComputeError(CloudjackError):
    """Base exception for compute/VM operations."""


class InstanceNotFoundError(ComputeError):
    """VM instance not found."""


class InstanceAlreadyExistsError(ComputeError):
    """VM instance already exists."""


# ── DNS ───────────────────────────────────────────────────────────────
class DNSError(CloudjackError):
    """Base exception for DNS operations."""


class ZoneNotFoundError(DNSError):
    """DNS zone not found."""


class ZoneAlreadyExistsError(DNSError):
    """DNS zone already exists."""


class RecordNotFoundError(DNSError):
    """DNS record not found."""


# ── IAM / Auth ────────────────────────────────────────────────────────
class IAMError(CloudjackError):
    """Base exception for IAM operations."""


class RoleNotFoundError(IAMError):
    """IAM role not found."""


class RoleAlreadyExistsError(IAMError):
    """IAM role already exists."""


class PolicyNotFoundError(IAMError):
    """IAM policy not found."""


# ── Logging ───────────────────────────────────────────────────────────
class LoggingError(CloudjackError):
    """Base exception for logging service operations."""


class LogGroupNotFoundError(LoggingError):
    """Log group / sink not found."""


class LogGroupAlreadyExistsError(LoggingError):
    """Log group / sink already exists."""
