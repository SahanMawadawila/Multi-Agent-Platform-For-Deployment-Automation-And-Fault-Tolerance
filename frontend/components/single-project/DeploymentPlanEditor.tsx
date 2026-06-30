import React, { useState, useEffect } from "react";
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  type EdgeMouseHandler,
} from "reactflow";
import "reactflow/dist/style.css";

import { PlanNode } from "./PlanNode";
import { ApplicationDetailPanel } from "./ApplicationDetailPanel";
import { InfrastructureDetailPanel } from "./InfrastructureDetailPanel";
import { ConnectionDetailPanel } from "./ConnectionDetailPanel";
import { infraRegistry } from "../../lib/infraRegistry";
import { Plus } from "lucide-react";

interface DeploymentPlanEditorProps {
  plan: any;
  projectId: string;
  onSave: (updatedPlan: any) => void;
}

const nodeTypes = {
  customNode: PlanNode,
};

export function DeploymentPlanEditor({
  plan,
  projectId,
  onSave,
}: DeploymentPlanEditorProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedComponentIndex, setSelectedComponentIndex] = useState<
    number | null
  >(null);
  const [selectedConnectionIndex, setSelectedConnectionIndex] = useState<
    number | null
  >(null);
  const [editablePlan, setEditablePlan] = useState<any>(plan);
  const [isAddMenuOpen, setIsAddMenuOpen] = useState(false);

  // Initialize map and nodes on plan load
  useEffect(() => {
    if (!editablePlan || !editablePlan.components) return;

    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];

    // Basic auto-layout positioning
    let xOffset = 100;
    let yOffset = 100;

    const appServiceNames: Record<string, string> = {};
    const serviceNameToComponent: Record<string, string> = {};

    editablePlan.components.forEach((comp: any) => {
      if (comp.type === "application") {
        appServiceNames[comp.name] = comp.name;
        serviceNameToComponent[comp.name] = comp.name;
      } else if (comp.type === "infrastructure") {
        serviceNameToComponent[comp.name] = comp.name;
      }
    });

    const resolveNodeId = (value: string) => {
      if (!value) return value;
      return serviceNameToComponent[value] || value;
    };

    editablePlan.components.forEach((comp: any, i: number) => {
      const nodeId = comp.name;
      newNodes.push({
        id: nodeId,
        type: "customNode",
        position: { x: xOffset, y: yOffset },
        data: {
          label: comp.name,
          type: comp.type,
          role: comp.role || comp.category,
          onSelect: () => {
            setSelectedComponentIndex(i);
            setSelectedConnectionIndex(null);
          },
        },
      });

      xOffset += 300;
      if (xOffset > 800) {
        xOffset = 100;
        yOffset += 200;
      }
    });

    editablePlan.connections?.forEach((conn: any, i: number) => {
      newEdges.push({
        id: `edge-${i}-${conn.from_component}-${conn.to_component}`,
        source: resolveNodeId(conn.from_component),
        target: resolveNodeId(conn.to_component),
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 20,
          height: 20,
          color: "#8b5cf6", // violet-500
        },
        style: { stroke: "#8b5cf6", strokeWidth: 2 },
        animated: true,
        data: { connectionIndex: i },
      });
    });

    setNodes(newNodes);
    setEdges(newEdges);
  }, [editablePlan]);

  const handleComponentUpdate = (updatedComponent: any) => {
    if (selectedComponentIndex === null) return;

    const newPlan = { ...editablePlan };
    newPlan.components = [...(editablePlan.components || [])];
    newPlan.components[selectedComponentIndex] = updatedComponent;

    setEditablePlan(newPlan);
    onSave(newPlan); // Save immediately
  };

  const handleConnectionUpdate = (updatedConnection: any) => {
    if (selectedConnectionIndex === null) return;

    const newPlan = { ...editablePlan };
    newPlan.connections = [...(editablePlan.connections || [])];
    newPlan.connections[selectedConnectionIndex] = updatedConnection;

    setEditablePlan(newPlan);
    onSave(newPlan);
  };

  const onEdgeClick: EdgeMouseHandler = (_event, edge) => {
    const idx = edge.data?.connectionIndex;
    if (typeof idx === "number") {
      setSelectedConnectionIndex(idx);
      setSelectedComponentIndex(null);
    }
  };

  const handleAddInfra = (registryKey: string) => {
    const registryEntry = infraRegistry[registryKey];
    if (!registryEntry) return;

    const newComp = {
      name: `new-${registryKey}`,
      type: "infrastructure",
      scope: "project",
      category: registryEntry.category,
      image: registryEntry.default_image,
      port: registryEntry.default_port,
      template_key: registryKey,
      supported_versions: registryEntry.supported_versions || [],
      credentials: {},
      env_variables: [],
      resources: registryEntry.default_resources || {},
      storage: registryEntry.default_storage || null
    };

    const newPlan = { ...editablePlan };
    newPlan.components = [...(editablePlan.components || []), newComp];
    setEditablePlan(newPlan);
    onSave(newPlan);
    setIsAddMenuOpen(false);
  };

  const handleDeleteComponent = (index: number) => {
    if (index === null) return;
    
    const compToDelete = editablePlan.components[index];
    const newPlan = { ...editablePlan };
    
    // Remove component
    newPlan.components = editablePlan.components.filter((_: any, i: number) => i !== index);
    
    // Remove connections
    if (newPlan.connections) {
      newPlan.connections = newPlan.connections.filter(
        (conn: any) => conn.from_component !== compToDelete.name && conn.to_component !== compToDelete.name
      );
    }

    setEditablePlan(newPlan);
    onSave(newPlan);
    setSelectedComponentIndex(null);
  };

  return (
    <div className="w-full h-full flex bg-slate-950 text-slate-200">
      <div className="flex-grow h-full relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onEdgeClick={onEdgeClick}
          nodeTypes={nodeTypes}
          fitView
          className="bg-slate-900/50"
        >
          <Background color="#334155" gap={24} />
          <Controls className="bg-slate-800 border-slate-700 fill-slate-300" />
        </ReactFlow>

        <div className="absolute top-4 right-4 z-10">
          <div className="relative">
            <button
              onClick={() => setIsAddMenuOpen(!isAddMenuOpen)}
              className="bg-violet-600 hover:bg-violet-500 text-white px-3 py-2 rounded-md text-sm font-medium flex items-center gap-2 shadow-lg"
            >
              <Plus size={16} /> Add Infra
            </button>
            {isAddMenuOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-slate-800 border border-slate-700 rounded-md shadow-xl overflow-hidden">
                {Object.keys(infraRegistry).map((key) => (
                  <button
                    key={key}
                    onClick={() => handleAddInfra(key)}
                    className="w-full text-left px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 hover:text-white"
                  >
                    {infraRegistry[key].display_name}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {selectedComponentIndex !== null &&
        editablePlan.components[selectedComponentIndex] && (
          <div className="w-96 h-full border-l border-slate-800 bg-slate-900/95 shadow-2xl overflow-y-auto">
            {editablePlan.components[selectedComponentIndex].type ===
            "infrastructure" ? (
              <InfrastructureDetailPanel
                component={editablePlan.components[selectedComponentIndex]}
                onUpdate={handleComponentUpdate}
                onClose={() => setSelectedComponentIndex(null)}
                onDelete={() => handleDeleteComponent(selectedComponentIndex)}
              />
            ) : (
              <ApplicationDetailPanel
                component={editablePlan.components[selectedComponentIndex]}
                onUpdate={handleComponentUpdate}
                onClose={() => setSelectedComponentIndex(null)}
              />
            )}
          </div>
        )}

      {selectedConnectionIndex !== null &&
        editablePlan.connections?.[selectedConnectionIndex] && (
          <div className="w-96 h-full border-l border-slate-800 bg-slate-900/95 shadow-2xl overflow-y-auto">
            <ConnectionDetailPanel
              connection={editablePlan.connections[selectedConnectionIndex]}
              onUpdate={handleConnectionUpdate}
              onClose={() => setSelectedConnectionIndex(null)}
            />
          </div>
        )}
    </div>
  );
}
