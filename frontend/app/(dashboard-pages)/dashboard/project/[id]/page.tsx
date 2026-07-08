"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useSession } from "next-auth/react";
import { DetailedProject } from "@/types/project";
import { Skeleton } from "@/components/ui/skeleton";
import ProjectOverview from "@/components/single-project/ProjectOverview";
import DeploymentsTable from "@/components/single-project/DeploymentsTable";
import EnvironmentVariableTab from "@/components/single-project/EnvironmentVariableTab";
import SettingsTabContent from "@/components/single-project/SettingsTabContent";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

async function fetchProjectDetails(
  projectId: string,
  accessToken: string,
): Promise<DetailedProject> {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/projects/${projectId}`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
    },
  );

  if (!res.ok) {
    throw new Error("Failed to fetch project details");
  }

  return (await res.json()) as DetailedProject;
}

function ProjectPageSkeleton() {
  return (
    <div className="space-y-8">
      {/* Page Header Skeleton */}
      <div className="border-b border-slate-800 pb-4">
        <Skeleton className="h-10 w-64 bg-slate-800" />
      </div>

      {/* Tab Triggers Skeleton (visual only, no tabs) */}
      <div className="flex gap-3">
        <Skeleton className="h-9 w-24 bg-slate-800" />
        <Skeleton className="h-9 w-28 bg-slate-800" />
        <Skeleton className="h-9 w-32 bg-slate-800" />
        <Skeleton className="h-9 w-28 bg-slate-800" />
      </div>

      {/* Content Skeletons mirroring page structure */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Skeleton className="h-[320px] w-full bg-slate-800 lg:col-span-2" />
        <Skeleton className="h-[320px] w-full bg-slate-800" />
      </div>

      {/* Secondary rows to hint at additional sections */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Skeleton className="h-48 w-full bg-slate-800 lg:col-span-2" />
        <Skeleton className="h-48 w-full bg-slate-800" />
      </div>
    </div>
  );
}

export default function ProjectDetailPage() {
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
    return <ProjectPageSkeleton />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold text-white">{projectData.project_name}</h1>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="bg-slate-900 border border-slate-800 mb-6">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="deployments">Deployments</TabsTrigger>
          <TabsTrigger value="environment">Environment</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview" className="mt-0 focus-visible:outline-none focus-visible:ring-0">
          <ProjectOverview project={projectData} />
        </TabsContent>
        
        <TabsContent value="deployments" className="mt-0 focus-visible:outline-none focus-visible:ring-0">
          <DeploymentsTable projectId={projectId} />
        </TabsContent>
        
        <TabsContent value="environment" className="mt-0 focus-visible:outline-none focus-visible:ring-0">
          <EnvironmentVariableTab projectId={projectId} />
        </TabsContent>
        
        <TabsContent value="settings" className="mt-0 focus-visible:outline-none focus-visible:ring-0">
          <SettingsTabContent project={projectData} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
