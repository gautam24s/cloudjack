# DNS — Examples

Covers AWS Route 53 and GCP Cloud DNS. Record types (A, AAAA, CNAME, MX, TXT, …) are provider-portable; zone identifiers are provider-specific.

## Create a zone

=== "AWS"

    ```python
    from cloudjack import universal_factory

    dns = universal_factory("dns", "aws", {"region_name": "us-east-1"})

    zone_id = dns.create_zone(
        "example.com.",
        comment="Production zone",
    )
    # -> 'Z0123456ABCDEF'
    ```

=== "GCP"

    ```python
    from cloudjack import universal_factory

    dns = universal_factory("dns", "gcp", {"project_id": "my-project"})

    zone_id = dns.create_zone(
        "example.com.",
        description="Production zone",
    )
    # -> 'example-com'
    ```

## Create records

```python
# A record
dns.create_record(zone_id, "www.example.com.", "A", ["203.0.113.10"], ttl=300)

# CNAME
dns.create_record(zone_id, "api.example.com.", "CNAME", ["www.example.com."])

# MX
dns.create_record(
    zone_id,
    "example.com.",
    "MX",
    ["10 mail1.example.com.", "20 mail2.example.com."],
)

# TXT (SPF)
dns.create_record(zone_id, "example.com.", "TXT", ['"v=spf1 include:_spf.google.com ~all"'])
```

Route 53 uses UPSERT semantics by default — the call creates the record or replaces it. Pass `action="CREATE"` to fail when the record already exists.

## List records

```python
for r in dns.list_records(zone_id):
    print(r["name"], r["type"], r["ttl"], r["values"])
```

`list_records` returns a list of `RecordDict`; each dict has `name`, `type`, `ttl`, `values`.

## Bulk upsert

```python
records = [
    ("www.example.com.", "A",     ["203.0.113.10"], 300),
    ("api.example.com.", "CNAME", ["www.example.com."], 300),
    ("mail.example.com.","A",     ["203.0.113.20"], 300),
]
for name, rtype, values, ttl in records:
    dns.create_record(zone_id, name, rtype, values, ttl=ttl)
```

## Delete a record

Both providers need the exact values/TTL to delete a record; fetch first if unsure:

```python
def delete_records_at(dns, zone_id: str, name: str) -> None:
    for r in dns.list_records(zone_id):
        if r["name"] == name:
            dns.delete_record(zone_id, r["name"], r["type"], r["values"], r["ttl"])
```

## Zone migration (AWS → GCP)

Read every record from a Route 53 zone and recreate it on Cloud DNS:

```python
from cloudjack import universal_factory, ZoneAlreadyExistsError

aws_dns = universal_factory("dns", "aws", {"region_name": "us-east-1"})
gcp_dns = universal_factory("dns", "gcp", {"project_id": "my-project"})

src_id = "Z0123456ABCDEF"
try:
    dst_id = gcp_dns.create_zone("example.com.", description="migrated")
except ZoneAlreadyExistsError:
    dst_id = "example-com"

for r in aws_dns.list_records(src_id):
    # Skip the NS/SOA records — Cloud DNS manages those for you
    if r["type"] in {"NS", "SOA"}:
        continue
    gcp_dns.create_record(dst_id, r["name"], r["type"], r["values"], ttl=r["ttl"])
```

## Idempotent zone creation

```python
from cloudjack import ZoneAlreadyExistsError

try:
    zone_id = dns.create_zone("example.com.")
except ZoneAlreadyExistsError:
    zone_id = next(z["zone_id"] for z in dns.list_zones() if z["name"].rstrip(".") == "example.com")
```

## Error handling

```python
from cloudjack import ZoneNotFoundError, RecordNotFoundError, DNSError

try:
    dns.list_records("missing-zone")
except ZoneNotFoundError:
    ...
except DNSError as e:
    ...
```

## CLI

```bash
cloudjack -p aws -s dns list-zones
cloudjack -p aws -s dns create-record Z0123 www.example.com. A -k '{"values":["203.0.113.10"],"ttl":300}'
```
