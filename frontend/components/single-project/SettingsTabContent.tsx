

'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Github, AlertTriangle, Save, Trash2 } from 'lucide-react';
import { DetailedProject } from '@/types/project';

export default function SettingsTabContent({project}: {project: DetailedProject}) {
    const [projectName, setProjectName] = useState('My Awesome Project');
    const [domainName, setDomainName] = useState('');
    const [githubUrl, setGithubUrl] = useState('https://github.com/username/repo');
    const [autoDeployment, setAutoDeployment] = useState(true);
    const [deleteConfirm, setDeleteConfirm] = useState('');
    const [showDeleteDialog, setShowDeleteDialog] = useState(false);

    useEffect(() => {
        // Load initial project settings
        setProjectName(project.project_name);
        setDomainName(project.domain_name || ''); // Assume we fetch this from project data
        setGithubUrl(project.github_url || '');
        setAutoDeployment(project.is_auto_deploy_enabled); // Assume we fetch this from project data
    }, [project]);

    const handleSaveGeneral = () => {
        // Save general settings
        console.log('Saving general settings:', { projectName, domainName });
    };

    const handleSaveGitSettings = () => {
        // Save git settings
        console.log('Saving git settings:', { githubUrl, autoDeployment });
    };

    const handleDeleteProject = () => {
        if (deleteConfirm === projectName) {
            console.log('Deleting project...');
            // Delete project logic
        }
    };

    return (
        <div className="space-y-8 max-w-4xl">
            {/* General Settings */}
            <Card className="p-6 bg-slate-900/30 border-slate-800">
                <div className="space-y-6">
                    <div>
                        <h3 className="text-lg font-semibold text-white mb-1">General Settings</h3>
                        <p className="text-sm text-slate-400">Configure your project's basic information</p>
                    </div>

                    <div className="space-y-4">
                        {/* Project Name */}
                        <div>
                            <label htmlFor="projectName" className="block text-sm font-medium text-slate-300 mb-2">
                                Project Name
                            </label>
                            <input
                                id="projectName"
                                type="text"
                                value={projectName}
                                onChange={(e) => setProjectName(e.target.value)}
                                className="w-full px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-600 focus:border-transparent transition-all"
                                placeholder="Enter project name"
                            />
                        </div>

                        {/* Domain Name */}
                        <div>
                            <label htmlFor="domainName" className="block text-sm font-medium text-slate-300 mb-2">
                                Custom Domain <span className="text-slate-500">(Optional)</span>
                            </label>
                            <input
                                id="domainName"
                                type="text"
                                value={domainName}
                                onChange={(e) => setDomainName(e.target.value)}
                                className="w-full px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-600 focus:border-transparent transition-all"
                                placeholder="example.com"
                            />
                            <p className="text-xs text-slate-500 mt-2">
                                Point your domain's DNS to our servers to use a custom domain
                            </p>
                        </div>
                    </div>

                    <div className="flex justify-end pt-2">
                        <Button
                            onClick={handleSaveGeneral}
                            className="bg-violet-600 hover:bg-violet-700 text-white"
                        >
                            <Save className="w-4 h-4 mr-2" />
                            Save Changes
                        </Button>
                    </div>
                </div>
            </Card>

            {/* Git & Deployment Settings */}
            <Card className="p-6 bg-slate-900/30 border-slate-800">
                <div className="space-y-6">
                    <div>
                        <h3 className="text-lg font-semibold text-white mb-1">Git & Deployment</h3>
                        <p className="text-sm text-slate-400">Manage your repository and deployment settings</p>
                    </div>

                    <div className="space-y-4">
                        {/* GitHub URL */}
                        <div>
                            <label htmlFor="githubUrl" className="block text-sm font-medium text-slate-300 mb-2">
                                GitHub Repository URL
                            </label>
                            <div className="relative">
                                <Github className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                                <input
                                    id="githubUrl"
                                    type="text"
                                    value={githubUrl}
                                    onChange={(e) => setGithubUrl(e.target.value)}
                                    className="w-full pl-11 pr-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-600 focus:border-transparent transition-all"
                                    placeholder="https://github.com/username/repository"
                                />
                            </div>
                            <p className="text-xs text-slate-500 mt-2">
                                Changes to this URL may require reconnecting your repository
                            </p>
                        </div>

                        {/* Auto Deployment Toggle */}
                        <div className="flex items-center justify-between p-4 bg-slate-800/30 border border-slate-700 rounded-lg">
                            <div className="flex-1">
                                <div className="flex items-center gap-2">
                                    <h4 className="text-sm font-medium text-white">Automatic Deployments</h4>
                                    <span className={`text-xs px-2 py-0.5 rounded-full ${autoDeployment ? 'bg-green-500/20 text-green-400' : 'bg-slate-700 text-slate-400'}`}>
                                        {autoDeployment ? 'Enabled' : 'Disabled'}
                                    </span>
                                </div>
                                <p className="text-xs text-slate-400 mt-1">
                                    Automatically deploy when you push to the main branch
                                </p>
                            </div>
                            <button
                                onClick={() => setAutoDeployment(!autoDeployment)}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-violet-600 focus:ring-offset-2 focus:ring-offset-slate-900 ${
                                    autoDeployment ? 'bg-violet-600' : 'bg-slate-700'
                                }`}
                            >
                                <span
                                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                                        autoDeployment ? 'translate-x-6' : 'translate-x-1'
                                    }`}
                                />
                            </button>
                        </div>
                    </div>

                    <div className="flex justify-end pt-2">
                        <Button
                            onClick={handleSaveGitSettings}
                            className="bg-violet-600 hover:bg-violet-700 text-white"
                        >
                            <Save className="w-4 h-4 mr-2" />
                            Save Changes
                        </Button>
                    </div>
                </div>
            </Card>

            {/* Danger Zone */}
            <Card className="p-6 bg-red-950/10 border-red-900/50">
                <div className="space-y-6">
                    <div className="flex items-start gap-3">
                        <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                        <div>
                            <h3 className="text-lg font-semibold text-red-500 mb-1">Danger Zone</h3>
                            <p className="text-sm text-slate-400">
                                Irreversible and destructive actions. Please proceed with caution.
                            </p>
                        </div>
                    </div>

                    {!showDeleteDialog ? (
                        <div className="flex items-center justify-between p-4 bg-slate-900/50 border border-red-900/30 rounded-lg">
                            <div>
                                <h4 className="text-sm font-medium text-white mb-1">Delete Project</h4>
                                <p className="text-xs text-slate-400">
                                    Once deleted, this project and all its data will be permanently removed
                                </p>
                            </div>
                            <Button
                                onClick={() => setShowDeleteDialog(true)}
                                variant="outline"
                                className="border-red-900/50 text-red-500 hover:bg-red-950/50 hover:text-red-400"
                            >
                                <Trash2 className="w-4 h-4 mr-2" />
                                Delete Project
                            </Button>
                        </div>
                    ) : (
                        <div className="space-y-4 p-4 bg-slate-900/50 border border-red-900/50 rounded-lg">
                            <div>
                                <h4 className="text-sm font-medium text-white mb-2">Confirm Project Deletion</h4>
                                <p className="text-xs text-slate-400 mb-3">
                                    This action <span className="font-semibold text-red-500">cannot be undone</span>. 
                                    This will permanently delete the project, deployments, and all associated data.
                                </p>
                                <p className="text-xs text-slate-300 mb-2">
                                    Please type <code className="px-2 py-0.5 bg-slate-800 rounded text-violet-400 font-mono">{projectName}</code> to confirm:
                                </p>
                                <input
                                    type="text"
                                    value={deleteConfirm}
                                    onChange={(e) => setDeleteConfirm(e.target.value)}
                                    className="w-full px-4 py-2 bg-slate-800/50 border border-red-900/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-red-600 focus:border-transparent transition-all"
                                    placeholder="Type project name to confirm"
                                />
                            </div>
                            <div className="flex gap-3 justify-end">
                                <Button
                                    onClick={() => {
                                        setShowDeleteDialog(false);
                                        setDeleteConfirm('');
                                    }}
                                    variant="outline"
                                    className="border-slate-700 text-slate-300 hover:bg-slate-800"
                                >
                                    Cancel
                                </Button>
                                <Button
                                    onClick={handleDeleteProject}
                                    disabled={deleteConfirm !== projectName}
                                    className="bg-red-600 hover:bg-red-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    <Trash2 className="w-4 h-4 mr-2" />
                                    Delete Project Permanently
                                </Button>
                            </div>
                        </div>
                    )}
                </div>
            </Card>
        </div>
    );
}