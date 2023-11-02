#!/usr/bin/python3
import requests
import pulumi
import pulumi_gcp as gcp
import pulumi_kubernetes as k8s 

gcp_config = pulumi.Config("gcp")
project = gcp_config.require("project")
zone = gcp_config.require("zone")
cidr = f"{requests.get('https://api.ipify.org').text}/32"
data_config = pulumi.Config("data")
cluster = data_config.require("cluster")

cluster_gke = gcp.container.get_cluster(
    name=cluster,
    location=zone
)

policy = gcp.compute.SecurityPolicy("policy", rules=[
    gcp.compute.SecurityPolicyRuleArgs(
        action="allow",
        description=f"Allow access to IPs in {cidr}",
        match=gcp.compute.SecurityPolicyRuleMatchArgs(
            config=gcp.compute.SecurityPolicyRuleMatchConfigArgs(
                src_ip_ranges=[f"{cidr}"],
            ),
            versioned_expr="SRC_IPS_V1",
        ),
        priority=1000,
    ),
    gcp.compute.SecurityPolicyRuleArgs(
        action="deny(403)",
        description="default rule",
        match=gcp.compute.SecurityPolicyRuleMatchArgs(
            config=gcp.compute.SecurityPolicyRuleMatchConfigArgs(
                src_ip_ranges=["*"],
            ),
            versioned_expr="SRC_IPS_V1",
        ),
        priority=2147483647,
    ),
])

# Manufacture a GKE-style Kubeconfig. Note that this is slightly "different" because of the way GKE requires
# gcloud to be in the picture for cluster authentication (rather than using the client cert/key directly).
k8s_info = pulumi.Output.all(cluster_gke.name, cluster_gke.endpoint, cluster_gke.master_auths[0])
k8s_config = k8s_info.apply(
    lambda info: """apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: {0}
    server: https://{1}
  name: {2}
contexts:
- context:
    cluster: {2}
    user: {2}
  name: {2}
current-context: {2}
kind: Config
preferences: {{}}
users:
- name: {2}
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: gke-gcloud-auth-plugin
      installHint: Install gke-gcloud-auth-plugin for use with kubectl by following
        https://cloud.google.com/blog/products/containers-kubernetes/kubectl-auth-changes-in-gke
      provideClusterInfo: true
""".format(info[2]['cluster_ca_certificate'], info[1], '{0}_{1}_{2}'.format(project, zone, info[0])))

# Make a Kubernetes provider instance that uses our cluster from above.
k8s_provider = k8s.Provider('gke_k8s', kubeconfig=k8s_config)

argo_cd_address = gcp.compute.GlobalAddress("argo-ip")

argo_cd_namespace = k8s.core.v1.Namespace(
    "argo-cd", 
    metadata={
        "name":"argo-cd"
    }
)

backendconfig_manifest = {
    # Add Cloud Armor
    "securityPolicy": {
        "name": policy.name
    },
    # Add your specific BackendConfig configuration here
    "healthCheck": {
        "checkIntervalSec": 30,
        "timeoutSec": 5,
        "healthyThreshold": 1,
        "unhealthyThreshold": 2,
        "type": "HTTP",
        "requestPath": "/healthz",
        "port": 8080
    },
    # Add Session affinity, ref:https://cloud.google.com/kubernetes-engine/docs/how-to/ingress-configuration#backendconfigspec_v1beta1_cloudgooglecom
    "sessionAffinity": {
        "affinityType": "GENERATED_COOKIE"
    }
}

# backend_config = k8s.apiextensions.CustomResource("backendconfig", manifest=backendconfig_manifest)

argo_cd = k8s.helm.v3.Chart(
    "argo-cd",
    k8s.helm.v3.ChartOpts(
        chart="argo-cd",
        version="5.50.0",
        namespace=argo_cd_namespace.metadata["name"],
        fetch_opts=k8s.helm.v3.FetchOpts(
            repo="https://argoproj.github.io/argo-helm",
        ),
        values={
            "server": {
                "extraArgs": ["--insecure"],
                "ingress": {
                    "enabled": True,
                    "annotations": {
                      "kubernetes.io/ingress.global-static-ip-name": argo_cd_address.name
                    }
                },
                "GKEbackendConfig": {
                    "spec": backendconfig_manifest,
                    "enabled": True
                },
                "service": {
                    "annotations": {
                        "cloud.google.com/backend-config":"{\"default\": \"argo-cd-argocd-server\"}"
                    }
                }
            },
        },
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider)
)

pulumi.export("Argo-cd url: http://", pulumi.Output.format(argo_cd_address.address))