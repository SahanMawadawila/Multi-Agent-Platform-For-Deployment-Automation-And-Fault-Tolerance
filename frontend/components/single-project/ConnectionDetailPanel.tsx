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

  const handleEnvUpdateChange = (
    index: number,
    field: string,
    value: string,
  ) => {
    setLocalConn((prev: any) => {
      const envUpdates = Array.isArray(prev.env_updates)
        ? [...prev.env_updates]
        : [];
      envUpdates[index] = { ...(envUpdates[index] || {}), [field]: value };
      return { ...prev, env_updates: envUpdates };
    });
  };

  const handleAddEnvUpdate = () => {
    setLocalConn((prev: any) => {
      const envUpdates = Array.isArray(prev.env_updates)
        ? [...prev.env_updates]
        : [];
      envUpdates.push({
        key: "",
        value: "",
        source: "override",
        editable: true,
        sensitive: false,
      });
      return { ...prev, env_updates: envUpdates };
    });
  };

  const handleRemoveEnvUpdate = (index: number) => {
    setLocalConn((prev: any) => {
      const envUpdates = Array.isArray(prev.env_updates)
        ? [...prev.env_updates]
        : [];
      envUpdates.splice(index, 1);
      return { ...prev, env_updates: envUpdates };
    });
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
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Scope</label>
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
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold tracking-wider text-slate-400 uppercase">
              Env Updates
            </h4>
            <button
              className="text-xs text-violet-300 hover:text-violet-200"
              onClick={handleAddEnvUpdate}
            >
              + Add
            </button>
          </div>
          <div className="space-y-3">
            {(localConn.env_updates || []).length === 0 && (
              <p className="text-xs text-slate-500">No env updates mapped.</p>
            )}
            {(localConn.env_updates || []).map((env: any, idx: number) => (
              <div
                key={`${env.key || "env"}-${idx}`}
                className="grid grid-cols-[1fr_1fr_auto] gap-2"
              >
                <input
                  className="bg-slate-800/50 border border-slate-700 rounded-md text-xs h-8 px-2"
                  placeholder="KEY"
                  value={env.key || ""}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    handleEnvUpdateChange(idx, "key", e.target.value)
                  }
                />
                <input
                  className="bg-slate-800/50 border border-slate-700 rounded-md text-xs h-8 px-2 font-mono"
                  placeholder="VALUE"
                  value={env.value || ""}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    handleEnvUpdateChange(idx, "value", e.target.value)
                  }
                />
                <button
                  className="text-xs text-red-300 hover:text-red-200 px-2"
                  onClick={() => handleRemoveEnvUpdate(idx)}
                >
                  Remove
                </button>
              </div>
            ))}
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
