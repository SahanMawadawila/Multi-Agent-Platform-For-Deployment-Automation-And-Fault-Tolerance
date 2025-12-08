"use client";

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { 
  Plus, 
  CheckCircle, 
  Clock, 
  Server,
  Code
} from 'lucide-react';
import Link from 'next/link';

// --- Dummy Data (to be replaced by API calls) ---
const projects = [
  { name: "Frontend Monolith", type: "Monolithic", status: "Live", uptime: "99.98%", icon: <Code size={16} />, color: "text-green-400" },
  { name: "Payments Microservice", type: "Microservice", status: "Degraded", uptime: "98.12%", icon: <Server size={16} />, color: "text-yellow-400" },
  { name: "Auth API", type: "Microservice", status: "Live", uptime: "100.00%", icon: <Server size={16} />, color: "text-green-400" },
  { name: "Marketing Site", type: "Monolithic", status: "Offline", uptime: "0.00%", icon: <Code size={16} />, color: "text-red-400" },
];

export default function ProjectList() {
  return (
    <div className="lg:col-span-1 space-y-6">
      <div className="flex justify-between items-center border-b border-slate-800 pb-4">
        <h2 className="text-xl font-bold text-white">Current Deployments</h2>
        <Button asChild>
          <Link href="/dashboard/new-project" className="h-9 px-4 text-sm flex items-center gap-2 inline-flex">
            <Plus size={16} /> Deploy New Project
          </Link>
        </Button>
      </div>

      <div className="space-y-4">
        {projects.map((project, index) => (
          <Card 
            key={index}
            className="p-4 rounded-lg border border-slate-800 bg-slate-900/50 hover:border-violet-500/50 transition-colors cursor-pointer flex justify-between items-center w-full"
          >
            <div className="flex items-center gap-4 w-full">
                {/* Left side: Icon | Name/Type (stacked) */}
                <div className="flex items-center gap-4">
                    {/* Icon */}
                    <div className="h-8 w-8 rounded-md bg-slate-800 flex items-center justify-center text-violet-400 shrink-0">
                        {project.icon}
                    </div>
                    {/* Name & Type (stacked) */}
                    <div>
                        <h3 className="text-base font-semibold text-white">{project.name}</h3>
                        <p className="text-xs text-slate-500">{project.type}</p>
                    </div>
                </div>
                
                {/* Right side: Status/Uptime (stacked) */}
                <div className="text-right ms-auto">
                    {/* Status */}
                    <div className={`text-sm font-medium flex items-center gap-1 justify-end ${project.color}`}>
                        <CheckCircle size={12} /> {project.status}
                    </div>
                    {/* Uptime */}
                    <div className="text-xs text-slate-500 flex items-center gap-1 mt-1 justify-end">
                        <Clock size={12} /> {project.uptime}
                    </div>
                </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}