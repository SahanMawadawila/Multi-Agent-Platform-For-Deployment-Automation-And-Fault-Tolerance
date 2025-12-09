

'use client';

import React, { useState, useEffect, useRef } from 'react';

interface TerminalLine {
    id: string;
    content: string;
    type: 'output' | 'error' | 'success' | 'info' | 'input';
    timestamp: Date;
}

// Sample terminal data - replace with WebSocket data later
const SAMPLE_TERMINAL_OUTPUT: TerminalLine[] = [
    {
        id: '1',
        content: '$ npm run build',
        type: 'input',
        timestamp: new Date(Date.now() - 5000),
    },
    {
        id: '2',
        content: '> myapp@1.0.0 build /home/user/projects/myapp',
        type: 'output',
        timestamp: new Date(Date.now() - 4800),
    },
    {
        id: '3',
        content: '> next build',
        type: 'output',
        timestamp: new Date(Date.now() - 4600),
    },
    {
        id: '4',
        content: '',
        type: 'output',
        timestamp: new Date(Date.now() - 4400),
    },
    {
        id: '5',
        content: '▲ Next.js 14.0.0',
        type: 'success',
        timestamp: new Date(Date.now() - 4200),
    },
    {
        id: '6',
        content: '',
        type: 'output',
        timestamp: new Date(Date.now() - 4000),
    },
    {
        id: '7',
        content: '  Creating an optimized production build ...',
        type: 'info',
        timestamp: new Date(Date.now() - 3800),
    },
    {
        id: '8',
        content: '  ✓ Compiled successfully',
        type: 'success',
        timestamp: new Date(Date.now() - 2000),
    },
    {
        id: '9',
        content: '',
        type: 'output',
        timestamp: new Date(Date.now() - 1800),
    },
    {
        id: '10',
        content: '  Linting and checking validity of types...',
        type: 'info',
        timestamp: new Date(Date.now() - 1600),
    },
    {
        id: '11',
        content: '  ✓ Types validated',
        type: 'success',
        timestamp: new Date(Date.now() - 500),
    },
];

export default function ProjectTerminal() {
    const [logs, setLogs] = useState<TerminalLine[]>(SAMPLE_TERMINAL_OUTPUT);
    const [isConnected, setIsConnected] = useState(true);
    const scrollContainerRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new logs arrive
    useEffect(() => {
        if (scrollContainerRef.current) {
            scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
        }
    }, [logs]);

    // Simulated WebSocket connection setup
    // Replace this with actual WebSocket connection using projectId
    useEffect(() => {
        // const ws = new WebSocket(`ws://your-backend/terminal?projectId=${projectId}`);
        // ws.onmessage = (event) => {
        //     const newLog: TerminalLine = {
        //         id: Date.now().toString(),
        //         content: event.data,
        //         type: 'output',
        //         timestamp: new Date(),
        //     };
        //     setLogs(prev => [...prev, newLog]);
        // };
        // ws.onopen = () => setIsConnected(true);
        // ws.onclose = () => setIsConnected(false);
        // return () => ws.close();
    }, []);

    const getLineColor = (type: TerminalLine['type']) => {
        switch (type) {
            case 'error':
                return 'text-red-400';
            case 'success':
                return 'text-green-400';
            case 'info':
                return 'text-blue-400';
            case 'input':
                return 'text-yellow-300';
            default:
                return 'text-gray-300';
        }
    };

    const formatTimestamp = (date: Date) => {
        return date.toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
    };

    return (
        <div className="w-full h-full max-h-[600px] flex flex-col bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 rounded-lg border border-slate-700 shadow-2xl overflow-hidden">
            {/* Terminal Header */}
            <div className="bg-gradient-to-r from-slate-800 to-slate-850 border-b border-slate-700 px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <span className="text-gray-300 text-sm font-medium ml-2">Terminal</span>
                </div>
                <div className="flex items-center gap-2">
                    <div
                        className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}
                    ></div>
                    <span className="text-xs text-gray-400">{isConnected ? 'Live' : 'Disconnected'}</span>
                </div>
            </div>

            {/* Terminal Content */}
            <div
                ref={scrollContainerRef}
                className="flex-1 overflow-y-auto p-4 font-mono text-sm leading-relaxed scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-slate-900"
            >
                <div className="space-y-0">
                    {logs.map((line) => (
                        <div
                            key={line.id}
                            className={`flex gap-3 group hover:bg-slate-800/50 px-2 py-1 rounded transition-colors ${getLineColor(line.type)}`}
                        >
                            <span className="text-slate-500 text-xs pt-0.5 flex-shrink-0 group-hover:text-slate-400">
                                {formatTimestamp(line.timestamp)}
                            </span>
                            <span className="flex-1 break-words whitespace-pre-wrap">
                                {line.content || '\u00A0'}
                            </span>
                        </div>
                    ))}
                </div>

                {/* Blinking cursor */}
                <div className="flex gap-3 mt-2">
                    <span className="text-slate-500 text-xs pt-0.5 flex-shrink-0">
                        {formatTimestamp(new Date())}
                    </span>
                    <span className="text-green-400 animate-pulse">▌</span>
                </div>
            </div>

            {/* Terminal Footer */}
            <div className="bg-slate-800 border-t border-slate-700 px-4 py-2 text-xs text-gray-400 flex justify-between">
                <div>{logs.length} lines</div>
            </div>
        </div>
    );
}