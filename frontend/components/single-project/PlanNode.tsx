import React from "react";
import { Handle, Position } from "reactflow";
import { Database, Server, Component, Cloud } from "lucide-react";

export function PlanNode({ data }: any) {
  const isInfra = data.type === "infrastructure";

  return (
    <div
      className="px-4 py-3 shadow-lg rounded-xl bg-slate-800 border-2 border-slate-700 min-w-[180px] cursor-pointer hover:border-violet-500 transition-colors"
      onClick={data.onSelect}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 bg-violet-400"
      />

      <div className="flex items-center gap-3">
        <div
          className={`p-2 rounded-lg ${isInfra ? "bg-indigo-900/50 text-indigo-400" : "bg-emerald-900/50 text-emerald-400"}`}
        >
          {isInfra ? <Database size={18} /> : <Server size={18} />}
        </div>
        <div>
          <h4 className="font-bold text-sm text-white">{data.label}</h4>
          <p className="text-xs text-slate-400 capitalize">{data.role}</p>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 bg-violet-400"
      />
    </div>
  );
}
