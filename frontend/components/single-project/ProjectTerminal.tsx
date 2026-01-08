

'use client';

import { useState, useEffect, useRef, memo, useCallback } from 'react';
import * as terminal from '@xterm/xterm';
// import { WebLinksAddon } from '@xterm/addon-web-links';

import '@xterm/xterm/css/xterm.css';
import './TerminalStyles.css';
import { useTerminalSocket } from './TerminalSocketContext';

function ProjectTerminal_() {
    // const [isConnected, setIsConnected] = useState(true);
    const terminalContentRef = useRef<HTMLDivElement>(null);
    const termRef = useRef<terminal.Terminal | null>(null);
    const { socket, isConnected, connect } = useTerminalSocket();

    const writeToTerminal = useCallback((line: string) => {
        if (!terminalContentRef.current) return;
        if (!termRef.current) {
            // Calculate number of rows based on container height
            const containerHeight = terminalContentRef.current.clientHeight;
            const approxRowHeight = 18; // Approximate height of a terminal row in pixels
            const rows = Math.floor(containerHeight / approxRowHeight) - 1;

            const term = new terminal.Terminal({
                rows,
                theme: {
                    background: '#040A1D00',
                },
                
            });
            // term.loadAddon(new WebLinksAddon());
            term.open(terminalContentRef.current);
            term.clear();
            termRef.current = term;
        }
        termRef.current.write(line);
    }, []);

    useEffect(() => {
        if (isConnected) return;
        
        const onmessage = (event: MessageEvent) => {
            writeToTerminal(event.data);
        };
        connect(onmessage);
    }, [isConnected, connect]);

    useEffect(() => {
        writeToTerminal('\x1b[32m>\x1b[0m\r\n');
    }, [writeToTerminal]);

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
                ref={terminalContentRef}
                className="flex-1 overflow-y-auto p-4 font-mono text-sm leading-relaxed scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-slate-900"
            >
            </div>

            {/* Terminal Footer */}
            <div className="bg-slate-800 border-t border-slate-700 px-4 py-2 text-xs text-gray-400 flex justify-between">
                <button className="hover:text-white cursor-pointer">Clear Terminal</button>
            </div>
        </div>
    );
}

// Export memoized component to prevent unnecessary re-renders
export default memo(ProjectTerminal_);