"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useSession } from "next-auth/react";
import { Card } from "@/components/ui/card";
import { Terminal, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { DetailedProject } from "@/types/project";
import { Skeleton } from "@/components/ui/skeleton";

interface LogEntry {
  timestamp: string;
  line: string;
}

export default function ProjectLogsPage() {
  const { id } = useParams();
  const projectId: string | undefined = Array.isArray(id) ? id[0] : id;
  const [project, setProject] = useState<DetailedProject | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const { data: session } = useSession();
  const token = session?.backendToken;

  useEffect(() => {
    async function fetchDetails() {
      if (!token || !projectId) return;

      try {
        const [projectRes, logsRes] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/projects/${projectId}`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/projects/${projectId}/logs`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);

        if (projectRes.ok) {
          setProject(await projectRes.json());
        }

        if (logsRes.ok) {
          const logsData = await logsRes.json();
          // Parse Loki response format
          const formattedLogs: LogEntry[] = [];
          if (logsData.data && logsData.data.result) {
            logsData.data.result.forEach((stream: any) => {
              if (stream.values) {
                stream.values.forEach((val: any) => {
                  // val[0] is epoch nanoseconds, val[1] is the log line
                  const date = new Date(parseInt(val[0]) / 1e6);
                  formattedLogs.push({
                    timestamp: date.toISOString(),
                    line: val[1],
                  });
                });
              }
            });
            
            // Sort by timestamp
            formattedLogs.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
            setLogs(formattedLogs);
          }
        } else {
          setError("Failed to fetch logs data");
        }
      } catch (err: any) {
        setError(err.message || "Failed to load logs");
      } finally {
        setIsLoading(false);
      }
    }

    fetchDetails();
  }, [projectId, token]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="border-b border-slate-800 pb-4">
          <Skeleton className="h-10 w-64 bg-slate-800" />
        </div>
        <Skeleton className="h-[600px] w-full bg-slate-800" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-full">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-2">
            <Link 
              href={`/dashboard/project/${projectId}/deploy`}
              className="text-slate-400 hover:text-white transition-colors"
              title="Back to Deployment"
            >
              <ArrowLeft size={24} />
            </Link>
            Live Logs
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Viewing container logs for project: <strong className="text-violet-400">{project?.project_name || projectId}</strong>
          </p>
        </div>
        <div className="flex items-center text-sm px-3 py-1 bg-slate-800 rounded-md text-emerald-400">
          <span className="relative flex h-2 w-2 mr-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          Live Stream
        </div>
      </div>

      <Card className="h-[calc(100vh-250px)] min-h-[500px] flex flex-col overflow-hidden border-slate-800 bg-[#0d1117]">
        <div className="flex items-center gap-2 p-3 bg-slate-900 border-b border-slate-800 text-slate-400 text-xs font-mono uppercase tracking-wider">
          <Terminal size={14} className="text-violet-400" />
          Container Output
        </div>
        
        <div className="flex-1 p-4 overflow-y-auto font-mono text-sm leading-relaxed scroll-smooth text-slate-300">
          {error ? (
            <div className="text-red-400 flex items-center justify-center h-full">
              Failed to load logs: {error}
            </div>
          ) : logs.length === 0 ? (
            <div className="text-slate-500 flex flex-col items-center justify-center h-full">
              <Terminal size={48} className="mb-4 opacity-20" />
              <p>No deployment logs found for this project yet.</p>
              <p className="text-xs mt-2 opacity-60">Make sure your app is actively running.</p>
            </div>
          ) : (
            <div className="space-y-1">
              {logs.map((log, i) => (
                <div key={i} className="hover:bg-slate-800/50 px-2 rounded -mx-2 flex gap-4">
                  <span className="text-slate-600 shrink-0 w-48 truncate">
                    {new Date(log.timestamp).toLocaleString()}
                  </span>
                  <span className="break-all whitespace-pre-wrap text-slate-300">{log.line}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}