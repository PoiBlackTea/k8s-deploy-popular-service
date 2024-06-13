import iam
import vpc
import pulumi
import pulumi_gcp as gcp
import requests


gcp_config = pulumi.Config("gcp")
project = gcp_config.require("project")
location = gcp_config.require("zone")
cidr = f"{requests.get('https://api.ipify.org').text}/32"

# create GKE
primary = gcp.container.Cluster("gke",
    name=f"gke-{pulumi.get_stack()}",
    location=location,
    remove_default_node_pool=True,
    initial_node_count=1,
    addons_config=gcp.container.ClusterAddonsConfigArgs(
        gce_persistent_disk_csi_driver_config=gcp.container.ClusterAddonsConfigGcePersistentDiskCsiDriverConfigArgs(enabled=True),
        horizontal_pod_autoscaling=gcp.container.ClusterAddonsConfigHorizontalPodAutoscalingArgs(disabled=False),
        http_load_balancing=gcp.container.ClusterAddonsConfigHttpLoadBalancingArgs(disabled=False),
        network_policy_config=gcp.container.ClusterAddonsConfigNetworkPolicyConfigArgs(disabled=False)
    ),
    network=vpc.gke_network,
    subnetwork=vpc.gke_subnetwork,
    private_cluster_config=gcp.container.ClusterPrivateClusterConfigArgs(
        enable_private_nodes=True,
        master_ipv4_cidr_block="10.0.100.0/28"),
    networking_mode="VPC_NATIVE",
    ip_allocation_policy=gcp.container.ClusterIpAllocationPolicyArgs(),
    master_authorized_networks_config=gcp.container.ClusterMasterAuthorizedNetworksConfigArgs(
        cidr_blocks=[gcp.container.ClusterMasterAuthorizedNetworksConfigCidrBlockArgs(cidr_block=cidr)]
    )
)
primary_preemptible_nodes = gcp.container.NodePool("gke-node-pools",
    name=f"gke-node-pools-{pulumi.get_stack()}",
    location=location,
    cluster=primary.name,
    node_count=3,
    node_config=gcp.container.NodePoolNodeConfigArgs(
        preemptible=False,
        machine_type="e2-medium",
        service_account=iam.gke_sa.email,
        oauth_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
)

pulumi.export("GKE Cluster Name", primary.name)
pulumi.export("Control plane authorized networks", cidr)