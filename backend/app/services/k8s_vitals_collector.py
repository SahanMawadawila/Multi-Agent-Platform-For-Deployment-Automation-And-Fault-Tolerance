import asyncio
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Iterable
from urllib.parse import quote_plus

import requests
from kubernetes import client, config
from sqlalchemy import delete, select

from app.database.database import SessionLocal
from app.config import settings
from app.models.deployment_vitals import DeploymentVital
from app.models.user_project import UserProject


def _parse_cpu_millicores(value: str) -> int:
    if not value:
        return 0
    if value.endswith("n"):
        return int(round(float(value[:-1]) / 1_000_000))
    if value.endswith("u"):
        return int(round(float(value[:-1]) / 1_000))
    if value.endswith("m"):
        return int(float(value[:-1]))
    return int(float(value) * 1000)


def _parse_memory_mebibytes(value: str) -> int:
    if not value:
        return 0

    memory_units = {
        "Ki": 1 / 1024,
        "Mi": 1,
        "Gi": 1024,
        "Ti": 1024 * 1024,
        "Pi": 1024 * 1024 * 1024,
        "Ei": 1024 * 1024 * 1024 * 1024,
    }

    match = re.fullmatch(r"([0-9.]+)([KMGTE]i)?", value)
    if match:
        magnitude = float(match.group(1))
        unit = match.group(2)
        if not unit:
          return int(round(magnitude / (1024 * 1024)))
        return int(round(magnitude * memory_units[unit]))

    return int(round(float(value) / (1024 * 1024)))


class K8sVitalsCollector:
    def __init__(self, interval_seconds: int = 30, retention_days: int = 7):
        self.interval_seconds = interval_seconds
        self.retention_days = retention_days
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._kube_config_loaded = False

    async def start(self):
        if not self.can_start():
            print("[Vitals] Kubernetes config not available; vitals collection is disabled in this environment.")
            return
        if self._task:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        self._stop_event.set()
        if self._task:
            await self._task
            self._task = None

    def _load_kube_config(self):
        if self._kube_config_loaded:
            return
        try:
            if settings.KUBECONFIG:
                config.load_kube_config(config_file=settings.KUBECONFIG)
            else:
                config.load_incluster_config()
        except Exception:
            if self._has_local_kubeconfig():
                kubeconfig_path = settings.KUBECONFIG or os.path.expanduser("~/.kube/config")
                config.load_kube_config(config_file=kubeconfig_path)
            else:
                raise
        self._kube_config_loaded = True

    @staticmethod
    def _has_local_kubeconfig() -> bool:
        kubeconfig_path = settings.KUBECONFIG or os.path.expanduser("~/.kube/config")
        return os.path.exists(kubeconfig_path)

    def can_start(self) -> bool:
        return bool(os.getenv("KUBERNETES_SERVICE_HOST")) or self._has_local_kubeconfig()

    async def _run(self):
        while not self._stop_event.is_set():
            try:
                await self.collect_once()
            except Exception as exc:
                print(f"[Vitals] collection failed: {exc}")

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue

    async def collect_once(self):
        async with SessionLocal() as session:
            result = await session.execute(select(UserProject.project_id))
            project_ids = [str(project_id) for (project_id,) in result.all()]

        if not project_ids:
            return

        records = await asyncio.to_thread(self._collect_namespace_metrics, project_ids)
        if not records:
            return

        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=self.retention_days)

        async with SessionLocal() as session:
            for record in records:
                session.add(DeploymentVital(**record))
            await session.commit()
            await session.execute(delete(DeploymentVital).where(DeploymentVital.sampled_at < cutoff))
            await session.commit()

    def _collect_namespace_metrics(self, namespaces: Iterable[str]):
        self._load_kube_config()
        sampled_at = datetime.utcnow()
        records = []

        cpu_series = self._query_prometheus_series(
            'sum(rate(container_cpu_usage_seconds_total{container!="",image!=""}[5m])) by (namespace,pod)'
        )
        memory_series = self._query_prometheus_series(
            'sum(container_memory_working_set_bytes{container!="",image!=""}) by (namespace,pod)'
        )
        pod_info_series = self._query_prometheus_series("kube_pod_info")
        pod_phase_series = self._query_prometheus_series('kube_pod_status_phase == 1')

        cpu_by_namespace_pod = {
            (item.get("namespace"), item.get("pod")): item.get("value", 0.0)
            for item in cpu_series
            if item.get("namespace") and item.get("pod")
        }
        memory_by_namespace_pod = {
            (item.get("namespace"), item.get("pod")): item.get("value", 0.0)
            for item in memory_series
            if item.get("namespace") and item.get("pod")
        }
        phase_by_namespace_pod = {
            (item.get("namespace"), item.get("pod")): item.get("phase")
            for item in pod_phase_series
            if item.get("namespace") and item.get("pod") and item.get("phase")
        }
        pod_info_by_namespace_pod = {
            (item.get("namespace"), item.get("pod"))
            for item in pod_info_series
            if item.get("namespace") and item.get("pod")
        }

        for namespace in namespaces:
            pod_names = {
                pod_name
                for (series_namespace, pod_name) in cpu_by_namespace_pod.keys()
                | memory_by_namespace_pod.keys()
                | phase_by_namespace_pod.keys()
                | pod_info_by_namespace_pod
                if series_namespace == namespace
            }
            if not pod_names:
                continue

            for pod_name in pod_names:
                cpu_cores = cpu_by_namespace_pod.get((namespace, pod_name), 0.0)
                memory_bytes = memory_by_namespace_pod.get((namespace, pod_name), 0.0)

                records.append(
                    {
                        "project_id": namespace,
                        "namespace": namespace,
                        "pod_name": pod_name,
                        "pod_phase": phase_by_namespace_pod.get((namespace, pod_name)),
                        "cpu_millicores": int(round(cpu_cores * 1000)),
                        "memory_mebibytes": int(round(memory_bytes / (1024 * 1024))),
                        "probe_status": None,
                        "probe_latency_ms": None,
                        "sampled_at": sampled_at,
                    }
                )

        return records

    def _query_prometheus_series(self, query: str) -> list[dict[str, object]]:
        self._load_kube_config()
        
        # Check if running in-cluster or locally with port-forward
        in_cluster = bool(os.getenv("KUBERNETES_SERVICE_HOST"))
        
        if in_cluster:
            return self._query_prometheus_via_k8s_proxy(query)
        else:
            return self._query_prometheus_via_direct_http(query)

    def _query_prometheus_via_direct_http(self, query: str) -> list[dict[str, object]]:
        """Query Prometheus directly via HTTP (for local dev with port-forward)."""
        url = f"http://localhost:{settings.PROMETHEUS_SERVICE_PORT}/api/v1/query"
        params = {"query": query}
        
        try:
            response = requests.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            print(f"[Vitals] unable to query Prometheus via direct HTTP: {exc}")
            return []

        return self._parse_prometheus_response(payload)

    def _query_prometheus_via_k8s_proxy(self, query: str) -> list[dict[str, object]]:
        """Query Prometheus via Kubernetes API proxy (for in-cluster)."""
        core_api = client.CoreV1Api()
        service_name = settings.PROMETHEUS_SERVICE
        path = f"api/v1/query?query={quote_plus(query)}"

        try:
            response = core_api.connect_get_namespaced_service_proxy_with_path(
                name=service_name,
                namespace=settings.PROMETHEUS_NAMESPACE,
                path=path,
            )
        except Exception as exc:
            print(f"[Vitals] unable to query Prometheus via K8s proxy: {exc}")
            return []

        if isinstance(response, (bytes, bytearray)):
            response = response.decode("utf-8")

        if isinstance(response, str):
            payload = json.loads(response)
        else:
            payload = response

        return self._parse_prometheus_response(payload)

    @staticmethod
    def _parse_prometheus_response(payload: dict) -> list[dict[str, object]]:
        """Parse Prometheus API response into normalized records."""
        result: list[dict[str, object]] = []
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        for item in data.get("result", []):
            metric = item.get("metric", {})
            namespace = metric.get("namespace")
            pod_name = metric.get("pod")
            phase = metric.get("phase")
            if not pod_name:
                continue

            value = item.get("value")
            if isinstance(value, list) and len(value) >= 2:
                try:
                    result.append(
                        {
                            "namespace": namespace,
                            "pod": pod_name,
                            "phase": phase,
                            "value": float(value[1]),
                        }
                    )
                except (TypeError, ValueError):
                    continue

        return result


collector_instance = K8sVitalsCollector()