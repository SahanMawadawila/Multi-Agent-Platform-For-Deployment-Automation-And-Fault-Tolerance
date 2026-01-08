'use client';

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

interface TerminalSocketContextValue {
    socket: WebSocket | null;
    isConnected: boolean;
    connect: (onmessage: (event: MessageEvent) => void) => void;
}

const TerminalSocketContext = createContext<TerminalSocketContextValue | null>(null);

export function useTerminalSocket() {
    const ctx = useContext(TerminalSocketContext);
    if (!ctx) {
        throw new Error("useTerminalSocket must be used within TerminalSocketProvider");
    }
    return ctx;
}

export function TerminalSocketProvider({
    children,
    projectId,
    accessToken,
}: {
    children: React.ReactNode;
    projectId: string;
    accessToken: string;
}) {
    const socketRef = useRef<WebSocket | null>(null);
    const connectDebouncedRef = useRef<NodeJS.Timeout | null>(null);
    const [socket, setSocket] = useState<WebSocket | null>(null);
    const [isConnected, setIsConnected] = useState(false);

    const connect = useCallback((onmessage: (event: MessageEvent) => void) => {
        if (!projectId || !accessToken) {
            console.error('Project ID or access token is missing for terminal websocket connection');
            return;
        }
        if (connectDebouncedRef.current) {
            clearTimeout(connectDebouncedRef.current);
        }

        connectDebouncedRef.current = setTimeout(async () => {
            if (socketRef.current) {
                // forcefully close existing connection
                socketRef.current.close();
                socketRef.current = null;
                // setSocket(null);
                // setIsConnected(false);
            }

            // get the auth cookie from document cookies
            const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/ws/terminal/authorize/${projectId}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                },
            });
            if (!response.ok) {
                console.error('Failed to authorize terminal websocket');
                return;
            }

            const data = await response.json();
            if (!data.ws_auth_token) {
                console.error('No token received for terminal websocket');
                return;
            }
            
            const ws = new WebSocket(
                `${process.env.NEXT_PUBLIC_TERMINAL_URL}/${projectId}?token=${data.ws_auth_token}`,
            );

            socketRef.current = ws;
            setSocket(ws);

            ws.onmessage = onmessage;
            ws.onopen = () => setIsConnected(true);
            ws.onclose = () => {
                setIsConnected(false);
                socketRef.current = null;
                setSocket(null);
            };

        }, 1500);
    }, [projectId, accessToken]);

    useEffect(() => {
        return () => {
            if (connectDebouncedRef.current) {
                clearTimeout(connectDebouncedRef.current);
            }
        };
    }, [projectId]);

    return (
        <TerminalSocketContext.Provider value={{ socket, isConnected, connect }}>
            {children}
        </TerminalSocketContext.Provider>
    );
}
