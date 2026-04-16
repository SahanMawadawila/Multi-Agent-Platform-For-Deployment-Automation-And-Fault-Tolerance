"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useSession } from "next-auth/react";
import { DetailedProject } from "@/types/project";
import DeploymentExecutionView from "@/components/single-project/DeploymentExecutionView";
import { Skeleton } from "@/components/ui/skeleton";
import { TerminalSocketProvider } from "@/components/single-project/TerminalSocketContext";

async function fetchProjectDetails(projectId: string, accessToken: string): Promise<DetailedProject> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/projects/${projectId}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    throw new Error("Failed to fetch project details");
  }

  return (await res.json()) as DetailedProject;
}

function DeployPageSkeleton() {
  return (
    <div className="space-y-8">
      <div className="border-b border-slate-800 pb-4">
        <Skeleton className="h-10 w-64 bg-slate-800" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Skeleton className="h-[360px] w-full bg-slate-800 lg:col-span-2" />
        <Skeleton className="h-[360px] w-full bg-slate-800" />
      </div>
    </div>
  );
}

export default function ProjectDeployPage() {
  const { id } = useParams();
  const projectId: string | undefined = Array.isArray(id) ? id[0] : id;
  const [projectData, setProjectData] = useState<DetailedProject | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const { data } = useSession();
  const token = data?.backendToken;

  useEffect(() => {
    if (!token || !projectId) return;

    fetchProjectDetails(projectId, token)
      .then((project) => {
        setProjectData(project);
      })
      .catch((err) => {
        console.error("Error fetching project details:", err);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [token, projectId]);

  if (isLoading || !projectData) {
    return <DeployPageSkeleton />;
  }

  return (
    <TerminalSocketProvider projectId={projectId || ""} accessToken={token || ""}>
      <DeploymentExecutionView project={projectData} />
    </TerminalSocketProvider>
  );
}
