import { CheckCircle, Clock, GitCommit, Play, XCircle } from "lucide-react";
import { ApplicationDiagramViewer } from "../diagram/application-diagram-viewer";
import { Card } from "../ui/card";
import ProjectTerminal from "./ProjectTerminal";

// --- Dummy Deployment Data ---
const deployments = [
    { id: 5, version: 'v1.5.0', date: '2025-11-25 10:30', status: 'Success', duration: '2 min', type: 'Current' },
    { id: 4, version: 'v1.4.1', date: '2025-11-20 18:45', status: 'Success', duration: '2 min', type: 'Previous' },
    { id: 3, version: 'v1.4.0', date: '2025-11-18 11:15', status: 'Failed', duration: '3 min', type: 'Previous' },
    { id: 2, version: 'v1.3.0', date: '2025-11-10 09:00', status: 'Success', duration: '1 min', type: 'Previous' },
];

// --- Status Icon Helper ---
const getStatusIcon = (status: string) => {
    switch (status) {
        case 'Success':
            return <CheckCircle size={16} className="text-green-400" />;
        case 'Failed':
            return <XCircle size={16} className="text-red-400" />;
        case 'Current':
            return <Play size={16} className="text-violet-400" />;
        default:
            return <GitCommit size={16} className="text-slate-500" />;
    }
};


export default function ProjectOverview() {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* -------------------- Left Panel: Deployments History (2/3 width) -------------------- */}
        <div className="lg:col-span-2 space-y-6">
          
          <ProjectTerminal />

        </div>

        {/* -------------------- Right Panel: Application Diagram (1/3 width) -------------------- */}
        <div className="lg:col-span-1 space-y-6">
            <h2 className="text-xl font-bold text-white">
                Application Topology
            </h2>
            <Card 
                className="h-[400px] p-0 rounded-xl border border-slate-800 bg-slate-900/50 text-slate-100 shadow-lg relative overflow-hidden"
                data-slot="card"
            >
                <ApplicationDiagramViewer />
            </Card>


            <div>
                <h2 className="text-xl font-bold text-white mb-4">
                    Current Deployment
                </h2>
                
                <Card 
                    className="p-4 rounded-lg border border-violet-600/50 ring-1 ring-violet-600/30 bg-slate-900/50 hover:border-violet-500/50 transition-colors cursor-pointer flex justify-between items-center flex-row w-full"
                >
                    {/* Left side: Version and Date */}
                    <div className="flex items-center gap-6">
                        {/* Version */}
                        <div className="flex items-center gap-2">
                            <GitCommit size={20} className="text-slate-400" />
                            <div>
                                <p className="text-base font-semibold text-white">
                                    {deployments[0].version}
                                    <span className="ml-2 px-2 py-0.5 text-xs font-medium text-violet-400 bg-violet-900/30 rounded-full">Current</span>
                                </p>
                                <p className="text-xs text-slate-500 flex items-center gap-1 mt-1">
                                    <Clock size={12} /> {deployments[0].date}
                                </p>
                            </div>
                        </div>
                    </div>
                    
                    {/* Right side: Status and Duration */}
                    <div className="text-right flex items-center gap-6">
                        {/* Duration */}
                        <div className="flex flex-col text-slate-400">
                            <span className="text-xs font-medium">Duration</span>
                            <span className="text-sm font-semibold text-white">{deployments[0].duration}</span>
                        </div>

                        {/* Status */}
                        <div className="flex flex-col text-right">
                            <div className="text-sm font-medium flex items-center gap-2 justify-end">
                                {getStatusIcon(deployments[0].status)}
                                <span className={deployments[0].status === 'Success' ? 'text-green-400' : 'text-red-400'}>
                                    {deployments[0].status}
                                </span>
                            </div>
                        </div>
                    </div>
                </Card>
            </div>
        </div>
      </div>
    );
}