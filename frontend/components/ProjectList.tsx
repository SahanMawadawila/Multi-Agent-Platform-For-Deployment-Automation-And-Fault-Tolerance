"use client";

import { Card } from "@/components/ui/card";
import { CheckCircle, Server } from "lucide-react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Skeleton } from "./ui/skeleton";
import { ProjectSimple } from "@/types/project";
import { PaginationInfo } from "@/types/pagination";

async function loadProjects(
  accessToken: string,
  page: number = 1,
  limit: number = 40,
) {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/projects?page=${page}&limit=${limit}`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
    },
  );

  if (!res.ok) {
    throw new Error("Failed to fetch projects");
  }

  return (await res.json()) as {
    projects: ProjectSimple[];
    pagination: PaginationInfo;
  };
}

function getProjectStateColor(status: string) {
  switch (status) {
    case "Live":
      return "text-green-400";
    case "Degraded":
      return "text-yellow-400";
    case "Offline":
      return "text-red-400";
    default:
      return "text-gray-400";
  }
}

function ProjectCardSkeleton() {
  return (
    <Card className="p-4 rounded-lg border border-slate-800 bg-slate-900/50 hover:border-violet-500/50 transition-colors cursor-pointer flex justify-between items-center w-full">
      <div className="flex items-center gap-4 w-full">
        {/* Left side: Icon | Name/Type (stacked) */}
        <div className="flex items-center gap-4">
          {/* Icon */}
          <div className="h-8 w-8 rounded-md bg-slate-800 flex items-center justify-center text-violet-400 shrink-0">
            <Skeleton className="h-4 w-4 " />
          </div>
          {/* Name & Type (stacked) */}
          <div>
            <Skeleton className="h-4 w-32 mb-2" />
            <Skeleton className="h-3 w-24" />
          </div>
        </div>

        {/* Right side: Status/Uptime (stacked) */}
        <div className="text-right ms-auto">
          <Skeleton className="h-4 w-full min-w-8 mb-2" />
        </div>
      </div>
    </Card>
  );
}

export default function ProjectList() {
  const [projects, setProjects] = useState<ProjectSimple[]>([]);
  const [projectsLoading, setProjectsLoading] = useState<boolean>(true);
  const [page, setPage] = useState<number>(1);
  const [hasMore, setHasMore] = useState<boolean>(false);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const { data } = useSession();
  const token = data?.backendToken;

  useEffect(() => {
    console.log("Loading projects with token:", token);
    if (!token) return;
    setProjectsLoading(true);
    setPage(1);
    loadProjects(token, 1)
      .then((data) => {
        setProjects(data.projects);
        setHasMore(data.pagination.page < data.pagination.total_pages);
      })
      .catch((err) => {
        console.error("Error loading projects:", err);
      })
      .finally(() => {
        setProjectsLoading(false);
      });
  }, [token]);

  const handleLoadMore = async () => {
    if (!token || loadingMore) return;
    setLoadingMore(true);
    const nextPage = page + 1;
    try {
      const data = await loadProjects(token, nextPage);
      setProjects((prev) => [...prev, ...data.projects]);
      setPage(nextPage);
      setHasMore(data.pagination.page < data.pagination.total_pages);
    } catch (err) {
      console.error("Error loading more projects:", err);
    } finally {
      setLoadingMore(false);
    }
  };

  return (
    <div className="lg:col-span-1 space-y-6">
      <div className="flex justify-between items-center border-b border-slate-800 pb-4">
        <h2 className="text-xl font-bold text-white">Current Deployments</h2>
      </div>

      <div className="space-y-4 max-h-[calc(100vh-12rem)] overflow-y-auto pr-2 overflow-x-hidden">
        {projectsLoading && (
          <>
            <ProjectCardSkeleton />
            <ProjectCardSkeleton />
            <ProjectCardSkeleton />
            <ProjectCardSkeleton />
          </>
        )}
        {projects.map((project, index) => (
          <Link
            href={`/dashboard/project/${project.project_id}/plan`}
            key={index}
            className="block"
          >
            <Card className="p-4 rounded-lg border border-slate-800 bg-slate-900/50 hover:border-violet-500/50 transition-colors cursor-pointer flex justify-between items-center w-full">
              <div className="flex items-center gap-4 w-full">
                {/* Left side: Icon | Name/Type (stacked) */}
                <div className="flex items-center gap-4">
                  {/* Icon */}
                  <div className="h-8 w-8 rounded-md bg-slate-800 flex items-center justify-center text-violet-400 shrink-0">
                    <Server size={16} />,
                  </div>
                  {/* Name & Type (stacked) */}
                  <div>
                    <h3 className="text-base font-semibold text-white">
                      {project.project_name}
                    </h3>
                    <p className="text-xs text-slate-500">
                      {project.domain_name || "No domain"}
                    </p>
                  </div>
                </div>

                {/* Right side: Status/Uptime (stacked) */}
                <div className="text-right ms-auto">
                  {/* Status */}
                  <div
                    className={`text-sm font-medium flex items-center gap-1 justify-end ${getProjectStateColor(project.status || "")}`}
                  >
                    <CheckCircle size={12} /> {project.status}
                  </div>
                  {/* Uptime
                      <div className="text-xs text-slate-500 flex items-center gap-1 mt-1 justify-end">
                          <Clock size={12} /> {project.uptime}
                      </div> */}
                </div>
              </div>
            </Card>
          </Link>
        ))}

        {hasMore && (
          <div className="flex justify-center pt-2 pb-4">
            <button
              onClick={handleLoadMore}
              disabled={loadingMore}
              className="text-sm font-medium text-violet-400 hover:text-violet-300 disabled:opacity-50 transition-colors"
            >
              {loadingMore ? "Loading..." : "Load More"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
