"""
Exceptions for secret manager
"""


class SecretManagerError(Exception):
    """Base exception for secret manager"""


class SecretNotFoundError(SecretManagerError):
    """Secret not found"""


class SecretAlreadyExistsError(SecretManagerError):
    """Secret already exists"""


"""
Exceptions for cloud storage
"""


class StorageError(Exception):
    """Base exception for cloud storage operations."""


class BucketNotFoundError(StorageError):
    """Bucket not found."""


class BucketAlreadyExistsError(StorageError):
    """Bucket already exists."""


class ObjectNotFoundError(StorageError):
    """Object not found."""
