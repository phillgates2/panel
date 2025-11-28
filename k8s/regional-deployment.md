# Regional Deployment Strategy
# Deploy Panel in multiple regions for low-latency access

# US East
kubectl apply -f k8s/deployment.yaml --context=us-east-cluster
kubectl apply -f k8s/postgres.yaml --context=us-east-cluster

# EU West
kubectl apply -f k8s/deployment.yaml --context=eu-west-cluster
kubectl apply -f k8s/postgres-replica.yaml --context=eu-west-cluster

# Asia Pacific
kubectl apply -f k8s/deployment.yaml --context=ap-southeast-cluster
kubectl apply -f k8s/postgres-replica.yaml --context=ap-southeast-cluster

# Global Load Balancer (AWS Global Accelerator or Cloudflare Load Balancing)
# Routes traffic to nearest region based on latency