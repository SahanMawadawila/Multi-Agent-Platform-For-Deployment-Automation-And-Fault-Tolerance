"use client";
import React, { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle, GitBranch, Zap, Layout } from "lucide-react";
import EnvFileEditor, { EnvVar } from "./EnvFileEditor";

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
  const [name, setName] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [repoStatus, setRepoStatus] = useState<
    "idle" | "loading" | "success" | "error" | "connect"
  >("idle");
  const [projectType, setProjectType] = useState<
    "single" | "microservice" | null
  >(null);
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
    try {
      // TODO: Replace with actual API call
      await new Promise((res) => setTimeout(res, 1500));
      // Simulate redirect
      window.location.href = "/dashboard/project/123";
      // Example payload:
      // {
      //   name,
      //   repoUrl,
      //   projectType,
      //   env: envVars // [{key, value}, ...]
      // }
    } catch {
      setError("Failed to create project.");
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
        disabled={submitting || !name || !repoUrl || !projectType}
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
