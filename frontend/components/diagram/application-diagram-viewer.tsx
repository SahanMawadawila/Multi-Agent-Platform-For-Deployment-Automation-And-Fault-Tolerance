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
          height: 70px;
          font-family: "Fira Mono", Monospace;
          font-weight: 500;
          letter-spacing: -0.2px;
          box-shadow: var(--node-box-shadow);
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
          justify-content: center;
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

        .react-flow__controls button {
          background-color: rgb(30, 41, 59);
          color: var(--text-color);
          border: 1px solid rgb(71, 85, 105);
          border-bottom: none;
        }

        .react-flow__controls button:hover {
          background-color: rgb(51, 65, 85);
        }

        .react-flow__controls button:first-child {
          border-radius: 5px 5px 0 0;
        }

        .react-flow__controls button:last-child {
          border-bottom: 1px solid rgb(71, 85, 105);
          border-radius: 0 0 5px 5px;
        }

        .react-flow__controls button path {
          fill: var(--text-color);
        }
      `}</style>
    </div>
  );
};
