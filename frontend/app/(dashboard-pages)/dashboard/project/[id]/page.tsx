import { ApplicationDiagramViewer } from '@/components/diagram/application-diagram-viewer';
import { Card } from '@/components/ui/card';
import { 
  GitCommit, 
  Clock, 
  CheckCircle, 
  XCircle,
  Play
} from 'lucide-react';

// --- Placeholder Component ---
// This is a placeholder for the external component that renders the application diagram.
/*const ApplicationDiagramViewer = () => (
    <div className="flex items-center justify-center p-8 bg-slate-900/50 border border-slate-700 rounded-xl min-h-[400px]">
        <span className="text-slate-500 italic text-center">
            &lt;ApplicationDiagramViewer /&gt; Placeholder:<br/> Application topology diagram will be rendered here.
        </span>
    </div>
);*/

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

// --- Main Page Component ---
export default function ProjectDetailPage({ params }: { params: { id: string } }) {
  const projectName = `Project ID:`;

  return (
    <div className="space-y-8">
      
      {/* Page Header */}
      <h1 className="text-3xl font-bold text-white border-b border-slate-800 pb-4">
        {projectName}
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* -------------------- Left Panel: Deployments History (2/3 width) -------------------- */}
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xl font-bold text-white">
              Deployment History
          </h2>
          
          <div className="space-y-4">
            {deployments.map((deployment) => (
              <Card 
                key={deployment.id}
                // Highlight the current deployment with violet border/ring
                className={`p-4 rounded-lg border bg-slate-900/50 hover:border-violet-500/50 transition-colors cursor-pointer flex justify-between items-center w-full ${deployment.type === 'Current' ? 'border-violet-600/50 ring-1 ring-violet-600/30' : 'border-slate-800'}`}
              >
                {/* Left side: Version and Date */}
                <div className="flex items-center gap-6">
                    {/* Version */}
                    <div className="flex items-center gap-2">
                        <GitCommit size={20} className="text-slate-400" />
                        <div>
                            <p className="text-base font-semibold text-white">
                                {deployment.version}
                                {deployment.type === 'Current' && <span className="ml-2 px-2 py-0.5 text-xs font-medium text-violet-400 bg-violet-900/30 rounded-full">Current</span>}
                            </p>
                            <p className="text-xs text-slate-500 flex items-center gap-1 mt-1">
                                <Clock size={12} /> {deployment.date}
                            </p>
                        </div>
                    </div>
                </div>
                
                {/* Right side: Status and Duration */}
                <div className="text-right flex items-center gap-6">
                    {/* Duration */}
                    <div className="flex flex-col text-slate-400">
                        <span className="text-xs font-medium">Duration</span>
                        <span className="text-sm font-semibold text-white">{deployment.duration}</span>
                    </div>

                    {/* Status */}
                    <div className="flex flex-col text-right">
                        <div className="text-sm font-medium flex items-center gap-2 justify-end">
                            {getStatusIcon(deployment.status)}
                            <span className={deployment.status === 'Success' ? 'text-green-400' : 'text-red-400'}>
                                {deployment.status}
                            </span>
                        </div>
                    </div>
                </div>
              </Card>
            ))}
          </div>

        </div>

        {/* -------------------- Right Panel: Application Diagram (1/3 width) -------------------- */}
        <div className="lg:col-span-1 space-y-6">
            <h2 className="text-xl font-bold text-white">
                Application Topology
            </h2>
            <Card 
                className="p-0 rounded-xl border border-slate-800 bg-slate-900/50 text-slate-100 shadow-lg relative overflow-hidden"
                data-slot="card"
            >
                <ApplicationDiagramViewer />
            </Card>
        </div>
      </div>
    </div>
  );
}