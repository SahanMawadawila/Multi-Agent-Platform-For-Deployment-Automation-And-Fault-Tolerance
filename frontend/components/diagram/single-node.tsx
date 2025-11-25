"use client";
import { Handle, Position } from "reactflow";

export const SingleNode = ({ data }: any) => {
  return (
    <div className="w-14 h-14 rounded-lg flex items-center justify-center cursor-pointer transition-all hover:scale-105">
      {data.label}
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 bg-blue-500/50 border-2 border-blue-600 rounded-full left-0 -ml-1"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 bg-blue-500/50 border-2 border-blue-600 rounded-full right-0 -mr-1"
      />
    </div>
  );
};
