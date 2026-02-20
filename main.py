from cloud import universal_factory



def main():
    # Example usage of the universal factory
    aws_config = {
        "aws_access_key_id": "AKIAEXAMPLE",
        "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "region_name": "us-west-1",
    }
    gcp_config = {"project_id": "my-gcp-project"}

    aws_storage = universal_factory("storage", "aws", aws_config)
    gcp_storage = universal_factory("storage", "gcp", gcp_config)

    print(f"AWS Storage: {aws_storage}")
    print(f"GCP Storage: {gcp_storage}")

if __name__ == "__main__":
    main()