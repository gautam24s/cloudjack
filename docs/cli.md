# CLI Reference

Cloudjack ships a command-line tool for quick cloud operations.

## Usage

```bash
cloudjack --provider <aws|gcp> --service <service> <operation> [args...] [--kwargs '{}']
```

## Options

| Flag | Short | Description |
|---|---|---|
| `--provider` | `-p` | Cloud provider (`aws` or `gcp`) |
| `--service` | `-s` | Service name (see below) |
| `--config` | `-c` | JSON config string |
| `--kwargs` | `-k` | JSON keyword arguments for the operation |

## Services

`secret_manager`, `storage`, `queue`, `compute`, `dns`, `iam`, `logging`

## Examples

```bash
# List S3 buckets
cloudjack -p aws -s storage list-buckets

# Create a secret
cloudjack -p aws -s secret_manager create-secret my-secret s3cr3t

# Get a GCP secret
cloudjack -p gcp -s secret_manager get-secret \
  -c '{"project_id":"my-project"}' my-secret

# Send an SQS message
cloudjack -p aws -s queue send-message \
  https://sqs.us-east-1.amazonaws.com/123/my-queue "Hello"
```

## Source

::: cloud.cli
    options:
      show_root_heading: false
