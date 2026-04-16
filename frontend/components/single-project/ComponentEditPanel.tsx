import React, { useState, useEffect } from 'react';
import { X, Save, Plus, Trash2 } from 'lucide-react';
import { Button } from '../ui/button';

interface ComponentEditPanelProps {
    component: any;
    onUpdate: (comp: any) => void;
    onClose: () => void;
}

export function ComponentEditPanel({ component, onUpdate, onClose }: ComponentEditPanelProps) {
    const [localComp, setLocalComp] = useState<any>(JSON.parse(JSON.stringify(component)));

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
        handleFieldChange('env_variables', newEnvs);
    };

    const removeEnv = (index: number) => {
        const newEnvs = [...(localComp.env_variables || [])];
        newEnvs.splice(index, 1);
        handleFieldChange('env_variables', newEnvs);
    };

    const addEnv = () => {
        const newEnvs = [...(localComp.env_variables || []), { key: '', value: '', source: 'override', editable: true, sensitive: false }];
        handleFieldChange('env_variables', newEnvs);
    };

    return (
        <div className="flex flex-col h-full bg-slate-900 border-l border-slate-800 text-slate-200">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900/50">
                <h3 className="font-semibold text-lg">{localComp.name} Settings</h3>
                <button onClick={onClose} className="text-slate-400 hover:text-white">
                    <X size={20} />
                </button>
            </div>

            {/* Scrollable Content */}
            <div className="flex-grow p-5 space-y-6 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700">
                {/* General Settings */}
                <div className="space-y-4">
                    <h4 className="text-sm font-semibold tracking-wider text-slate-400 uppercase">General</h4>
                    <div className="space-y-3">
                        <div>
                            <label className="text-xs text-slate-400 mb-1 block">Role</label>
                            <input 
                                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2 focus:outline-none focus:ring-1 focus:ring-violet-500"
                                value={localComp.role || localComp.category || ''} 
                                readOnly 
                            />
                        </div>
                        <div>
                            <label className="text-xs text-slate-400 mb-1 block">Port</label>
                            <input 
                                type="number"
                                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2 focus:outline-none focus:ring-1 focus:ring-violet-500"
                                value={localComp.port || ''} 
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange('port', parseInt(e.target.value))}
                            />
                        </div>
                        
                        {localComp.type === 'application' && (
                            <>
                                <div>
                                    <label className="text-xs text-slate-400 mb-1 block">Build Command</label>
                                    <input 
                                        className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2 focus:outline-none focus:ring-1 focus:ring-violet-500"
                                        value={localComp.build_command || ''} 
                                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange('build_command', e.target.value)}
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-slate-400 mb-1 block">Run Command</label>
                                    <input 
                                        className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2 focus:outline-none focus:ring-1 focus:ring-violet-500"
                                        value={localComp.run_command || ''} 
                                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange('run_command', e.target.value)}
                                    />
                                </div>
                            </>
                        )}
                        {localComp.type === 'infrastructure' && (
                            <div>
                                <label className="text-xs text-slate-400 mb-1 block">Image</label>
                                <input 
                                    className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2 focus:outline-none focus:ring-1 focus:ring-violet-500"
                                    value={localComp.image || ''} 
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleFieldChange('image', e.target.value)}
                                />
                            </div>
                        )}
                    </div>
                </div>

                {/* Resource Limits */}
                <div className="space-y-4">
                    <h4 className="text-sm font-semibold tracking-wider text-slate-400 uppercase">Resources</h4>
                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="text-xs text-slate-400 mb-1 block">CPU Limit</label>
                            <input 
                                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2 focus:outline-none focus:ring-1 focus:ring-violet-500"
                                value={localComp.resources?.cpu_limit || ''} 
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setLocalComp((prev: any) => ({
                                    ...prev, resources: { ...prev.resources, cpu_limit: e.target.value }
                                }))}
                            />
                        </div>
                        <div>
                            <label className="text-xs text-slate-400 mb-1 block">Memory</label>
                            <input 
                                className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-sm h-8 px-2 focus:outline-none focus:ring-1 focus:ring-violet-500"
                                value={localComp.resources?.memory_limit || ''} 
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setLocalComp((prev: any) => ({
                                    ...prev, resources: { ...prev.resources, memory_limit: e.target.value }
                                }))}
                            />
                        </div>
                    </div>
                </div>

                {/* Environment Variables */}
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <h4 className="text-sm font-semibold tracking-wider text-slate-400 uppercase">Environment</h4>
                        <button onClick={addEnv} className="text-violet-400 hover:text-violet-300 text-xs flex items-center gap-1">
                            <Plus size={14} /> Add
                        </button>
                    </div>
                    <div className="space-y-2">
                        {(localComp.env_variables || []).map((env: any, i: number) => (
                            <div key={i} className="flex gap-2 items-start">
                                <div className="flex-grow space-y-2">
                                    <input 
                                        placeholder="Key"
                                        className="w-full bg-slate-800/50 border border-slate-700 rounded-md text-xs h-8 px-2 font-mono focus:outline-none focus:ring-1 focus:ring-violet-500"
                                        value={env.key} 
                                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleEnvChange(i, 'key', e.target.value)}
                                        readOnly={env.source === 'auto_generate'}
                                    />
                                    <input 
                                        placeholder={env.source === 'auto_generate' ? 'Auto-generated by system' : 'Value'}
                                        type={env.sensitive ? "password" : "text"}
                                        className={`w-full bg-slate-800/50 border border-slate-700 rounded-md text-xs h-8 px-2 font-mono focus:outline-none focus:ring-1 focus:ring-violet-500 ${env.source === 'auto_generate' ? 'text-slate-500 italic' : ''}`}
                                        value={env.value} 
                                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleEnvChange(i, 'value', e.target.value)}
                                        readOnly={env.source === 'auto_generate'}
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
                        {(!localComp.env_variables || localComp.env_variables.length === 0) && (
                            <p className="text-xs text-slate-500 italic text-center py-2">No environment variables.</p>
                        )}
                    </div>
                </div>

            </div>

            {/* Footer */}
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
