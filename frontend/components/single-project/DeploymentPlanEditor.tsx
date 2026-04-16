import React, { useState, useCallback, useMemo, useEffect } from 'react';
import ReactFlow, { 
  Node, 
  Edge, 
  Controls, 
  Background, 
  useNodesState, 
  useEdgesState,
  MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';

import { PlanNode } from './PlanNode';
import { ComponentEditPanel } from './ComponentEditPanel';

interface DeploymentPlanEditorProps {
    plan: any;
    projectId: string;
    onSave: (updatedPlan: any) => void;
}

const nodeTypes = {
  customNode: PlanNode
};

export function DeploymentPlanEditor({ plan, projectId, onSave }: DeploymentPlanEditorProps) {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [selectedComponentIndex, setSelectedComponentIndex] = useState<number | null>(null);
    const [editablePlan, setEditablePlan] = useState<any>(plan);

    // Initialize map and nodes on plan load
    useEffect(() => {
        if (!editablePlan || !editablePlan.components) return;

        const newNodes: Node[] = [];
        const newEdges: Edge[] = [];

        // Basic auto-layout positioning
        let xOffset = 100;
        let yOffset = 100;

        editablePlan.components.forEach((comp: any, i: number) => {
            newNodes.push({
                id: comp.name,
                type: 'customNode',
                position: { x: xOffset, y: yOffset },
                data: {
                    label: comp.name,
                    type: comp.type,
                    role: comp.role || comp.category,
                    onSelect: () => setSelectedComponentIndex(i)
                }
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
                source: conn.from_component,
                target: conn.to_component,
                label: conn.description || `${conn.protocol}`,
                markerEnd: {
                    type: MarkerType.ArrowClosed,
                    width: 20,
                    height: 20,
                    color: '#8b5cf6', // violet-500
                },
                style: { stroke: '#8b5cf6', strokeWidth: 2 },
                animated: true
            });
        });

        setNodes(newNodes);
        setEdges(newEdges);
    }, [editablePlan]);

    const handleComponentUpdate = (updatedComponent: any) => {
        if (selectedComponentIndex === null) return;
        
        const newPlan = { ...editablePlan };
        newPlan.components[selectedComponentIndex] = updatedComponent;
        
        setEditablePlan(newPlan);
        onSave(newPlan); // Save immediately
    };

    return (
        <div className="w-full h-full flex bg-slate-950 text-slate-200">
            <div className="flex-grow h-full relative">
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    nodeTypes={nodeTypes}
                    fitView
                    className="bg-slate-900/50"
                >
                    <Background color="#334155" gap={24} />
                    <Controls className="bg-slate-800 border-slate-700 fill-slate-300" />
                </ReactFlow>

                {/* Overlaid UI or buttons can go here */}
            </div>

            {selectedComponentIndex !== null && editablePlan.components[selectedComponentIndex] && (
                <div className="w-96 h-full border-l border-slate-800 bg-slate-900/95 shadow-2xl overflow-y-auto">
                    <ComponentEditPanel 
                        component={editablePlan.components[selectedComponentIndex]}
                        onUpdate={handleComponentUpdate}
                        onClose={() => setSelectedComponentIndex(null)}
                    />
                </div>
            )}
        </div>
    );
}
