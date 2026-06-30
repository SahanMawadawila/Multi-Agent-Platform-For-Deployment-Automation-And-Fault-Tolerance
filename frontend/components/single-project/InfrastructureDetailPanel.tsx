import React, { useEffect, useState } from "react";
import { X, Save, Plus, Trash2, AlertTriangle, CheckCircle2 } from "lucide-react";
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

  /** When the user picks a version from the dropdown, update the image tag */
  const handleVersionChange = (newTag: string) => {
    const currentImage = localComp.image || "";
    // Replace the tag portion: "postgres:16-alpine" -> "postgres:15-alpine"
    const imageBase = currentImage.includes(":")
      ? currentImage.substring(0, currentImage.lastIndexOf(":"))
      : currentImage;
    handleFieldChange("image", `${imageBase}:${newTag}`);
  };

  const supportedVersions: string[] = localComp.supported_versions || [];
  const isTemplated = !!localComp.template_key;
  const versionWarning: string | null = localComp.version_warning || null;

  // Extract current tag from image
  const currentTag = localComp.image?.includes(":")
    ? localComp.image.split(":").pop()
    : "";

  return (
    <div className="flex flex-col h-full bg-slate-900 border-l border-slate-800 text-slate-200">
      <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900/50">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-lg">{localComp.name} Settings</h3>
          {isTemplated ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <CheckCircle2 size={12} /> Tested Template
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <AlertTriangle size={12} /> Custom (AI)
            </span>
          )}
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-white">
          <X size={20} />
        </button>
      </div>

      <div className="flex-grow p-5 space-y-6 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700">
        {/* Version Warning Banner */}
        {versionWarning && (
          <div className="flex items-start gap-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <AlertTriangle size={18} className="text-amber-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-amber-300">Version Compatibility</p>
              <p className="text-xs text-amber-200/80 mt-1">{versionWarning}</p>
            </div>
          </div>
        )}

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

            {/* Image + Version */}
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Image</label>
              {supportedVersions.length > 0 ? (
                <div className="flex gap-2">
                  <input
                    className="flex-grow bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2 text-slate-400"
                    value={
                      localComp.image?.includes(":")
                        ? localComp.image.substring(
                            0,
                            localComp.image.lastIndexOf(":"),
                          )
                        : localComp.image || ""
                    }
                    readOnly
                    title="Image base is managed by the template"
                  />
                  <select
                    className="w-36 bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                    value={currentTag}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                      handleVersionChange(e.target.value)
                    }
                  >
                    {supportedVersions.map((ver: string) => (
                      <option key={ver} value={ver}>
                        {ver}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <input
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2"
                  value={localComp.image || ""}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    handleFieldChange("image", e.target.value)
                  }
                />
              )}
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

      <div className="p-4 border-t border-slate-800 bg-slate-900/50 flex gap-2">
        <Button
          className="flex-1 bg-violet-600 hover:bg-violet-500 text-white flex items-center justify-center gap-2"
          onClick={handleSave}
        >
          <Save size={16} /> Save Changes
        </Button>
        {onDelete && (
          <Button
            variant="destructive"
            className="flex-none flex items-center justify-center gap-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20"
            onClick={onDelete}
          >
            <Trash2 size={16} /> Delete
          </Button>
        )}
      </div>
    </div>
  );
}
