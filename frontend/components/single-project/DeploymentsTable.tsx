'use client';

import { useState } from 'react';
import { CheckCircle2, XCircle, Clock, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface Deployment {
    id: number;
    version: string;
    date: string;
    status: 'Success' | 'Failed' | 'Building';
    duration: string;
    type: 'Current' | 'Previous';
    commit?: string;
    branch?: string;
}

const deployments: Deployment[] = [
    { id: 5, version: 'v1.5.0', date: '2025-11-25 10:30', status: 'Success', duration: '2 min', type: 'Current', commit: 'a3f2c1d', branch: 'main' },
    { id: 4, version: 'v1.4.1', date: '2025-11-20 18:45', status: 'Success', duration: '2 min', type: 'Previous', commit: 'b7e9f2a', branch: 'main' },
    { id: 3, version: 'v1.4.0', date: '2025-11-18 11:15', status: 'Failed', duration: '3 min', type: 'Previous', commit: 'c1d4e5f', branch: 'main' },
    { id: 2, version: 'v1.3.0', date: '2025-11-10 09:00', status: 'Success', duration: '1 min', type: 'Previous', commit: 'd8a2b3c', branch: 'main' },
    { id: 1, version: 'v1.2.5', date: '2025-11-05 14:22', status: 'Success', duration: '2 min', type: 'Previous', commit: 'e9f1a4d', branch: 'main' },
];

const ITEMS_PER_PAGE = 10;

export default function DeploymentsTable() {
    const [currentPage, setCurrentPage] = useState(1);
    
    const totalPages = Math.ceil(deployments.length / ITEMS_PER_PAGE);
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const endIndex = startIndex + ITEMS_PER_PAGE;
    const currentDeployments = deployments.slice(startIndex, endIndex);

    const getStatusIcon = (status: Deployment['status']) => {
        switch (status) {
            case 'Success':
                return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
            case 'Failed':
                return <XCircle className="w-4 h-4 text-red-500" />;
            case 'Building':
                return <Clock className="w-4 h-4 text-yellow-500 animate-spin" />;
        }
    };

    const getStatusBadge = (status: Deployment['status']) => {
        const variants = {
            Success: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
            Failed: 'bg-red-500/10 text-red-500 border-red-500/20',
            Building: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
        };
        
        return (
            <Badge variant="outline" className={`${variants[status]} flex items-center gap-1.5 px-2.5 py-0.5`}>
                {getStatusIcon(status)}
                <span className="font-medium">{status}</span>
            </Badge>
        );
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 60) return `${diffMins} minutes ago`;
        if (diffHours < 24) return `${diffHours} hours ago`;
        if (diffDays < 7) return `${diffDays} days ago`;
        
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    };

    return (
        <div className="space-y-4">
            {/* Table Container */}
            <div className="bg-slate-900/30 border border-slate-800 rounded-lg overflow-hidden">
                {/* Table Header */}
                <div className="bg-slate-900/50 border-b border-slate-800">
                    <div className="grid grid-cols-12 gap-4 px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        <div className="col-span-2">Version</div>
                        <div className="col-span-2">Status</div>
                        <div className="col-span-3">Deployed</div>
                        <div className="col-span-2">Duration</div>
                        <div className="col-span-2">Commit</div>
                        <div className="col-span-1 text-right">Actions</div>
                    </div>
                </div>

                {/* Table Body */}
                <div className="divide-y divide-slate-800">
                    {currentDeployments.map((deployment) => (
                        <div
                            key={deployment.id}
                            className="grid grid-cols-12 gap-4 px-6 py-4 hover:bg-slate-800/30 transition-colors group"
                        >
                            {/* Version */}
                            <div className="col-span-2 flex items-center gap-2">
                                <span className="text-slate-200 font-mono font-medium">
                                    {deployment.version}
                                </span>
                                {deployment.type === 'Current' && (
                                    <Badge className="bg-violet-600/20 text-violet-400 border-violet-600/30 text-[10px] px-1.5 py-0">
                                        LIVE
                                    </Badge>
                                )}
                            </div>

                            {/* Status */}
                            <div className="col-span-2 flex items-center">
                                {getStatusBadge(deployment.status)}
                            </div>

                            {/* Date */}
                            <div className="col-span-3 flex items-center">
                                <div className="flex flex-col">
                                    <span className="text-slate-300 text-sm">
                                        {formatDate(deployment.date)}
                                    </span>
                                    <span className="text-slate-500 text-xs">
                                        {deployment.date}
                                    </span>
                                </div>
                            </div>

                            {/* Duration */}
                            <div className="col-span-2 flex items-center">
                                <span className="text-slate-400 text-sm font-mono">
                                    {deployment.duration}
                                </span>
                            </div>

                            {/* Commit */}
                            <div className="col-span-2 flex items-center">
                                <div className="flex items-center gap-2">
                                    <code className="text-slate-400 bg-slate-800/50 px-2 py-1 rounded text-xs font-mono">
                                        {deployment.commit}
                                    </code>
                                    <span className="text-slate-500 text-xs">
                                        {deployment.branch}
                                    </span>
                                </div>
                            </div>

                            {/* Actions */}
                            <div className="col-span-1 flex items-center justify-end">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-slate-200"
                                >
                                    <ExternalLink className="w-4 h-4" />
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Empty State */}
                {currentDeployments.length === 0 && (
                    <div className="px-6 py-12 text-center">
                        <p className="text-slate-400 text-sm">No deployments found</p>
                    </div>
                )}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex items-center justify-between px-2">
                    <div className="text-sm text-slate-400">
                        Showing <span className="text-slate-200 font-medium">{startIndex + 1}</span> to{' '}
                        <span className="text-slate-200 font-medium">{Math.min(endIndex, deployments.length)}</span> of{' '}
                        <span className="text-slate-200 font-medium">{deployments.length}</span> deployments
                    </div>

                    <div className="flex items-center gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                            disabled={currentPage === 1}
                            className="bg-slate-900/30 border-slate-800 text-slate-300 hover:bg-slate-800 hover:text-white disabled:opacity-50"
                        >
                            <ChevronLeft className="w-4 h-4 mr-1" />
                            Previous
                        </Button>

                        <div className="flex items-center gap-1">
                            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                                <Button
                                    key={page}
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setCurrentPage(page)}
                                    className={`w-9 h-9 p-0 ${
                                        currentPage === page
                                            ? 'bg-violet-600 border-violet-600 text-white hover:bg-violet-700'
                                            : 'bg-slate-900/30 border-slate-800 text-slate-300 hover:bg-slate-800 hover:text-white'
                                    }`}
                                >
                                    {page}
                                </Button>
                            ))}
                        </div>

                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                            disabled={currentPage === totalPages}
                            className="bg-slate-900/30 border-slate-800 text-slate-300 hover:bg-slate-800 hover:text-white disabled:opacity-50"
                        >
                            Next
                            <ChevronRight className="w-4 h-4 ml-1" />
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}