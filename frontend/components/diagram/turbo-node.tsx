"use client";
import { memo, type ReactNode } from "react";

import { Handle, Position, type NodeProps } from "reactflow";

export type TurboNodeData = {
  icon?: ReactNode;
};

export default memo(({ data }: NodeProps<TurboNodeData>) => {
  return (
    <>
      <div className="wrapper gradient">
        <div className="inner">
          <div className="body">
            {data.icon && <div className="icon">{data.icon}</div>}
          </div>
          <Handle type="target" position={Position.Left} />
          <Handle type="source" position={Position.Right} />
        </div>
      </div>
    </>
  );
});
