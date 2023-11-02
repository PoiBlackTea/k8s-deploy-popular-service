import pulumi
import pulumi_gcp as gcp
import requests


gcp_config = pulumi.Config("gcp")
project = gcp_config.require("project")
region = gcp_config.require("region")
location = gcp_config.require("zone")
cidr = f"{requests.get('https://api.ipify.org').text}/32"

gke_sa = gcp.serviceaccount.Account("gke-sa",
    account_id="gke-sa",
    display_name="GKE Service Account")

gke_sa_iam1 = gcp.projects.IAMMember("gke-sa-iam1",
    project=gke_sa.project,
    role="roles/logging.logWriter",
    member=gke_sa.member)

gke_sa_iam2= gcp.projects.IAMMember("gke-sa-iam2",
    project=gke_sa.project,
    role="roles/monitoring.metricWriter",
    member=gke_sa.member)

gke_sa_iam3 = gcp.projects.IAMMember("gke-sa-iam3",
    project=gke_sa.project,
    role="roles/monitoring.viewer",
    member=gke_sa.member)

gke_sa_iam4 = gcp.projects.IAMMember("gke-sa-iam4",
    project=gke_sa.project,
    role="roles/stackdriver.resourceMetadata.writer",
    member=gke_sa.member)

gke_sa_iam5 = gcp.projects.IAMMember("gke-sa-iam5",
    project=gke_sa.project,
    role="roles/autoscaling.metricsWriter",
    member=gke_sa.member)


# create custom vpc
gke_network = gcp.compute.Network("gke-vpc",
    auto_create_subnetworks=False,
    description="gke vpc",
    mtu=1460)


# create custom vpc subnet
gke_subnetwork = gcp.compute.Subnetwork("gke-demo-subnet1",
    ip_cidr_range="10.0.2.0/24",
    region=region,
    network=gke_network.id,
    private_ip_google_access=True)

# create vpc nat
addr = gcp.compute.Address("addr", region=region)
router = gcp.compute.Router("router",
    region=gke_subnetwork.region,
    network=gke_network.id
    )
nat = gcp.compute.RouterNat("nat",
    router=router.name,
    region=router.region,
    nat_ip_allocate_option="MANUAL_ONLY",
    nat_ips=[addr.self_link],
    source_subnetwork_ip_ranges_to_nat="ALL_SUBNETWORKS_ALL_IP_RANGES",
    log_config=gcp.compute.RouterNatLogConfigArgs(
        enable=True,
        filter="ERRORS_ONLY",
    ))

# create GKE
primary = gcp.container.Cluster("primary",
    location=location,
    remove_default_node_pool=True,
    initial_node_count=1,
    addons_config=gcp.container.ClusterAddonsConfigArgs(
        gce_persistent_disk_csi_driver_config=gcp.container.ClusterAddonsConfigGcePersistentDiskCsiDriverConfigArgs(enabled=True),
        horizontal_pod_autoscaling=gcp.container.ClusterAddonsConfigHorizontalPodAutoscalingArgs(disabled=False),
        http_load_balancing=gcp.container.ClusterAddonsConfigHttpLoadBalancingArgs(disabled=False)
    ),
    network=gke_network,
    subnetwork=gke_subnetwork,
    private_cluster_config=gcp.container.ClusterPrivateClusterConfigArgs(
        enable_private_nodes=True,
        master_ipv4_cidr_block="10.0.100.0/28"),
    networking_mode="VPC_NATIVE",
    ip_allocation_policy=gcp.container.ClusterIpAllocationPolicyArgs(),
    master_authorized_networks_config=gcp.container.ClusterMasterAuthorizedNetworksConfigArgs(
        cidr_blocks=[gcp.container.ClusterMasterAuthorizedNetworksConfigCidrBlockArgs(cidr_block=cidr)]
    )
)
primary_preemptible_nodes = gcp.container.NodePool("primarynodes",
    location=location,
    cluster=primary.name,
    node_count=1,
    node_config=gcp.container.NodePoolNodeConfigArgs(
        preemptible=False,
        machine_type="e2-medium",
        service_account=gke_sa.email,
        oauth_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
)

# create firewall allow ingress iap traffic
default_firewall = gcp.compute.Firewall("allow-from-iap",
    network=gke_network.name,
    allows=[
        gcp.compute.FirewallAllowArgs(
            protocol="tcp",
            ports=[
                "22",
            ],
        ),
    ],
    priority=500,
    source_ranges=["35.235.240.0/20"])