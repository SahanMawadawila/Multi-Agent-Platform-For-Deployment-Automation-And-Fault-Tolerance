"use client";
import React, { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";

export type EnvVar = { key: string; value: string };

function parseEnvFile(content: string): EnvVar[] {
  return content
    .split(/\r?\n/)
    .filter(line => line.trim() && !line.trim().startsWith('#'))
    .map(line => {
      const eqIdx = line.indexOf('=');
      if (eqIdx === -1) return { key: line.trim(), value: '' };
      return {
        key: line.slice(0, eqIdx).trim(),
        value: line.slice(eqIdx + 1).trim(),
      };
    });
}

export default function EnvFileEditor({ value, onChange }: {
  value: EnvVar[];
  onChange: (vars: EnvVar[]) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState('');

  const handleFileImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    setError('');
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = parseEnvFile(text);
      onChange(parsed);
    } catch {
      setError('Failed to parse env file.');
    }
  };

  const handleAdd = () => {
    onChange([...value, { key: '', value: '' }]);
  };

  const handleEdit = (idx: number, field: 'key'|'value', val: string) => {
    const updated = value.map((v, i) => i === idx ? { ...v, [field]: val } : v);
    onChange(updated);
  };

  const handleRemove = (idx: number) => {
    onChange(value.filter((_, i) => i !== idx));
  };

  return (
    <div className="space-y-4">
      {/* Section 1: Import env file */}
      <div>
        <label className="block text-sm font-medium mb-1">Import .env File</label>
        <input
          type="file"
          accept=".env,text/plain"
          ref={fileInputRef}
          onChange={handleFileImport}
          className="block w-full text-sm text-slate-300 bg-slate-800 border border-slate-700 rounded px-2 py-1"
        />
        {error && <div className="text-red-400 text-xs mt-1">{error}</div>}
      </div>
      {/* Section 2: Add/Edit/Remove env variables */}
      <div>
        <label className="block text-sm font-medium mb-2">Environment Variables</label>
        <div className="space-y-2">
          {value.map((env, idx) => (
            <div key={idx} className="flex gap-2 items-center">
              <input
                type="text"
                placeholder="Name"
                value={env.key}
                onChange={e => handleEdit(idx, 'key', e.target.value)}
                className="px-2 py-1 rounded bg-slate-800 text-white border border-slate-700 w-1/3"
              />
              <input
                type="text"
                placeholder="Value"
                value={env.value}
                onChange={e => handleEdit(idx, 'value', e.target.value)}
                className="px-2 py-1 rounded bg-slate-800 text-white border border-slate-700 w-1/2"
              />
              <Button 
                type="button" 
                size="sm" 
                variant="ghost"
                onClick={() => handleRemove(idx)}
                className="text-red-500 hover:text-red-400 hover:bg-red-950/30 cursor-pointer"
                title="Remove"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          ))}
        </div>
        <Button type="button" size="sm" className="mt-2" onClick={handleAdd}>
          Add Variable
        </Button>
      </div>
    </div>
  );
}
