"use client";
import ProjectOverview from "@/components/single-project/ProjectOverview";
import DeploymentsTable from "@/components/single-project/DeploymentsTable";
import SettingsTabContent from "@/components/single-project/SettingsTabContent";
import EnvironmentVariableTab from "@/components/single-project/EnvironmentVariableTab";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

// --- Main Page Component ---
export default function ProjectDetailPage({ params }: { params: { id: string } }) {
  const projectName = `Project ABC`;

  return (
    <div className="space-y-8">
      
      {/* Page Header */}
      <h1 className="text-3xl font-bold text-white border-b border-slate-800 pb-4">
        {projectName}
      </h1>

      <div className="w-full">
        <Tabs defaultValue="overview" className="w-full">
            <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="deployments">Deployments</TabsTrigger>
                <TabsTrigger value="environment">Environment</TabsTrigger>
                <TabsTrigger value="settings">Settings</TabsTrigger>
            </TabsList>
            <TabsContent value="overview">
              <ProjectOverview />
            </TabsContent>
            <TabsContent value="deployments">
              <DeploymentsTable />
            </TabsContent>
            <TabsContent value="environment">
              <EnvironmentVariableTab />
            </TabsContent>
            <TabsContent value="settings">
              <SettingsTabContent />
            </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}