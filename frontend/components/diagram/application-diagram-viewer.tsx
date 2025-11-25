"use client";
import { useCallback } from "react";
import {
  ReactFlow,
  Controls,
  useNodesState,
  useEdgesState,
  addEdge,
  type Node,
  type Edge,
  type OnConnect,
} from "reactflow";
import { Server, Database } from "lucide-react";

import "reactflow/dist/style.css";

import TurboNode, { type TurboNodeData } from "./turbo-node";
import TurboEdge from "./turbo-edge";

const initialNodes: Node<TurboNodeData>[] = [
  {
    id: "1",
    position: { x: 0, y: 0 },
    data: { icon: <Server size={24} /> },
    type: "turbo",
  },
  {
    id: "2",
    position: { x: 250, y: 0 },
    data: { icon: <Server size={24} /> },
    type: "turbo",
  },
  {
    id: "3",
    position: { x: 500, y: 0 },
    data: { icon: <Server size={24} /> },
    type: "turbo",
  },
  {
    id: "4",
    data: { icon: <Database size={24} /> },
    position: { x: 250, y: 150 },
    type: "turbo",
  },
  {
    id: "5",
    position: { x: 750, y: 0 },
    data: { icon: <Database size={24} /> },
    type: "turbo",
  },
];

const initialEdges: Edge[] = [
  { id: "e1-2", source: "1", target: "2" },
  { id: "e2-3", source: "2", target: "3" },
  { id: "e2-4", source: "2", target: "4" },
  { id: "e3-5", source: "3", target: "5" },
];

const nodeTypes = {
  turbo: TurboNode,
};

const edgeTypes = {
  turbo: TurboEdge,
};

const defaultEdgeOptions = {
  type: "turbo",
  markerEnd: "edge-arrow",
};

export const ApplicationDiagramViewer = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect: OnConnect = useCallback(
    (params) => setEdges((els) => addEdge(params, els)),
    []
  );

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
      >
        <Controls showInteractive={false} />
        <svg>
          <defs>
            <linearGradient id="edge-gradient">
              <stop offset="0%" stopColor="#ae53ba" />
              <stop offset="100%" stopColor="#2a8af6" />
            </linearGradient>

            <marker
              className="react-flow__arrowhead"
              id="edge-arrow"
              markerWidth="20"
              markerHeight="20"
              viewBox="-10 -10 20 20"
              markerUnits="userSpaceOnUse"
              orient="auto-start-reverse"
              refX="0"
              refY="0"
            >
              <polyline
                style={{
                  strokeWidth: 1,
                  stroke: "#e92a67",
                  fill: "#e92a67",
                }}
                strokeLinecap="round"
                strokeLinejoin="round"
                points="-5,-4 0,0 -5,4 -5,-4"
              />
            </marker>
          </defs>
        </svg>
      </ReactFlow>
    </div>
  );
};
