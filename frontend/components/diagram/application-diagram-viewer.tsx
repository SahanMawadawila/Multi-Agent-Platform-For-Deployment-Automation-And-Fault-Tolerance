"use client";
import { useCallback, useEffect, useState } from "react";
import {
  ReactFlow,
  Controls,
  useNodesState,
  useEdgesState,
  addEdge,
  type Node,
  type Edge,
  type OnConnect,
  Background,
} from "reactflow";
import { Server, Database, RefreshCw, AlertCircle, Box, Network } from "lucide-react";
import { useSession } from "next-auth/react";

import "reactflow/dist/style.css";

import TurboNode, { type TurboNodeData } from "./turbo-node";
import TurboEdge from "./turbo-edge";
import { Button } from "@/components/ui/button";

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

interface ApplicationDiagramViewerProps {
  projectId?: string;
}

// Layout Algorithm
const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
  // Group by kind/type
  const lbNodes = nodes.filter(n => n.id === 'load-balancer')
  const appNodes = nodes.filter(n => n.data.group === 'app')
  const dbNodes = nodes.filter(n => n.data.group === 'database')
  const otherNodes = nodes.filter(n => n.data.group === 'other' || n.data.group === 'pod')

  // Set X positions
  const X_SPACING = 400
  const Y_SPACING = 120

  const layoutNode = (node: Node, index: number, levelX: number) => {
    node.position = {
      x: levelX,
      y: index * Y_SPACING + 50
    }
    return node
  }

  const newNodes = [
    ...lbNodes.map((n, i) => layoutNode(n, i, 0)),
    ...appNodes.map((n, i) => layoutNode(n, i, X_SPACING)),
    ...dbNodes.map((n, i) => layoutNode(n, i, X_SPACING * 2)),
    ...otherNodes.map((n, i) => layoutNode(n, i, X_SPACING * 1.5)) // Place others between app and db or alongside app
  ]

  // Add any remaining nodes
  const processedIds = new Set(newNodes.map(n => n.id));
  const remainingNodes = nodes.filter(n => !processedIds.has(n.id));
  remainingNodes.forEach((n, i) => {
    n.position = { x: 0, y: (newNodes.length + i) * Y_SPACING + 50 };
    newNodes.push(n);
  });

  return { nodes: newNodes, edges }
}

export const ApplicationDiagramViewer = ({ projectId }: ApplicationDiagramViewerProps) => {
  const { data: session } = useSession();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onConnect: OnConnect = useCallback(
    (params) => setEdges((els) => addEdge(params, els)),
    []
  );

  const fetchDiagram = useCallback(async () => {
    if (!session?.backendToken || !projectId) return;

    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/k8s/${projectId}/diagram`, {
        headers: {
          Authorization: `Bearer ${session.backendToken}`
        }
      });

      if (!res.ok) {
        if (res.status === 404) {
          setNodes([]);
          setEdges([]);
          return;
        }
        throw new Error("Failed to fetch diagram data");
      }

      const data = await res.json();

      const mappedNodes: Node[] = [];
      const mappedEdges = (data.edges || []).map((e: any) => ({
        ...e,
        type: 'turbo',
        animated: true,
        style: { stroke: '#94a3b8' }
      }));

      // Add Load Balancer Node
      mappedNodes.push({
        id: 'load-balancer',
        type: 'turbo',
        data: {
          icon: <Network size={20} />,
          title: 'Gateway',
          subline: 'Load Balancer',
          group: 'loadbalancer'
        },
        position: { x: 0, y: 0 }
      });

      // Map backend data to TurboNodes
      (data.nodes || []).forEach((n: any) => {
        let icon = <Box size={20} />;
        let group = 'other';
        let title = n.data.kind || 'Resource';
        let subline = n.data.label;

        if (n.data.kind === 'Pod') {
          const type = n.data.type;
          if (type === 'app') {
            icon = <Server size={20} />;
            group = 'app';
            title = 'Application';
          } else if (type === 'database') {
            icon = <Database size={20} />;
            group = 'database';
            title = 'Database';
          } else {
            icon = <Box size={20} />;
            group = 'pod';
          }
          // subline should contain status for detail view
          // n.data.status exists from backend
          subline = `${n.data.label} (${n.data.status})`;
        }

        mappedNodes.push({
          id: n.id,
          type: 'turbo',
          data: {
            icon,
            title,
            subline: subline, // Passed partially for truncation in TurboNode
            group
          },
          position: { x: 0, y: 0 }
        });
      });

      // Apply layout
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(mappedNodes, mappedEdges);

      setNodes(layoutedNodes);
      setEdges(layoutedEdges);

    } catch (err: any) {
      console.error(err);
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  }, [projectId, session, setNodes, setEdges]);

  useEffect(() => {
    if (session && projectId) {
      fetchDiagram();
    }
  }, [session, projectId, fetchDiagram]);

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      {/* Overlay Header */}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        {error && (
          <div className="flex items-center gap-2 bg-red-900/50 text-red-200 px-3 py-1 rounded text-xs border border-red-800">
            <AlertCircle size={12} />
            {error}
          </div>
        )}
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0 bg-slate-800/50 hover:bg-slate-700 border border-slate-700"
          onClick={fetchDiagram}
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

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
        <Background color="#334155" gap={20} size={1} />
        <Controls showInteractive={false} className="bg-slate-800 border-slate-700" />
        <svg>
          <defs>
            <linearGradient id="edge-gradient">
              <stop offset="0%" stopColor="#7c3aed" />
              <stop offset="100%" stopColor="#a78bfa" />
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
                  stroke: "#8b5cf6",
                  fill: "#8b5cf6",
                }}
                strokeLinecap="round"
                strokeLinejoin="round"
                points="-5,-4 0,0 -5,4 -5,-4"
              />
            </marker>
          </defs>
        </svg>
      </ReactFlow>
      <style jsx global>{`
        .react-flow {
          --bg-color: rgb(15, 23, 42);
          --text-color: rgb(226, 232, 240);
          --node-border-radius: 10px;
          --node-box-shadow: 0 10px 15px -3px rgba(124, 58, 237, 0.3),
            0 4px 6px -4px rgba(139, 92, 246, 0.3);
          background-color: var(--bg-color);
          color: var(--text-color);
        }

        .react-flow__node-turbo {
          border-radius: var(--node-border-radius);
          display: flex;
          height: auto;
          min-height: 70px;
          min-width: 200px; /* Default width */
          font-family: "Fira Mono", Monospace;
          font-weight: 500;
          letter-spacing: -0.2px;
          box-shadow: var(--node-box-shadow);
          transition: all 0.2s ease-in-out;
        }
        
        /* Expand when selected */
        .react-flow__node-turbo.selected {
             min-width: 280px; /* Expand width */
             border: 1px solid rgba(139, 92, 246, 0.5);
        }

        .react-flow__node-turbo .wrapper {
          overflow: hidden;
          display: flex;
          padding: 2px;
          position: relative;
          border-radius: var(--node-border-radius);
          flex-grow: 1;
        }

        .gradient:before {
          content: "";
          position: absolute;
          padding-bottom: calc(100% * 1.41421356237);
          width: calc(100% * 1.41421356237);
          background: conic-gradient(
            from -160deg at 50% 50%,
            #7c3aed 0deg,
            #8b5cf6 120deg,
            #a78bfa 240deg,
            #7c3aed 360deg
          );
          left: 50%;
          top: 50%;
          transform: translate(-50%, -50%);
          border-radius: 100%;
        }

        .react-flow__node-turbo.selected .wrapper.gradient:before {
          content: "";
          background: conic-gradient(
            from -160deg at 50% 50%,
            #7c3aed 0deg,
            #8b5cf6 120deg,
            #a78bfa 240deg,
            rgba(124, 58, 237, 0) 360deg
          );
          animation: spinner 4s linear infinite;
          transform: translate(-50%, -50%) rotate(0deg);
          z-index: -1;
        }

        @keyframes spinner {
          100% {
            transform: translate(-50%, -50%) rotate(-360deg);
          }
        }

        .react-flow__node-turbo .inner {
          background: rgb(30, 41, 59);
          padding: 16px 20px;
          border-radius: var(--node-border-radius);
          display: flex;
          flex-direction: column;
          justify-content: center;
          flex-grow: 1;
          position: relative;
        }

        .react-flow__node-turbo .icon {
          display: flex;
          justify-content: center;
          align-items: center;
          color: rgb(167, 139, 250);
        }

        .react-flow__node-turbo .body {
          display: flex;
          align-items: center; 
        }

        .react-flow__handle {
          opacity: 0;
        }

        .react-flow__handle.source {
          right: -10px;
        }

        .react-flow__handle.target {
          left: -10px;
        }

        .react-flow__node:focus {
          outline: none;
        }

        .react-flow__edge .react-flow__edge-path {
          stroke: url(#edge-gradient);
          stroke-width: 2;
          stroke-opacity: 0.75;
        }

        .react-flow__edge .react-flow__edge-path.animated {
          stroke-dasharray: 5;
          animation: dash-flow 0.5s linear infinite;
        }

        @keyframes dash-flow {
          to {
            stroke-dashoffset: -10;
          }
        }
      `}</style>

      {!projectId && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/50 z-20">
          <div className="text-slate-400">Loading diagram...</div>
        </div>
      )}

      {nodes.length === 0 && !loading && projectId && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-slate-500 text-sm">No active resources found in cluster</div>
        </div>
      )}
    </div>
  );
};
