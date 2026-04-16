'use client';

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Card } from "../ui/card";
import { Button } from "../ui/button";
import { Rocket } from "lucide-react";
import { DeploymentPlanEditor } from "./DeploymentPlanEditor";
import { DetailedProject } from "@/types/project";

interface PlanReviewViewProps {
  project: DetailedProject;
}

export default function PlanReviewView({ project }: PlanReviewViewProps) {
  const { data: session } = useSession();
  const router = useRouter();
  const [localPlan, setLocalPlan] = useState<any>(project.deployment_plan ?? null);
  const [planStatus, setPlanStatus] = useState<string | null>(project.plan_status ?? null);
  const [startingDeploy, setStartingDeploy] = useState(false);

  const projectId = project.project_id;

  useEffect(() => {
    setLocalPlan(project.deployment_plan ?? null);
    setPlanStatus(project.plan_status ?? null);
  }, [project]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (planStatus === "generating") {
      interval = setInterval(async () => {
        if (!session?.backendToken) return;
        try {
          const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/projects/${projectId}/plan`, {
            headers: {
              Authorization: `Bearer ${session.backendToken}`,
            },
          });
          if (res.ok) {
            const data = await res.json();
            setPlanStatus(data.status);
            if (data.status === "ready" || data.plan) {
              setLocalPlan(data.plan);
            }
          }
        } catch (err) {
          console.error("Error polling plan", err);
        }
      }, 3000);
    }

    return () => clearInterval(interval);
  }, [planStatus, projectId, session?.backendToken]);

  const handlePlanSave = async (updatedPlan: any) => {
    setLocalPlan(updatedPlan);
    setPlanStatus("ready");

    if (!session?.backendToken) return;
    try {
      await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/projects/${projectId}/plan`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.backendToken}`,
        },
        body: JSON.stringify(updatedPlan),
      });
    } catch (err) {
      console.error("Error saving plan", err);
    }
  };

  const handleStartDeployment = async () => {
    if (!session?.backendToken) return;
    setStartingDeploy(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/projects/${projectId}/deploy`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.backendToken}`,
        },
      });
      if (res.ok) {
        setPlanStatus("approved");
        router.push(`/dashboard/project/${projectId}/deploy`);
      } else {
        console.error("Failed to start deployment");
      }
    } catch (err) {
      console.error("Error starting deployment", err);
    } finally {
      setStartingDeploy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-3xl font-bold text-white">Deployment Plan</h1>
        <p className="text-sm text-slate-400">
          Review and edit the plan before approving deployment.
        </p>
      </div>

      {planStatus === "generating" && !localPlan && (
        <Card className="p-0 rounded-xl border border-violet-600/50 bg-slate-900/80 text-slate-100 shadow-lg overflow-hidden">
          <div className="px-8 py-12 flex flex-col items-center justify-center gap-6">
            <div className="relative">
              <div className="w-16 h-16 rounded-full border-4 border-violet-900/30 border-t-violet-500 animate-spin"></div>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-8 h-8 rounded-full bg-violet-500/20 animate-pulse"></div>
              </div>
            </div>

            <div className="text-center space-y-2">
              <h3 className="text-xl font-semibold text-white">Analyzing Repository</h3>
              <p className="text-slate-400 text-sm max-w-md">
                We are detecting components, infrastructure, and connections to build a
                deployment plan.
              </p>
            </div>

            <div className="flex flex-col gap-3 w-full max-w-sm mt-2">
              {[
                "Scanning project structure",
                "Identifying services & components",
                "Detecting infrastructure dependencies",
                "Mapping connections & ports",
                "Generating deployment plan",
              ].map((step, i) => (
                <div key={step} className="flex items-center gap-3 text-sm">
                  <div
                    className={`w-2 h-2 rounded-full ${i < 2 ? "bg-violet-500" : "bg-slate-700"} ${
                      i === 1 ? "animate-pulse" : ""
                    }`}
                  ></div>
                  <span className={i < 2 ? "text-slate-300" : "text-slate-600"}>{step}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}

      {localPlan && (
        <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/50 shadow-lg">
          <div className="bg-gradient-to-r from-violet-900/50 to-slate-900/50 border-b border-violet-600/30 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-violet-500 animate-pulse"></div>
              <h3 className="text-lg font-semibold text-white">Deployment Plan</h3>
              <span className="px-2 py-0.5 text-xs font-medium text-violet-400 bg-violet-900/30 rounded-full border border-violet-600/30">
                {planStatus === "approved" ? "Approved" : "Pending Review"}
              </span>
            </div>
          </div>

          <div className="w-full relative" style={{ height: "600px" }}>
            <DeploymentPlanEditor plan={localPlan} projectId={projectId} onSave={handlePlanSave} />
          </div>

          <div className="bg-slate-900/80 border-t border-slate-800 p-4 flex justify-end">
            <Button
              onClick={handleStartDeployment}
              disabled={startingDeploy}
              className="bg-violet-600 text-white hover:bg-violet-700 font-semibold shadow-lg shadow-violet-900/20"
            >
              <Rocket className="w-4 h-4 mr-2" />
              {startingDeploy ? "Starting Deployment..." : "Approve Plan & Start Deployment"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
