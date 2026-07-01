import React, { useEffect, useState } from "react";
import { X, Save, Plus, Trash2 } from "lucide-react";
import { Button } from "../ui/button";

interface InfrastructureDetailPanelProps {
  component: any;
  onUpdate: (comp: any) => void;
  onClose: () => void;
  onDelete?: () => void;
}

export function InfrastructureDetailPanel({
  component,
  onUpdate,
  onClose,
  onDelete,
}: InfrastructureDetailPanelProps) {
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

  const handleCredentialChange = (key: string, value: string) => {
    const nextCreds = { ...(localComp.credentials || {}) };
    nextCreds[key] = { ...(nextCreds[key] || {}), value };
    handleFieldChange("credentials", nextCreds);
  };

  const addCredential = () => {
    const nextCreds = { ...(localComp.credentials || {}) };
    const key = `CREDENTIAL_${Object.keys(nextCreds).length + 1}`;
    nextCreds[key] = {
      value: "",
      source: "override",
      editable: true,
      sensitive: false,
    };
    handleFieldChange("credentials", nextCreds);
  };

  const removeCredential = (key: string) => {
    const nextCreds = { ...(localComp.credentials || {}) };
    delete nextCreds[key];
    handleFieldChange("credentials", nextCreds);
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 border-l border-slate-800 text-slate-200">
      <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900/50">
        <h3 className="font-semibold text-lg">{localComp.name} Settings</h3>
        <div className="flex items-center gap-3">
          {onDelete && (
            <button onClick={onDelete} className="text-red-400 hover:text-red-300" title="Delete Component">
              <Trash2 size={18} />
            </button>
          )}
          <button onClick={onClose} className="text-slate-400 hover:text-white" title="Close Panel">
            <X size={20} />
          </button>
        </div>
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
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 mb-1 block">
                  Scope
                </label>
                <select
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                  value={localComp.scope || "project"}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                    handleFieldChange("scope", e.target.value)
                  }
                >
                  <option value="project">project</option>
                  <option value="global">global</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400 mb-1 block">
                  Owner App
                </label>
                <input
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                  value={localComp.owner_app || ""}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    handleFieldChange("owner_app", e.target.value)
                  }
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 mb-1 block">
                  Category
                </label>
                <input
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                  value={localComp.category || ""}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    handleFieldChange("category", e.target.value)
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
              <label className="text-xs text-slate-400 mb-1 block">Image</label>
              <input
                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                value={localComp.image || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  handleFieldChange("image", e.target.value)
                }
              />
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold tracking-wider text-slate-400 uppercase">
              Credentials
            </h4>
            <button
              onClick={addCredential}
              className="text-violet-400 hover:text-violet-300 text-xs flex items-center gap-1"
            >
              <Plus size={14} /> Add
            </button>
          </div>
          <div className="space-y-2">
            {Object.entries(localComp.credentials || {}).map(
              ([key, cred]: any) => (
                <div key={key} className="flex gap-2 items-start">
                  <div className="flex-grow space-y-2">
                    <input
                      className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-xs h-8 px-2 font-mono"
                      value={key}
                      readOnly
                    />
                    <input
                      placeholder="Value"
                      type="text"
                      className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-xs h-8 px-2 font-mono"
                      value={cred?.value || ""}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                        handleCredentialChange(key, e.target.value)
                      }
                    />
                  </div>
                  <button
                    onClick={() => removeCredential(key)}
                    className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-400/10 rounded"
                    title="Remove"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ),
            )}
            {(!localComp.credentials ||
              Object.keys(localComp.credentials).length === 0) && (
              <p className="text-xs text-slate-500 italic text-center py-2">
                No credentials.
              </p>
            )}
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
            Storage
          </h4>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Size</label>
              <input
                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                value={localComp.storage?.size || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setLocalComp((prev: any) => ({
                    ...prev,
                    storage: { ...prev.storage, size: e.target.value },
                  }))
                }
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">
                Storage Class
              </label>
              <input
                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                value={localComp.storage?.storage_class || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setLocalComp((prev: any) => ({
                    ...prev,
                    storage: { ...prev.storage, storage_class: e.target.value },
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
