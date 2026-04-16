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
  const [components, setComponents] = useState<
    { name: string; path: string }[]
  >([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [envVarsMap, setEnvVarsMap] = useState<Record<string, EnvVar[]>>({});

  const analyzeRepo = async (url: string) => {
    setIsAnalyzing(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/github/analyze-repo/?repo_url=${encodeURIComponent(url)}`,
        {
          headers: {
            Authorization: `Bearer ${session?.backendToken}`,
          },
        },
      );
      if (response.ok) {
        const data = await response.json();
        if (data.components && data.components.length > 0) {
          setComponents(data.components);
        } else {
        }
      } else {
      }
    } catch (err) {
      console.error("Analysis failed:", err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Simulate backend check for repo access
  const checkRepoAccess = async (url: string) => {
    setRepoStatus("loading");
    setError("");
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/github/check-repo-accessible/?repo_url=${encodeURIComponent(url)}`,
        {
          headers: {
            Authorization: `Bearer ${session?.backendToken}`,
          },
        },
      );
      if (!response.ok) {
        throw new Error("Failed to check repository access");
      }

      const data = await response.json();

      // Since your GitHub repos are always accessible to the project (even if the API says otherwise),
      // we will always trigger analyzeRepo here regardless of the strict public/private accessible boolean
      analyzeRepo(url);

      if (data.is_accessible === true) {
        setRepoStatus("success");
      } else if (data.is_private === true) {
        // Repo exists but is private - show connect option
        setRepoStatus("connect");
        setError("Repository is private or requires authentication.");
      } else {
        // Repo might not exist or other error
        setRepoStatus("error");
        setError("Could not access repository. Please check the URL.");
      }
    } catch {
      setRepoStatus("error");
      setError("Could not access repository.");
    }
  };

  const RequestRepoAccess = async () => {
    try {
      // Step 1: Get repo access URL from backend
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/github/get-access-request-url/`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${session?.backendToken}`,
          },
        },
      );
      if (!resp.ok) {
        throw new Error("Failed to get repo access URL");
      }
      const data = await resp.json();
      const { access_request_url } = data;

      // Step 2: Redirect user to GitHub access request URL in new tab
      window.open(access_request_url, "_blank");
    } catch (err) {
      console.error("Error requesting repo access:", err);
    }
  };

  const handleRepoBlur = () => {
    if (repoUrl && repoUrl.startsWith("https://github.com")) {
      checkRepoAccess(repoUrl);
    } else {
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
      // Convert envVars array/map
      let envVariables: any = {};
      if (components.length > 1) {
        // Monorepo mode
        components.forEach((c) => {
          const compVars: Record<string, string> = {};
          (envVarsMap[c.path] || []).forEach((env) => {
            if (env.key.trim()) compVars[env.key.trim()] = env.value;
          });
          if (Object.keys(compVars).length > 0) {
            envVariables[c.path] = compVars;
          }
        });
      } else {
        // Single mode
        envVars.forEach((env) => {
          if (env.key.trim()) {
            envVariables[env.key.trim()] = env.value;
          }
        });
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/projects/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session.backendToken}`,
          },
          body: JSON.stringify({
            project_name: name,
            repository_url: repoUrl,
            env_vars: envVariables,
            trigger_deployment: true,
          }),
        },
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to create project");
      }

      const data = await response.json();
      // Redirect to the new project page
      window.location.href = `/dashboard/project/${data.project_id}/plan`;
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create project.",
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
            <Button
              type="button"
              size="sm"
              className="absolute right-1 top-1 h-8 bg-yellow-500 hover:bg-yellow-600 text-black"
              onClick={RequestRepoAccess}
            >
              Connect
            </Button>
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
      {isAnalyzing && (
        <div className="flex items-center gap-3 text-violet-400 p-4 border border-violet-900/50 bg-violet-900/10 rounded-lg animate-pulse">
          <Zap className="animate-spin" size={24} />
          <div>
            <div className="font-semibold">
              Analyzing repository structure...
            </div>
            <div className="text-xs opacity-80">
              Finding deployable components.
            </div>
          </div>
        </div>
      )}

      {!isAnalyzing && components.length > 1 ? (
        <div className="space-y-4">
          <label className="block text-sm font-medium mb-1 flex items-center gap-2">
            Monorepo Components ({components.length} detected)
          </label>
          <div className="space-y-4">
            {components.map((c) => (
              <div
                key={c.path}
                className="p-4 border border-slate-700 rounded-lg bg-slate-800/50"
              >
                <h4 className="text-sm font-medium mb-4 text-violet-300">
                  Environment variables for <strong>{c.path}</strong>
                </h4>
                <EnvFileEditor
                  value={envVarsMap[c.path] || []}
                  onChange={(vars) =>
                    setEnvVarsMap({ ...envVarsMap, [c.path]: vars })
                  }
                />
              </div>
            ))}
          </div>
        </div>
      ) : (
        !isAnalyzing && <EnvFileEditor value={envVars} onChange={setEnvVars} />
      )}

      <Button
        type="submit"
        className="w-full mt-6"
        disabled={submitting || !name || !repoUrl}
      >
        {submitting ? (
          <span className="flex items-center justify-center gap-2">
            <Zap className="animate-spin" size={18} /> Analyzing...
          </span>
        ) : (
          "Generate Deployment Plan"
        )}
      </Button>
      {error && <div className="text-red-400 text-xs mt-2">{error}</div>}
    </form>
  );
}
