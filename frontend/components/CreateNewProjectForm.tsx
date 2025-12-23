"use client";
import React, { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle, GitBranch, Zap, Layout } from "lucide-react";
import EnvFileEditor, { EnvVar } from "./EnvFileEditor";
import { useSession } from "next-auth/react";

const PROJECT_TYPES = [
  {
    key: "single",
    label: "Single Application",
    icon: <Layout className="text-violet-400" size={32} />,
  },
  {
    key: "microservice",
    label: "Microservice Application",
    icon: <Zap className="text-violet-400" size={32} />,
  },
];

export default function CreateNewProjectForm() {
  const { data: session } = useSession();
  const [name, setName] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [repoStatus, setRepoStatus] = useState<
    "idle" | "loading" | "success" | "error" | "connect"
  >("idle");
  const [envVars, setEnvVars] = useState<EnvVar[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Simulate backend check for repo access
  const checkRepoAccess = async (url: string) => {
    setRepoStatus("loading");
    setError("");
    try {
      // TODO: Replace with actual API call
      await new Promise((res) => setTimeout(res, 1200));
      // Simulate: if url contains 'private', ask to connect
      if (url.includes("private")) {
        setRepoStatus("connect");
      } else {
        setRepoStatus("success");
      }
    } catch {
      setRepoStatus("error");
      setError("Could not access repository.");
    }
  };

  const handleRepoBlur = () => {
    if (repoUrl && repoUrl.startsWith("http")) {
      checkRepoAccess(repoUrl);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");

    // Check if user is authenticated
    if (!session?.backendToken) {
      setError("Please sign in to create a project.");
      setSubmitting(false);
      return;
    }

    try {
      // Convert envVars array to object: [{key, value}] -> {key: value}
      const envVariables: Record<string, string> = {};
      envVars.forEach((env) => {
        if (env.key.trim()) {
          envVariables[env.key.trim()] = env.value;
        }
      });

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/deploy/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session.backendToken}`,
          },
          body: JSON.stringify({
            project_name: name,
            github_url: repoUrl,
            env_variables: envVariables,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to create project");
      }

      const data = await response.json();
      // Redirect to the new project page
      window.location.href = `/dashboard/project/${data.project_id}`;
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create project."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="space-y-6" onSubmit={handleSubmit}>
      <div>
        <label className="block text-sm font-medium mb-1">Project Name</label>
        <input
          type="text"
          className="w-full px-3 py-2 rounded bg-slate-800 text-white border border-slate-700 focus:outline-none"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">
          GitHub Repository URL
        </label>
        <div className="relative">
          <input
            type="url"
            className="w-full px-3 py-2 rounded bg-slate-800 text-white border border-slate-700 focus:outline-none"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            onBlur={handleRepoBlur}
            required
          />
          {repoStatus === "loading" && (
            <span className="absolute right-3 top-2">
              <Zap className="animate-spin text-violet-400" size={20} />
            </span>
          )}
          {repoStatus === "success" && (
            <span className="absolute right-3 top-2">
              <CheckCircle className="text-green-400" size={20} />
            </span>
          )}
          {repoStatus === "connect" && (
            <span className="absolute right-3 top-2">
              <GitBranch className="text-yellow-400" size={20} />
            </span>
          )}
        </div>
        {repoStatus === "connect" && (
          <div className="text-yellow-400 text-xs mt-1">
            Repository is private. Please connect with GitHub.
          </div>
        )}
        {repoStatus === "error" && (
          <div className="text-red-400 text-xs mt-1">{error}</div>
        )}
      </div>

      {/* EnvFileEditor section */}
      <EnvFileEditor value={envVars} onChange={setEnvVars} />

      <Button
        type="submit"
        className="w-full mt-6"
        disabled={submitting || !name || !repoUrl}
      >
        {submitting ? (
          <span className="flex items-center justify-center gap-2">
            <Zap className="animate-spin" size={18} /> Deploying...
          </span>
        ) : (
          "Deploy"
        )}
      </Button>
      {error && <div className="text-red-400 text-xs mt-2">{error}</div>}
    </form>
  );
}
