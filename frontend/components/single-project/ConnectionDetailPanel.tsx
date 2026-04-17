import React, { useEffect, useState } from "react";
import { X, Save } from "lucide-react";
import { Button } from "../ui/button";

interface ConnectionDetailPanelProps {
  connection: any;
  onUpdate: (conn: any) => void;
  onClose: () => void;
}

export function ConnectionDetailPanel({
  connection,
  onUpdate,
  onClose,
}: ConnectionDetailPanelProps) {
  const [localConn, setLocalConn] = useState<any>(
    JSON.parse(JSON.stringify(connection)),
  );

  useEffect(() => {
    setLocalConn(JSON.parse(JSON.stringify(connection)));
  }, [connection]);

  const handleSave = () => {
    onUpdate(localConn);
    onClose();
  };

  const handleFieldChange = (field: string, value: any) => {
    setLocalConn((prev: any) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 border-l border-slate-800 text-slate-200">
      <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900/50">
        <h3 className="font-semibold text-lg">Connection Details</h3>
        <button onClick={onClose} className="text-slate-400 hover:text-white">
          <X size={20} />
        </button>
      </div>

      <div className="flex-grow p-5 space-y-6 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700">
        <div className="space-y-4">
          <h4 className="text-sm font-semibold tracking-wider text-slate-400 uppercase">
            General
          </h4>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">
                From Component
              </label>
              <input
                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                value={localConn.from_component || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  handleFieldChange("from_component", e.target.value)
                }
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">
                To Component
              </label>
              <input
                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                value={localConn.to_component || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  handleFieldChange("to_component", e.target.value)
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 mb-1 block">
                  Scope
                </label>
                <select
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                  value={localConn.scope || "internal"}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                    handleFieldChange("scope", e.target.value)
                  }
                >
                  <option value="internal">internal</option>
                  <option value="external">external</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400 mb-1 block">
                  Env Key
                </label>
                <input
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                  value={localConn.env_key || ""}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    handleFieldChange("env_key", e.target.value)
                  }
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">
                Resolved Value
              </label>
              <input
                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2 font-mono"
                value={localConn.resolved_value || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  handleFieldChange("resolved_value", e.target.value)
                }
              />
            </div>
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-slate-800 bg-slate-900/50">
        <Button
          className="w-full bg-violet-600 hover:bg-violet-500 text-white flex items-center justify-center gap-2"
          onClick={handleSave}
        >
          <Save size={16} /> Save Changes
        </Button>
      </div>
    </div>
  );
}
