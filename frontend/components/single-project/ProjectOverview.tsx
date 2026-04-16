'use client';

import Link from "next/link";
import { CheckCircle, Clock, ExternalLink, GitCommit, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Card } from "../ui/card";
import { Button } from "../ui/button";
import { DetailedProject } from "@/types/project";

interface CurrentDeployment {
    build_id: number;
    build_version: string;
    build_date: string;
    build_status: string;
    duration?: number;
    commit_id?: string;
    is_current: boolean;
}

interface ProjectOverviewProps {
    project: DetailedProject;
}

const getStatusIcon = (status: string) => {
    switch (status) {
        case 'success':
        case 'Success':
            return <CheckCircle size={16} className="text-green-400" />;
        case 'failed':
        case 'Failed':
            return <XCircle size={16} className="text-red-400" />;
        case 'in_process':
        case 'Building':
            return <Clock size={16} className="text-yellow-400 animate-spin" />;
        default:
            return <GitCommit size={16} className="text-slate-500" />;
    }
};

const formatDuration = (seconds?: number) => {
    if (!seconds) return '—';
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
};

const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
};

export default function ProjectOverview({ project }: ProjectOverviewProps) {
    const { data: session } = useSession();
    const [currentDeployment, setCurrentDeployment] = useState<CurrentDeployment | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchCurrentDeployment = async () => {
            if (!session?.backendToken) return;

            try {
                const res = await fetch(
                    `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/projects/${project.project_id}/current-deployment`,
                    {
                        headers: {
                            'Authorization': `Bearer ${session.backendToken}`,
                            'Content-Type': 'application/json',
                        },
                    }
                );

                if (res.ok) {
                    const data = await res.json();
                    setCurrentDeployment(data.deployment);
                }
            } catch (error) {
                console.error('Failed to fetch current deployment:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchCurrentDeployment();
    }, [project.project_id, session?.backendToken]);

    return (
        <div className="space-y-6">
            <Card className="p-6 rounded-xl border border-slate-800 bg-slate-900/50">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                    <div className="space-y-2">
                        <h2 className="text-xl font-semibold text-white">Deployment Workflow</h2>
                        <p className="text-sm text-slate-400">
                            Generate a plan, review the diagram, then approve to launch the deployment console.
                        </p>
                        {project.plan_status && (
                            <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium text-violet-400 bg-violet-900/30 rounded-full border border-violet-600/30">
                                Plan status: {project.plan_status}
                            </span>
                        )}
                    </div>
                    <div className="flex flex-wrap gap-3">
                        <Button asChild className="bg-slate-800 text-white hover:bg-slate-700">
                            <Link href={`/dashboard/project/${project.project_id}/plan`}>Review Deployment Plan</Link>
                        </Button>
                        <Button asChild className="bg-violet-600 text-white hover:bg-violet-700">
                            <Link href={`/dashboard/project/${project.project_id}/deploy`}>Open Deployment Console</Link>
                        </Button>
                    </div>
                </div>
            </Card>

            {project.project_access_url && (
                <div className="flex items-center gap-2 p-3 bg-slate-900/30 border border-slate-800 rounded-lg">
                    <ExternalLink size={16} className="text-violet-400" />
                    <a
                        href={project.project_access_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-violet-400 hover:text-violet-300 transition-colors text-sm font-medium"
                    >
                        {project.project_access_url}
                    </a>
                </div>
            )}

            <div>
                <h2 className="text-xl font-bold text-white mb-4">Current Deployment</h2>

                {loading ? (
                    <Card className="p-4 rounded-lg border border-slate-800 bg-slate-900/50">
                        <div className="animate-pulse flex justify-between items-center">
                            <div className="h-4 bg-slate-700 rounded w-24"></div>
                            <div className="h-4 bg-slate-700 rounded w-16"></div>
                        </div>
                    </Card>
                ) : currentDeployment ? (
                    <Card className="p-4 rounded-lg border border-violet-600/50 ring-1 ring-violet-600/30 bg-slate-900/50 flex justify-between items-center flex-row w-full">
                        <div className="flex items-center gap-6">
                            <div className="flex items-center gap-2">
                                <GitCommit size={20} className="text-slate-400" />
                                <div>
                                    <p className="text-base font-semibold text-white">
                                        v{currentDeployment.build_version}
                                        <span className="ml-2 px-2 py-0.5 text-xs font-medium text-violet-400 bg-violet-900/30 rounded-full">Current</span>
                                    </p>
                                    <p className="text-xs text-slate-500 flex items-center gap-1 mt-1">
                                        <Clock size={12} /> {formatDate(currentDeployment.build_date)}
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div className="text-right flex items-center gap-6">
                            <div className="flex flex-col text-slate-400">
                                <span className="text-xs font-medium">Duration</span>
                                <span className="text-sm font-semibold text-white">{formatDuration(currentDeployment.duration)}</span>
                            </div>

                            <div className="flex flex-col text-right">
                                <div className="text-sm font-medium flex items-center gap-2 justify-end">
                                    {getStatusIcon(currentDeployment.build_status)}
                                    <span className={currentDeployment.build_status === 'success' ? 'text-green-400' : 'text-red-400'}>
                                        {currentDeployment.build_status}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </Card>
                ) : (
                    <Card className="p-4 rounded-lg border border-slate-800 bg-slate-900/50">
                        <p className="text-slate-400 text-sm text-center">No deployments yet</p>
                    </Card>
                )}
            </div>
        </div>
    );
}