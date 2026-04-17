import React, { useEffect, useState } from "react";
import { X, Save, Plus, Trash2 } from "lucide-react";
import { Button } from "../ui/button";

interface ApplicationDetailPanelProps {
  component: any;
  onUpdate: (comp: any) => void;
  onClose: () => void;
}

export function ApplicationDetailPanel({
  component,
  onUpdate,
  onClose,
}: ApplicationDetailPanelProps) {
  const [localComp, setLocalComp] = useState<any>(
    JSON.parse(JSON.stringify(component)),
  );

  useEffect(() => {
    setLocalComp(JSON.parse(JSON.stringify(component)));
  }, [component]);

  const handleSave = () => {
    onUpdate(localComp);
    onClose();
  };

  const handleFieldChange = (field: string, value: any) => {
    setLocalComp((prev: any) => ({ ...prev, [field]: value }));
  };

  const handleEnvChange = (index: number, key: string, value: string) => {
    const newEnvs = [...(localComp.env_variables || [])];
    newEnvs[index] = { ...newEnvs[index], [key]: value };
    handleFieldChange("env_variables", newEnvs);
  };

  const removeEnv = (index: number) => {
    const newEnvs = [...(localComp.env_variables || [])];
    newEnvs.splice(index, 1);
    handleFieldChange("env_variables", newEnvs);
  };

  const addEnv = () => {
    const newEnvs = [
      ...(localComp.env_variables || []),
      {
        key: "",
        value: "",
        source: "override",
        editable: true,
        sensitive: false,
      },
    ];
    handleFieldChange("env_variables", newEnvs);
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 border-l border-slate-800 text-slate-200">
      <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900/50">
        <h3 className="font-semibold text-lg">{localComp.name} Settings</h3>
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
              <label className="text-xs text-slate-400 mb-1 block">Name</label>
              <input
                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                value={localComp.name || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  handleFieldChange("name", e.target.value)
                }
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Path</label>
              <input
                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                value={localComp.path || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  handleFieldChange("path", e.target.value)
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 mb-1 block">
                  Project Type
                </label>
                <input
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                  value={localComp.project_type || ""}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    handleFieldChange("project_type", e.target.value)
                  }
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 mb-1 block">
                  Framework
                </label>
                <input
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                  value={localComp.framework || ""}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    handleFieldChange("framework", e.target.value)
                  }
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 mb-1 block">
                  Runtime Version
                </label>
                <input
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                  value={localComp.version || ""}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    handleFieldChange("version", e.target.value)
                  }
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 mb-1 block">
                  Package Manager
                </label>
                <input
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                  value={localComp.package_manager || ""}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    handleFieldChange("package_manager", e.target.value)
                  }
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 mb-1 block">
                  Role
                </label>
                <input
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                  value={localComp.role || ""}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    handleFieldChange("role", e.target.value)
                  }
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 mb-1 block">
                  Port
                </label>
                <input
                  type="number"
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                  value={localComp.port || ""}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    handleFieldChange("port", Number(e.target.value))
                  }
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">
                Image Name
              </label>
              <input
                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                value={localComp.image_name || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  handleFieldChange("image_name", e.target.value)
                }
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">
                Health Check Path
              </label>
              <input
                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                value={localComp.health_check_path || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  handleFieldChange("health_check_path", e.target.value)
                }
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">
                Build Command
              </label>
              <input
                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                value={localComp.build_command || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  handleFieldChange("build_command", e.target.value)
                }
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">
                Run Command
              </label>
              <input
                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                value={localComp.run_command || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  handleFieldChange("run_command", e.target.value)
                }
              />
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold tracking-wider text-slate-400 uppercase">
              Environment
            </h4>
            <button
              onClick={addEnv}
              className="text-violet-400 hover:text-violet-300 text-xs flex items-center gap-1"
            >
              <Plus size={14} /> Add
            </button>
          </div>
          <div className="space-y-2">
            {(localComp.env_variables || []).map((env: any, i: number) => (
              <div key={i} className="flex gap-2 items-start">
                <div className="flex-grow space-y-2">
                  <input
                    placeholder="Key"
                    className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-xs h-8 px-2 font-mono"
                    value={env.key}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      handleEnvChange(i, "key", e.target.value)
                    }
                  />
                  <input
                    placeholder="Value"
                    type="text"
                    className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-xs h-8 px-2 font-mono"
                    value={env.value}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      handleEnvChange(i, "value", e.target.value)
                    }
                  />
                </div>
                <button
                  onClick={() => removeEnv(i)}
                  className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-400/10 rounded"
                  title="Remove"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
            {(!localComp.env_variables ||
              localComp.env_variables.length === 0) && (
              <p className="text-xs text-slate-500 italic text-center py-2">
                No environment variables.
              </p>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <h4 className="text-sm font-semibold tracking-wider text-slate-400 uppercase">
            Resources
          </h4>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">
                CPU Limit
              </label>
              <input
                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                value={localComp.resources?.cpu_limit || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setLocalComp((prev: any) => ({
                    ...prev,
                    resources: { ...prev.resources, cpu_limit: e.target.value },
                  }))
                }
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">
                Memory
              </label>
              <input
                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                value={localComp.resources?.memory_limit || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setLocalComp((prev: any) => ({
                    ...prev,
                    resources: {
                      ...prev.resources,
                      memory_limit: e.target.value,
                    },
                  }))
                }
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">
                Replicas
              </label>
              <input
                type="number"
                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                value={localComp.resources?.replicas ?? 1}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setLocalComp((prev: any) => ({
                    ...prev,
                    resources: {
                      ...prev.resources,
                      replicas: Number(e.target.value),
                    },
                  }))
                }
              />
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <h4 className="text-sm font-semibold tracking-wider text-slate-400 uppercase">
            Ingress
          </h4>
          <div className="space-y-3">
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={Boolean(localComp.ingress?.expose)}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setLocalComp((prev: any) => ({
                    ...prev,
                    ingress: { ...prev.ingress, expose: e.target.checked },
                  }))
                }
              />
              Expose via ingress
            </label>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">
                Path Prefix
              </label>
              <input
                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                value={localComp.ingress?.path_prefix || "/"}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setLocalComp((prev: any) => ({
                    ...prev,
                    ingress: { ...prev.ingress, path_prefix: e.target.value },
                  }))
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
