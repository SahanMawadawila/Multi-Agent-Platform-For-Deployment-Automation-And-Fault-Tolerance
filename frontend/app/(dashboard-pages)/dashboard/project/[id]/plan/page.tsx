"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useSession } from "next-auth/react";
import { DetailedProject } from "@/types/project";
import PlanReviewView from "@/components/single-project/PlanReviewView";
import { Skeleton } from "@/components/ui/skeleton";

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

function PlanPageSkeleton() {
  return (
    <div className="space-y-8">
      <div className="border-b border-slate-800 pb-4">
        <Skeleton className="h-10 w-64 bg-slate-800" />
      </div>
      <Skeleton className="h-[600px] w-full bg-slate-800" />
    </div>
  );
}

export default function ProjectPlanPage() {
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
    return <PlanPageSkeleton />;
  }

  return <PlanReviewView project={projectData} />;
}
