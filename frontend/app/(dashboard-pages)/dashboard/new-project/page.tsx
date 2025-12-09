import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import ProjectList from '@/components/ProjectList'; // Import the new client component
import { 
  Plus, 
  GitBranch, 
  CheckCircle, 
  Zap
} from 'lucide-react';
import CreateNewProjectForm from '@/components/CreateNewProjectForm';

// --- Sub-Components ---

/**
 * 
 * @returns Meta: title and description for the New Project page
 */
export const metadata = {
  title: 'Create New Project - ToolX',
  description: 'Start a new project with ToolX\'s intelligent agents. Follow our simple 3-step guide to deploy your application effortlessly.',
};


export default function NewProjectPage() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-12 mt-8">
      
      {/* -------------------- Left Panel: Project List (Client Component) -------------------- */}
      <ProjectList /> 

      {/* -------------------- Right Panel: New Project Form -------------------- */}
        <div className="lg:col-span-3 space-y-6">
          <Card 
            className="p-8 rounded-xl border border-slate-800 bg-slate-900/50 text-slate-100 shadow-lg relative overflow-hidden min-h-[400px]"
            data-slot="card"
          >
            <h2 className="text-3xl font-bold tracking-tight text-white mb-4">
              <Plus className="inline-block text-violet-400 mr-2" size={24} /> 
              Create New Project
            </h2>
            {/* External form component */}
            <CreateNewProjectForm />
          </Card>
        </div>
    </div>
  );
}