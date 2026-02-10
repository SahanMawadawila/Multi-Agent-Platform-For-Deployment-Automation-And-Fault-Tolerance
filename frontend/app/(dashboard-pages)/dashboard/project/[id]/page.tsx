"use client";

import ProjectOverview from "@/components/single-project/ProjectOverview";
import DeploymentsTable from "@/components/single-project/DeploymentsTable";
import SettingsTabContent from "@/components/single-project/SettingsTabContent";
import EnvironmentVariableTab from "@/components/single-project/EnvironmentVariableTab";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import { DetailedProject } from "@/types/project";
import { TerminalSocketProvider } from "@/components/single-project/TerminalSocketContext";



async function fetchProjectDetails(projectId: string, accessToken: string): Promise<DetailedProject> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/projects/${projectId}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
  });

  if (!res.ok) {
    throw new Error('Failed to fetch project details');
  }

  return await res.json() as DetailedProject;
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
  const [activeTab, setActiveTab] = useState<string>("overview");

  const { data } = useSession();
  const token = data?.backendToken;

  useEffect(() => {
    if (!token) return;
    if (!projectId) return;

    fetchProjectDetails(projectId, token)
      .then(data => {
        setProjectData(data);
      })
      .catch(err => {
        console.error('Error fetching project details:', err);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [token, projectId]);
  const projectName = `Project ${projectId ?? ""}`; // Placeholder for project name

  if (isLoading || !projectData) {
    return <ProjectPageSkeleton />;
  }


  return (
    <TerminalSocketProvider projectId={projectId || ""} accessToken={token || ""}>
      <div className="space-y-8">

        {/* Page Header */}
        <h1 className="text-3xl font-bold text-white border-b border-slate-800 pb-4">
          {projectData.project_name}
        </h1>

        <div className="w-full">

          <Tabs defaultValue="overview" className="w-full" onValueChange={setActiveTab} value={activeTab} >
            <TabsList>
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="deployments">Deployments</TabsTrigger>
              <TabsTrigger value="environment">Environment</TabsTrigger>
              <TabsTrigger value="settings">Settings</TabsTrigger>
            </TabsList>
            <TabsContent value="overview" forceMount={true} hidden={activeTab !== "overview"}>
              <ProjectOverview project={projectData} />
            </TabsContent>
            <TabsContent value="deployments" >
              <DeploymentsTable projectId={projectId || ""} />
            </TabsContent>
            <TabsContent value="environment">
              <EnvironmentVariableTab projectId={projectId || ""} initialEnvVars={projectData.env_vars} />
            </TabsContent>
            <TabsContent value="settings">
              <SettingsTabContent project={projectData} />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </TerminalSocketProvider>
  );
}