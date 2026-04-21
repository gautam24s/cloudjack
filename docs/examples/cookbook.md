# Cookbook

End-to-end recipes that chain multiple services together. Copy, tweak, run.

## Daily backup from an app server to cloud storage

Upload a local file (e.g. a Postgres dump) to S3 every night. Include retry for transient network errors.

```python
from datetime import datetime
from cloudjack import universal_factory
from cloudjack.base.retry import retry
from cloudjack import StorageError

storage = universal_factory("storage", "aws", {"region_name": "us-east-1"})

@retry(max_attempts=3, retryable_exceptions=(StorageError, ConnectionError))
def upload_backup(local_path: str, bucket: str, prefix: str = "backups/") -> str:
    key = f"{prefix}{datetime.utcnow():%Y-%m-%d}/{local_path.rsplit('/', 1)[-1]}"
    storage.upload_object_from_file(bucket, key, local_path)
    return key

key = upload_backup("/var/backups/db.dump", "my-backup-bucket")
print(f"uploaded to s3://my-backup-bucket/{key}")
```

## Deploy a VM with its access credentials stored in Secret Manager

Generate an SSH-equivalent secret, store it, then launch an EC2 instance that can read it via its IAM role.

```python
import json
import secrets as stdlib_secrets
from cloudjack import universal_factory

aws_config = {"region_name": "us-east-1"}
ec2 = universal_factory("compute", "aws", aws_config)
sm  = universal_factory("secret_manager", "aws", aws_config)
iam = universal_factory("iam", "aws", aws_config)

# 1. Generate and store a fresh secret
API_KEY = stdlib_secrets.token_urlsafe(32)
sm.create_secret("prod/app/api-key", API_KEY)

# 2. Create a role the VM can assume
trust = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "ec2.amazonaws.com"},
        "Action": "sts:AssumeRole",
    }],
}
role_arn = iam.create_role("app-ec2-role", trust)

# 3. Attach a managed policy that allows reading Secrets Manager
iam.attach_policy("app-ec2-role", "SecretsManagerReadWrite", managed=True)

# 4. Launch the instance with a user-data script that pulls the secret
user_data = """#!/bin/bash
aws secretsmanager get-secret-value --secret-id prod/app/api-key > /root/api-key.json
"""

instance_id = ec2.create_instance(
    name="app-1",
    instance_type="t3.micro",
    image_id="ami-0abcdef1234567890",
    key_name="ops",
    user_data=user_data,
)
print(f"launched {instance_id} with role {role_arn}")
```

## Sync DNS zones between providers

You're migrating from Route 53 to Cloud DNS and want every record mirrored:

```python
from cloudjack import universal_factory, ZoneAlreadyExistsError

aws_dns = universal_factory("dns", "aws", {"region_name": "us-east-1"})
gcp_dns = universal_factory("dns", "gcp", {"project_id": "my-project"})

def mirror(aws_zone_id: str, zone_name: str) -> None:
    try:
        gcp_zone_id = gcp_dns.create_zone(zone_name, description="mirrored from aws")
    except ZoneAlreadyExistsError:
        gcp_zone_id = next(
            z["zone_id"] for z in gcp_dns.list_zones()
            if z["name"].rstrip(".") == zone_name.rstrip(".")
        )

    for r in aws_dns.list_records(aws_zone_id):
        if r["type"] in {"NS", "SOA"}:
            continue  # GCP manages its own NS/SOA
        gcp_dns.create_record(gcp_zone_id, r["name"], r["type"], r["values"], ttl=r["ttl"])

mirror("Z0123456ABCDEF", "example.com.")
```

## Log every queue message to Cloud Logging

A worker that processes messages and writes structured audit entries:

```python
import json
import asyncio
from cloudjack import universal_factory, MessageError

region = {"region_name": "us-east-1"}
q   = universal_factory("queue",   "aws", region)
log = universal_factory("logging", "aws", region)

QUEUE_ID = q.create_queue("events")
LOG_GROUP = "/app/events/audit"
log.create_log_group(LOG_GROUP, retention_days=30)

async def handle(body: str) -> None:
    # ... real work ...
    await asyncio.sleep(0)

async def worker():
    while True:
        msgs = await q.areceive_messages(QUEUE_ID, max_messages=10, wait_time_seconds=20)
        for m in msgs:
            try:
                await handle(m["body"])
            except Exception as e:
                await log.awrite_log(
                    LOG_GROUP,
                    json.dumps({"event": "handler_failed", "body": m["body"], "error": str(e)}),
                    severity="ERROR",
                )
                continue
            await log.awrite_log(
                LOG_GROUP,
                json.dumps({"event": "handler_ok", "message_id": m["message_id"]}),
                severity="INFO",
            )
            await q.adelete_message(QUEUE_ID, m["receipt_handle"])

asyncio.run(worker())
```

## Issue a signed upload URL, accept the upload, then kick off processing

Browser uploads directly to storage; once the object is there you enqueue a job:

```python
from cloudjack import universal_factory

region = {"region_name": "us-east-1"}
storage = universal_factory("storage", "aws", region)
queue   = universal_factory("queue",   "aws", region)

QUEUE_ID = queue.create_queue("image-pipeline")

def request_upload(user_id: str, filename: str) -> str:
    key = f"uploads/{user_id}/{filename}"
    return storage.generate_signed_url(
        "my-bucket",
        key,
        expiration=600,
        method="PUT",
        content_type="image/jpeg",
    )

def notify_upload_complete(user_id: str, key: str) -> None:
    # Called by your server once the client reports the upload succeeded
    queue.send_message(QUEUE_ID, f"{user_id}|{key}")
```

## Bulk-stop non-production EC2 instances at the end of the day

```python
from cloudjack import universal_factory

ec2 = universal_factory("compute", "aws", {"region_name": "us-east-1"})

for inst in ec2.list_instances(filters=[
    {"Name": "instance-state-name", "Values": ["running"]},
    {"Name": "tag:environment", "Values": ["dev", "staging"]},
]):
    print("stopping", inst["instance_id"], inst["name"])
    ec2.stop_instance(inst["instance_id"])
```

## Rotate an API key across AWS and GCP

```python
import secrets as stdlib_secrets
from cloudjack import universal_factory, SecretNotFoundError

aws = universal_factory("secret_manager", "aws", {"region_name": "us-east-1"})
gcp = universal_factory("secret_manager", "gcp", {"project_id": "my-project"})

new = stdlib_secrets.token_urlsafe(32)

def rotate(sm, name: str, value: str) -> None:
    try:
        sm.update_secret(name, value)
    except SecretNotFoundError:
        sm.create_secret(name, value)

rotate(aws, "prod/app/api-key", new)
rotate(gcp, "prod-app-api-key", new)
```

## Inventory everything (async)

Fetch a cross-cloud snapshot of buckets, queues, and VMs in parallel:

```python
import asyncio
from cloudjack import universal_factory

aws = {"region_name": "us-east-1"}
gcp = {"project_id": "my-project"}

s_aws = universal_factory("storage", "aws", aws)
s_gcp = universal_factory("storage", "gcp", gcp)
q_aws = universal_factory("queue",   "aws", aws)
c_aws = universal_factory("compute", "aws", aws)

async def inventory():
    buckets_aws, buckets_gcp, queues_aws, vms_aws = await asyncio.gather(
        s_aws.alist_buckets(),
        s_gcp.alist_buckets(),
        q_aws.alist_queues(),
        c_aws.alist_instances(),
    )
    return {
        "aws_buckets": buckets_aws,
        "gcp_buckets": buckets_gcp,
        "aws_queues":  queues_aws,
        "aws_vms":     [i["instance_id"] for i in vms_aws],
    }

print(asyncio.run(inventory()))
```
