

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import EnvFileEditor, { EnvVar } from '@/components/EnvFileEditor';
import { Save, AlertCircle } from 'lucide-react';

export default function EnvironmentVariableTab() {
    const [envVars, setEnvVars] = useState<EnvVar[]>([
        { key: 'DATABASE_URL', value: 'postgresql://localhost:5432/mydb' },
        { key: 'API_KEY', value: 'your-secret-api-key-here' },
        { key: 'NODE_ENV', value: 'production' },
    ]);
    const [isSaving, setIsSaving] = useState(false);
    const [saveSuccess, setSaveSuccess] = useState(false);

    const handleSave = async () => {
        setIsSaving(true);
        setSaveSuccess(false);
        
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        console.log('Saving environment variables:', envVars);
        
        setIsSaving(false);
        setSaveSuccess(true);
        
        // Hide success message after 3 seconds
        setTimeout(() => setSaveSuccess(false), 3000);
    };

    return (
        <div className="space-y-6 max-w-5xl">
            {/* Info Banner */}
            <div className="flex items-start gap-3 p-4 bg-blue-950/20 border border-blue-900/30 rounded-lg">
                <AlertCircle className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
                <div className="text-sm">
                    <p className="text-blue-300 font-medium mb-1">Environment Variables</p>
                    <p className="text-blue-400/80">
                        Environment variables are encrypted and securely stored. Changes will be applied on the next deployment.
                        Sensitive values are masked for security.
                    </p>
                </div>
            </div>

            {/* Environment Variables Editor */}
            <Card className="p-6 bg-slate-900/30 border-slate-800">
                <div className="space-y-6">
                    <div>
                        <h3 className="text-lg font-semibold text-white mb-1">Environment Variables</h3>
                        <p className="text-sm text-slate-400">
                            Configure environment variables for your application. You can import from a .env file or add them manually.
                        </p>
                    </div>

                    <EnvFileEditor value={envVars} onChange={setEnvVars} />

                    {/* Action Buttons */}
                    <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                        <div className="text-sm text-slate-400">
                            {envVars.length} {envVars.length === 1 ? 'variable' : 'variables'} configured
                        </div>
                        <div className="flex items-center gap-3">
                            {saveSuccess && (
                                <span className="text-sm text-green-400 flex items-center gap-2">
                                    <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                                    Changes saved successfully
                                </span>
                            )}
                            <Button
                                onClick={handleSave}
                                disabled={isSaving}
                                className="bg-violet-600 hover:bg-violet-700 text-white disabled:opacity-50"
                            >
                                {isSaving ? (
                                    <>
                                        <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2"></span>
                                        Saving...
                                    </>
                                ) : (
                                    <>
                                        <Save className="w-4 h-4 mr-2" />
                                        Save Changes
                                    </>
                                )}
                            </Button>
                        </div>
                    </div>
                </div>
            </Card>

            {/* Additional Info */}
            <Card className="p-4 bg-slate-900/20 border-slate-800">
                <div className="text-xs text-slate-400 space-y-2">
                    <p className="font-medium text-slate-300">Important Notes:</p>
                    <ul className="list-disc list-inside space-y-1 ml-2">
                        <li>Environment variables are only available at build time and runtime</li>
                        <li>Changes require a new deployment to take effect</li>
                        <li>Avoid committing sensitive values to your repository</li>
                        <li>Use descriptive names in UPPER_SNAKE_CASE format</li>
                    </ul>
                </div>
            </Card>
        </div>
    );
}