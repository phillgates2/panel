#!/bin/bash

install_optional_monitoring() {
    if [[ ${MONITORING:-false} != true ]]; then
        return
    fi

    log_info "Setting up monitoring with Prometheus & Grafana (Kubernetes/Helm)..."
    if ! command -v kubectl &> /dev/null || ! command -v helm &> /dev/null; then
        log_warning "kubectl/helm not found, skipping monitoring stack installation"
        return
    fi

    kubectl create namespace monitoring 2>/dev/null || log_warning "Monitoring namespace may already exist"

    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts || true
    helm repo add grafana https://grafana.github.io/helm-charts || true
    helm repo update || true

    helm install prometheus prometheus-community/prometheus --namespace monitoring 2>/dev/null || log_warning "Prometheus install may have failed or already exist"
    helm install grafana grafana/grafana --namespace monitoring 2>/dev/null || log_warning "Grafana install may have failed or already exist"

    log_success "Monitoring stack installation attempted (check your cluster for details)"
}
