"use client";

import { useCallback } from "react";
import ReactFlow, {
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
} from "reactflow";
import { Server, Database } from "lucide-react";
import { SingleNode } from "./single-node";

import "reactflow/dist/style.css";

// 1. Define your initial nodes
const initialNodes = [
  {
    id: "node-1",
    position: { x: 0, y: 0 },
    data: {
      label: <Server className="w-6 h-6 text-blue-600" />,
    },
    type: "singleNode",
  },
  {
    id: "node-2",
    position: { x: 0, y: 100 },
    data: {
      label: <Server className="w-6 h-6 text-blue-600" />,
    },
    type: "singleNode",
  },
  {
    id: "node-3",
    position: { x: 0, y: 200 },
    data: {
      label: <Server className="w-6 h-6 text-blue-600" />,
    },
    type: "singleNode",
  },
  {
    id: "node-4",
    position: { x: 0, y: 300 },
    data: {
      label: <Server className="w-6 h-6 text-blue-600" />,
    },
    type: "singleNode",
  },
  {
    id: "db-1",
    type: "singleNode",
    position: { x: 250, y: 50 },
    data: {
      label: <Database className="w-6 h-6 text-blue-600" />,
    },
  },
  {
    id: "db-2",
    type: "singleNode",
    position: { x: 250, y: 200 },
    data: {
      label: <Database className="w-6 h-6 text-blue-600" />,
    },
  },
  {
    id: "db-3",
    type: "singleNode",
    position: { x: 250, y: 350 },
    data: {
      label: <Database className="w-6 h-6 text-blue-600" />,
    },
  },
  {
    id: "db-4",
    type: "singleNode",
    position: { x: 250, y: 300 },
    data: {
      label: <Database className="w-6 h-6 text-blue-600" />,
    },
  },
  {
    id: "db-5",
    type: "singleNode",
    position: { x: 250, y: 400 },
    data: {
      label: <Database className="w-6 h-6 text-blue-600" />,
    },
  },
];

// 2. Define your initial edges
const initialEdges = [
  {
    id: "e1-db",
    source: "node-1",
    target: "db-1",
    animated: true,
    style: { stroke: "#8884d8" },
  },
  {
    id: "e2-db",
    source: "node-2",
    target: "db-1",
    animated: true,
    style: { stroke: "#8884d8" },
  },
  {
    id: "e3-db",
    source: "node-2",
    target: "db-2",
    animated: true,
    style: { stroke: "#8884d8" },
  },
  {
    id: "e4-db",
    source: "node-3",
    target: "db-2",
    animated: true,
    style: { stroke: "#8884d8" },
  },
  {
    id: "e5-db",
    source: "node-4",
    target: "db-3",
    animated: true,
    style: { stroke: "#8884d8" },
  },
  {
    id: "e6-db",
    source: "node-4",
    target: "db-4",
    animated: true,
    style: { stroke: "#8884d8" },
  },
  {
    id: "e7-db",
    source: "node-4",
    target: "db-5",
    animated: true,
    style: { stroke: "#8884d8" },
  },
];

export function ApplicationDiagramViewer() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (params: any) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  return (
    <div className="w-[600px] h-[600px]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={{ singleNode: SingleNode }}
      >
        <Controls />
        <Background />
      </ReactFlow>
    </div>
  );
}
