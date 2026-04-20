# IAM — Examples

Covers AWS IAM and GCP IAM. The concept of "role" is similar across providers but the policy model differs — AWS uses managed/inline policy ARNs, GCP uses project-level bindings between roles and member strings. Cloudjack exposes both behind the same `create_role` / `attach_policy` / `detach_policy` / `list_policies` interface.

## Create a role

=== "AWS"

    ```python
    import json
    from cloudjack import universal_factory

    iam = universal_factory("iam", "aws", {"region_name": "us-east-1"})

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }],
    }

    arn = iam.create_role(
        role_name="ec2-app-role",
        trust_policy=trust_policy,
        description="Allow EC2 instances to run the app",
    )
    # -> 'arn:aws:iam::123456789012:role/ec2-app-role'
    ```

=== "GCP"

    ```python
    from cloudjack import universal_factory

    iam = universal_factory("iam", "gcp", {"project_id": "my-project"})

    role_name = iam.create_role(
        role_name="appReader",
        trust_policy={
            "title": "App Reader",
            "description": "Read application buckets and secrets",
            "permissions": [
                "storage.buckets.get",
                "storage.objects.list",
                "secretmanager.versions.access",
            ],
            "stage": "GA",
        },
    )
    # -> 'projects/my-project/roles/appReader'
    ```

## Attach a policy

=== "AWS"

    ```python
    # Attach an AWS-managed policy
    iam.attach_policy("ec2-app-role", "AmazonS3ReadOnlyAccess", managed=True)

    # Attach a customer-managed policy by name (ARN is built automatically)
    iam.attach_policy("ec2-app-role", "MyCustomPolicy")

    # Or pass the full ARN directly
    iam.attach_policy("ec2-app-role", "arn:aws:iam::aws:policy/AWSLambdaExecute")
    ```

=== "GCP"

    ```python
    # In GCP, "attaching a policy" means binding a member to a role
    iam.attach_policy("roles/storage.objectViewer", "user:alice@example.com")
    iam.attach_policy("roles/editor", "serviceAccount:robot@my-project.iam.gserviceaccount.com")
    ```

    The read-modify-write of the project IAM policy is wrapped in an etag-retry loop, so concurrent `attach_policy` / `detach_policy` calls are safe.

## Detach a policy

```python
# AWS
iam.detach_policy("ec2-app-role", "AmazonS3ReadOnlyAccess", managed=True)

# GCP
iam.detach_policy("roles/storage.objectViewer", "user:alice@example.com")
```

## List roles and policies

```python
for r in iam.list_roles():
    print(r["role_name"], r["role_id"])

for p in iam.list_policies():
    print(p["policy_name"], p["policy_identifier"])
```

## Idempotent role creation

```python
from cloudjack import RoleAlreadyExistsError

try:
    iam.create_role("ec2-app-role", trust_policy)
except RoleAlreadyExistsError:
    pass  # already configured
```

## Grant a fresh user read-only access to a bucket (GCP)

```python
iam = universal_factory("iam", "gcp", {"project_id": "my-project"})
iam.attach_policy("roles/storage.objectViewer", "user:new-hire@example.com")
```

## Revoke every role for a departing user (GCP)

```python
def revoke_all(iam, member: str) -> None:
    for p in iam.list_policies():
        # `list_policies` returns one dict per role binding; members live on the binding
        if member in p.get("members", []):
            iam.detach_policy(p["policy_name"], member)

revoke_all(iam, "user:ex-employee@example.com")
```

## Error handling

```python
from cloudjack import RoleNotFoundError, RoleAlreadyExistsError, IAMError

try:
    iam.delete_role("ghost-role")
except RoleNotFoundError:
    ...
except IAMError:
    ...
```

## CLI

```bash
cloudjack -p aws -s iam list-roles
cloudjack -p aws -s iam attach-policy ec2-app-role AmazonS3ReadOnlyAccess -k '{"managed":true}'
cloudjack -p gcp -s iam list-policies -c '{"project_id":"p"}'
```
