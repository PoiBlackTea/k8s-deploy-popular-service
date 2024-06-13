import pulumi
from pulumi_gcp import compute as compute

gcp_config = pulumi.Config("gcp")
region = gcp_config.require("region")

# create custom vpc
gke_network = compute.Network("gke-vpc",
    name=f"gke-vpc-{pulumi.get_stack()}",
    auto_create_subnetworks=False,
    description="gke vpc",
    mtu=1460)


# create custom vpc subnet
gke_subnetwork = compute.Subnetwork("gke-subnet1",
    name=f"gke-subnet1-{pulumi.get_stack()}",
    ip_cidr_range="10.0.2.0/24",
    region=region,
    network=gke_network.id,
    private_ip_google_access=True)

# create vpc nat
addr = compute.Address("addr", region=region)
router = compute.Router("router",
    region=gke_subnetwork.region,
    network=gke_network.id
    )
nat = compute.RouterNat("nat",
    router=router.name,
    region=router.region,
    nat_ip_allocate_option="MANUAL_ONLY",
    nat_ips=[addr.self_link],
    source_subnetwork_ip_ranges_to_nat="ALL_SUBNETWORKS_ALL_IP_RANGES",
    log_config=compute.RouterNatLogConfigArgs(
        enable=True,
        filter="ERRORS_ONLY",
    ))

# create firewall allow ingress iap traffic
default_firewall = compute.Firewall("allow-from-iap",
    network=gke_network.name,
    allows=[
        compute.FirewallAllowArgs(
            protocol="tcp",
            ports=[
                "22",
            ],
        ),
    ],
    priority=500,
    source_ranges=["35.235.240.0/20"])