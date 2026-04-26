"use client";

import {
  BarChart3,
  Clock3,
  Cpu,
  Layers3,
  MemoryStick,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type VitalSample = {
  vital_id: number;
  project_id: string;
  namespace: string;
  pod_name: string;
  pod_phase?: string | null;
  cpu_millicores: number;
  memory_mebibytes: number;
  probe_status?: string | null;
  probe_latency_ms?: number | null;
  sampled_at: string;
};

type VitalsResponse = {
  project_id: string;
  window_hours: number;
  sample_count: number;
  pod_count: number;
  totals: {
    cpu_millicores: number;
    memory_mebibytes: number;
  };
  latest: VitalSample[];
  samples: VitalSample[];
};

async function fetchVitals(projectId: string, token: string): Promise<VitalsResponse> {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/projects/${projectId}/vitals?hours=24`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    },
  );

  if (!res.ok) {
    throw new Error("Failed to fetch vitals");
  }

  return (await res.json()) as VitalsResponse;
}

function formatTimestamp(value: string) {
  const date = new Date(value);
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatMegabytes(value: number) {
  if (value >= 1024) {
    return `${(value / 1024).toFixed(1)} GiB`;
  }
  return `${value.toFixed(0)} MiB`;
}

function formatMillicores(value: number) {
  // Convert millicores to percentage (1000m = 100%)
  const percentage = (value / 10);
  if (percentage < 0.1) {
    return `${percentage.toFixed(2)}%`;
  }
  return `${percentage.toFixed(1)}%`;
}

function vitalsBadgeClass(phase?: string | null) {
  switch (phase) {
    case "Running":
      return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
    case "Pending":
      return "bg-amber-500/15 text-amber-300 border-amber-500/30";
    case "Failed":
    case "CrashLoopBackOff":
      return "bg-rose-500/15 text-rose-300 border-rose-500/30";
    default:
      return "bg-slate-800 text-slate-300 border-slate-700";
  }
}

function VitalsSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="space-y-3">
          <Skeleton className="h-9 w-72 bg-slate-800" />
          <Skeleton className="h-4 w-96 bg-slate-800" />
        </div>
        <Skeleton className="h-10 w-36 bg-slate-800" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-28 rounded-xl bg-slate-800" />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        <Skeleton className="h-[360px] rounded-xl bg-slate-800" />
        <Skeleton className="h-[360px] rounded-xl bg-slate-800" />
      </div>
    </div>
  );
}

export default function DeployVitalsPage() {
  const { id } = useParams();
  const projectId: string | undefined = Array.isArray(id) ? id[0] : id;
  const { data: session } = useSession();
  const token = session?.backendToken;

  const [vitals, setVitals] = useState<VitalsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !projectId) {
      return;
    }

    let active = true;
    const loadVitals = async () => {
      try {
        const data = await fetchVitals(projectId, token);
        if (!active) {
          return;
        }
        setVitals(data);
        setError(null);
        setLastUpdated(new Date().toLocaleTimeString());
      } catch (fetchError) {
        if (active) {
          setError(fetchError instanceof Error ? fetchError.message : "Failed to load vitals");
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    };

    loadVitals();
    const interval = setInterval(loadVitals, 10000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [projectId, token]);

  const timelineData = useMemo(() => {
    const grouped = new Map<
      string,
      {
        sampled_at: string;
        cpu_millicores: number;
        memory_mebibytes: number;
        pod_count: number;
      }
    >();

    for (const sample of vitals?.samples ?? []) {
      const key = sample.sampled_at;
      const entry = grouped.get(key) ?? {
        sampled_at: key,
        cpu_millicores: 0,
        memory_mebibytes: 0,
        pod_count: 0,
      };
      entry.cpu_millicores += sample.cpu_millicores;
      entry.memory_mebibytes += sample.memory_mebibytes;
      entry.pod_count += 1;
      grouped.set(key, entry);
    }

    return Array.from(grouped.values()).sort(
      (left, right) => new Date(left.sampled_at).getTime() - new Date(right.sampled_at).getTime(),
    );
  }, [vitals?.samples]);

  const latestPods = vitals?.latest ?? [];

  if (isLoading && !vitals) {
    return <VitalsSkeleton />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-slate-800 pb-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-violet-300">
            <BarChart3 size={18} />
            <span className="text-sm font-medium uppercase tracking-[0.24em]">Vitals</span>
          </div>
          <h1 className="text-3xl font-bold text-white">Cluster Vitals</h1>
          <p className="max-w-3xl text-sm text-slate-400">
            CPU and memory samples collected from the Kubernetes Metrics API for the active project namespace.
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <RefreshCw size={16} className="text-violet-300" />
          <span>{lastUpdated ? `Last updated ${lastUpdated}` : "Polling every 10 seconds"}</span>
        </div>
      </div>

      {error && (
        <Card className="border border-rose-500/30 bg-rose-500/10 p-4 text-rose-200">
          <div className="flex items-center gap-2 text-sm font-medium">
            <ShieldAlert size={16} />
            {error}
          </div>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="border border-slate-800 bg-slate-900/50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">Tracked Pods</p>
              <p className="mt-2 text-2xl font-bold text-white">{vitals?.pod_count ?? 0}</p>
            </div>
            <Layers3 className="text-violet-300" size={22} />
          </div>
        </Card>
        <Card className="border border-slate-800 bg-slate-900/50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">CPU Total</p>
              <p className="mt-2 text-2xl font-bold text-white">
                {formatMillicores(vitals?.totals.cpu_millicores ?? 0)}
              </p>
            </div>
            <Cpu className="text-violet-300" size={22} />
          </div>
        </Card>
        <Card className="border border-slate-800 bg-slate-900/50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">Memory Total</p>
              <p className="mt-2 text-2xl font-bold text-white">
                {formatMegabytes(vitals?.totals.memory_mebibytes ?? 0)}
              </p>
            </div>
            <MemoryStick className="text-violet-300" size={22} />
          </div>
        </Card>
        <Card className="border border-slate-800 bg-slate-900/50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">Samples</p>
              <p className="mt-2 text-2xl font-bold text-white">{vitals?.sample_count ?? 0}</p>
            </div>
            <Clock3 className="text-violet-300" size={22} />
          </div>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="border border-slate-800 bg-slate-900/50 p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">CPU Usage</h2>
              <p className="text-sm text-slate-400">Total CPU across all pods in the namespace</p>
            </div>
          </div>
          <div className="h-[320px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timelineData}>
                <defs>
                  <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.45} />
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="sampled_at" tickFormatter={formatTimestamp} stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" tickFormatter={(value) => `${(value / 10).toFixed(1)}%`} />
                <Tooltip
                  contentStyle={{ background: "#020617", border: "1px solid #334155" }}
                  labelFormatter={(value) => formatTimestamp(String(value))}
                  formatter={(value) => [formatMillicores(Number(value ?? 0)), "CPU"] as [string, string]}
                />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="cpu_millicores"
                  name="CPU"
                  stroke="#a855f7"
                  fill="url(#cpuGradient)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="border border-slate-800 bg-slate-900/50 p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">Memory Usage</h2>
              <p className="text-sm text-slate-400">Total memory across all pods in the namespace</p>
            </div>
          </div>
          <div className="h-[320px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timelineData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="sampled_at" tickFormatter={formatTimestamp} stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" tickFormatter={(value) => `${value} MiB`} />
                <Tooltip
                  contentStyle={{ background: "#020617", border: "1px solid #334155" }}
                  labelFormatter={(value) => formatTimestamp(String(value))}
                  formatter={(value) => [formatMegabytes(Number(value ?? 0)), "Memory"] as [string, string]}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="memory_mebibytes"
                  name="Memory"
                  stroke="#38bdf8"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card className="border border-slate-800 bg-slate-900/50 p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Latest Pod Snapshot</h2>
            <p className="text-sm text-slate-400">Per-pod status and current metrics from the most recent sample</p>
          </div>
        </div>

        <div className="overflow-hidden rounded-xl border border-slate-800">
          <div className="grid grid-cols-12 gap-2 bg-slate-950/70 px-4 py-3 text-xs font-medium uppercase tracking-[0.16em] text-slate-400">
            <div className="col-span-3">Pod</div>
            <div className="col-span-2">Phase</div>
            <div className="col-span-2">CPU</div>
            <div className="col-span-2">Memory</div>
            <div className="col-span-3">Sampled</div>
          </div>

          <div className="divide-y divide-slate-800">
            {latestPods.length === 0 ? (
              <div className="px-4 py-6 text-sm text-slate-400">No vitals samples available yet.</div>
            ) : (
              latestPods.map((pod) => (
                <div key={pod.vital_id} className="grid grid-cols-12 gap-2 px-4 py-4 text-sm text-slate-200">
                  <div className="col-span-3 font-medium text-white">{pod.pod_name}</div>
                  <div className="col-span-2">
                    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${vitalsBadgeClass(pod.pod_phase)}`}>
                      {pod.pod_phase ?? "Unknown"}
                    </span>
                  </div>
                  <div className="col-span-2">{formatMillicores(pod.cpu_millicores)}</div>
                  <div className="col-span-2">{formatMegabytes(pod.memory_mebibytes)}</div>
                  <div className="col-span-3 text-slate-400">{formatTimestamp(pod.sampled_at)}</div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="mt-4 text-xs text-slate-500">
          Request count is not shown because this slice only reads cluster metrics and does not depend on application-exposed telemetry.
        </div>
      </Card>
    </div>
  );
}