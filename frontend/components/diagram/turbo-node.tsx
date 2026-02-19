"use client";
import { memo, type ReactNode } from "react";

import { Handle, Position, type NodeProps } from "reactflow";

export type TurboNodeData = {
  icon?: ReactNode;
  title?: string;
  subline?: string;
};

export default memo(({ data, selected }: NodeProps<TurboNodeData>) => {
  return (
    <>
      <div className={`wrapper gradient ${selected ? 'selected' : ''}`}>
        <div className="inner">
          <div className="body flex items-center">
            {data.icon && <div className="icon">{data.icon}</div>}
            <div className="ml-3 flex flex-col">
              {/* Title (Type) always visible */}
              {data.title && <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{data.title}</div>}

              {/* Subline (Pod Name) - Truncated by default, full if selected */}
              <div className={`text-sm font-medium text-slate-200 ${!selected ? 'truncate w-[120px]' : ''}`} title={data.subline}>
                {data.subline}
              </div>

              {/* Status - Only visible if selected */}
              {selected && data.subline && (
                <div className="mt-1 text-xs text-emerald-400 font-mono">
                  Running
                </div>
              )}
            </div>
          </div>
          <Handle type="target" position={Position.Left} />
          <Handle type="source" position={Position.Right} />
        </div>
      </div>
    </>
  );
});
