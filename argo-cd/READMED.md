# Argo-cd

## Prerequisites

Ensure you have [Python 3](https://www.python.org/downloads/) and [the Pulumi CLI](https://www.pulumi.com/docs/get-started/install/).

We will be deploying to Google Cloud Platform (GCP), so you will need an account. If you don't have an account,
[sign up for free here](https://cloud.google.com/free/). In either case,
[follow the instructions here](https://www.pulumi.com/docs/intro/cloud-providers/gcp/setup/) to connect Pulumi to your GCP account.

This example assumes that you have GCP's `gcloud` CLI on your path. This is installed as part of the
[GCP SDK](https://cloud.google.com/sdk/).


## Running the Example

1. Create a new stack, which is an isolated deployment target for this example:

    ```bash
    pulumi stack init dev
    ```

2. Set the required configuration variables for this program:

    ```
    pulumi config set gcp:project <project>
    pulumi config set gcp:region <region>
    pulumi config set gcp:zone <zone>
    pulumi config set data:cluster <cluster>
    ```

After reaching the UI the first time you can login with username: admin and the random password generated during the installation. You can find the password by running:
```
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```