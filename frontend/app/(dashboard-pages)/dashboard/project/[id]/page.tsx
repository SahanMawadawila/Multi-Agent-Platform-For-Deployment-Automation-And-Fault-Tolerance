"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";



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
  const router = useRouter();

  useEffect(() => {
    if (!projectId) return;
    router.replace(`/dashboard/project/${projectId}/plan`);
  }, [projectId, router]);

  return <ProjectPageSkeleton />;
}