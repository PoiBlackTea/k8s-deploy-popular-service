from pulumi_gcp import serviceaccount, projects

# Harden your cluster's securitys. Use least privilege IAM service accounts
# https://cloud.google.com/kubernetes-engine/docs/how-to/hardening-your-cluster#permissions

gke_sa = serviceaccount.Account(
    "gke-sa",
    account_id="gke-sa",
    display_name="GKE Service Account"
)

projects.IAMMember(
    "gke-logg-write-policy-attachment",
    project=gke_sa.project,
    role="roles/logging.logWriter",
    member=gke_sa.member
)

projects.IAMMember(
    "gke-metrics-write-policy-attachment",
    project=gke_sa.project,
    role="roles/monitoring.metricWriter",
    member=gke_sa.member
)

projects.IAMMember(
    "gke-monitor-viewer-policy-attachment",
    project=gke_sa.project,
    role="roles/monitoring.viewer",
    member=gke_sa.member
)

projects.IAMMember(
    "gke-metadata-write-policy-attachment",
    project=gke_sa.project,
    role="roles/stackdriver.resourceMetadata.writer",
    member=gke_sa.member
)

projects.IAMMember(
    "gke-autoscaling-metrics-write-policy-attachment",
    project=gke_sa.project,
    role="roles/autoscaling.metricsWriter",
    member=gke_sa.member
)