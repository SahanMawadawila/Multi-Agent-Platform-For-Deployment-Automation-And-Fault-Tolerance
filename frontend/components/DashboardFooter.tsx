import {
    Globe,
    Server
} from 'lucide-react';

export default function DashboardFooter() {
    return (
        <footer className="border-t border-slate-900 py-6 bg-slate-950 mt-12">
            <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">

                {/* Copyright and Location */}
                <div className="flex items-center gap-4">
                    <p className="text-xs text-slate-500">
                        © 2024 FlowPilot | San Francisco, CA
                    </p>
                    {/* Simplified Links */}
                    <div className="flex gap-3">
                        <Globe size={18} className="text-slate-600 hover:text-white cursor-pointer" />
                        <Server size={18} className="text-slate-600 hover:text-white cursor-pointer" />
                    </div>
                </div>

                {/* System Status */}
                <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse"></div>
                    <span className="text-xs text-slate-400">All Systems Normal</span>
                </div>
            </div>
        </footer>
    );
}