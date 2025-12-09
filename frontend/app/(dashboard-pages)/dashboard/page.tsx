import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import ProjectList from '@/components/ProjectList'; // Import the new client component
import { 
  Plus, 
  GitBranch, 
  CheckCircle, 
  Zap
} from 'lucide-react';
import Link from 'next/link';

// --- Sub-Components ---

// Step Guide Item (kept here as it's static/server-rendered content)
const GuideStep = ({ icon, title, description, isLast = false, step }: { icon: React.ReactNode, title: string, description: string, isLast?: boolean, step: number }) => (
    <div className="flex">
        <div className="flex flex-col items-center mr-4">
            <div className="w-8 h-8 rounded-full bg-violet-600 text-white flex items-center justify-center font-bold">
                {step}
            </div>
            {!isLast && <div className="w-px h-full bg-slate-700 mt-2 mb-2" />}
        </div>
        <div className="pb-6">
            <div className="flex items-center gap-2 mb-1 text-white font-semibold">
                {icon}
                <h3 className="text-lg">{title}</h3>
            </div>
            <p className="text-slate-400 text-sm">{description}</p>
        </div>
    </div>
);

// --- Main Page (Server Component) ---

export default function DashboardPage() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-12 mt-8">
      
      {/* -------------------- Left Panel: Project List (Client Component) -------------------- */}
      <ProjectList /> 

      {/* -------------------- Right Panel: Getting Started Guide (Server Component) -------------------- */}
      <div className="lg:col-span-3 space-y-6">
        <Card 
          className="p-8 rounded-xl border border-slate-800 bg-slate-900/50 text-slate-100 shadow-lg relative overflow-hidden min-h-[400px]"
          data-slot="card"
        >
          {/* Abstract background visualization (placeholder for "transparent vector graphics") */}
          <div className="absolute top-0 right-0 h-full w-full opacity-10 pointer-events-none">
            {/* Simple diagonal lines and dots to represent data flow/agents */}
            <div className="absolute top-1/4 left-1/4 h-3 w-3 rounded-full bg-violet-400 animate-pulse" />
            <div className="absolute top-3/4 right-1/3 h-40 w-0.5 bg-purple-500 rotate-45" />
            <div className="absolute bottom-1/4 left-1/3 h-2 w-2 rounded-full bg-violet-600" />
          </div>

          <div className="relative z-10">
            <h2 className="text-3xl font-bold tracking-tight text-white mb-4">
              <Zap className="inline-block text-violet-400 mr-2" size={24} /> 
              Get Started with Intelligent Agents
            </h2>
            <p className="text-lg text-slate-400 mb-8 max-w-2xl">
              Deploy your first application in just three simple steps. Our autonomous agents handle the rest.
            </p>

            {/* 3 Step Deployment Guide */}
            <div className="space-y-4">
              <GuideStep 
                step={1}
                icon={<Plus size={20} className="text-violet-400" />}
                title="Create a New Project"
                description="Define your project name and infrastructure requirements. No YAML files needed."
              />
              <GuideStep 
                step={2}
                icon={<GitBranch size={20} className="text-violet-400" />}
                title="Connect to GitHub"
                description="Link your repository. Our agents automatically configure webhooks for CI/CD."
              />
              <GuideStep 
                step={3}
                icon={<CheckCircle size={20} className="text-violet-400" />}
                title="Go Live Instantly"
                description="Your first build runs, and the intelligent agents deploy a fully fault-tolerant service."
                isLast={true}
              />
            </div>

            <Button asChild>
              <Link href="/dashboard/new-project" className="mt-6 h-12 px-8 text-base bg-violet-600 hover:bg-violet-500">
                Start 3-Step Deployment Now
              </Link>
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}