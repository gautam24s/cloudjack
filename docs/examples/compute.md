# Compute — Examples

Covers AWS EC2 and GCP Compute Engine. Instance types, image IDs, and zone/subnet details are provider-specific; everything else is portable.

## Launch

=== "AWS"

    ```python
    from cloudjack import universal_factory

    ec2 = universal_factory("compute", "aws", {"region_name": "us-east-1"})

    instance_id = ec2.create_instance(
        name="web-1",
        instance_type="t3.micro",
        image_id="ami-0abcdef1234567890",      # Amazon Linux 2023 in us-east-1
        key_name="my-key",
        security_group_ids=["sg-0123456789abcdef0"],
        subnet_id="subnet-0123456789abcdef0",
        user_data="#!/bin/bash\necho hello > /tmp/hello.txt\n",
    )
    ```

=== "GCP"

    ```python
    from cloudjack import universal_factory

    gce = universal_factory("compute", "gcp", {"project_id": "my-project"})

    instance_id = gce.create_instance(
        name="web-1",
        instance_type="e2-small",
        image_id="projects/debian-cloud/global/images/family/debian-12",
        zone="us-central1-a",
        metadata={"env": "prod"},
    )
    ```

## Inspect

```python
# One-off lookup
info = ec2.get_instance(instance_id)
print(info["state"], info.get("public_ip"))

# List (optional filter)
running = ec2.list_instances(filters=[
    {"Name": "instance-state-name", "Values": ["running"]}
])
```

GCP's `list_instances` takes `zone=` and `filter=` keyword arguments:

```python
gce.list_instances(zone="us-central1-a", filter='status = "RUNNING"')
```

## Lifecycle

```python
ec2.stop_instance(instance_id)
ec2.start_instance(instance_id)
ec2.terminate_instance(instance_id)   # destroys the instance
```

## Wait for a state transition

There's no built-in waiter — poll with a small delay:

```python
import time

def wait_for(compute, instance_id: str, desired: str, timeout: int = 300) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if compute.get_instance(instance_id)["state"] == desired:
            return
        time.sleep(5)
    raise TimeoutError(f"instance {instance_id} did not reach {desired}")

ec2.start_instance(instance_id)
wait_for(ec2, instance_id, "running")
```

## Bulk-stop all running instances

```python
for inst in ec2.list_instances(filters=[
    {"Name": "instance-state-name", "Values": ["running"]}
]):
    ec2.stop_instance(inst["instance_id"])
```

## Concurrent status snapshot

```python
import asyncio

async def snapshot(compute) -> list[dict]:
    instances = await compute.alist_instances()
    # Every detail call runs in parallel
    return await asyncio.gather(*(
        compute.aget_instance(i["instance_id"]) for i in instances
    ))

asyncio.run(snapshot(ec2))
```

## Idempotent launch

If you want "launch if not already present", key off `name`:

```python
def ensure_instance(compute, name: str, **kw) -> str:
    for inst in compute.list_instances():
        if inst["name"] == name and inst["state"] != "terminated":
            return inst["instance_id"]
    return compute.create_instance(name=name, **kw)
```

## Error handling

```python
from cloudjack import InstanceNotFoundError, ComputeError

try:
    ec2.get_instance("i-bad-id")
except InstanceNotFoundError:
    ...
except ComputeError as e:
    # any other compute failure
    ...
```

## CLI

```bash
cloudjack -p aws -s compute list-instances
cloudjack -p aws -s compute stop-instance i-0123456789abcdef0
cloudjack -p gcp -s compute list-instances -c '{"project_id":"p"}' -k '{"zone":"us-central1-a"}'
```
