import { useEffect, useState } from "react";
import { getStoredToken } from "./api";

export type SocketEvent = Record<string, unknown>;

function trimTrailingSlash(value: string) {
  return value.replace(/\/+$/, "");
}

function getSocketOrigin() {
  const configuredWsBase = import.meta.env.VITE_WS_BASE_URL?.trim();
  if (configuredWsBase) {
    return trimTrailingSlash(configuredWsBase);
  }

  const configuredApiBase = import.meta.env.VITE_API_BASE_URL?.trim();
  if (configuredApiBase) {
    try {
      const apiUrl = new URL(configuredApiBase);
      apiUrl.protocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
      return apiUrl.origin;
    } catch {
      // Relative API bases should continue to use the current origin.
    }
  }

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${window.location.host}`;
}

export function useSocketFeed() {
  const [events, setEvents] = useState<SocketEvent[]>([]);
  const [status, setStatus] = useState<"connecting" | "open" | "closed">("connecting");

  useEffect(() => {
    let active = true;
    let retry = 1000;
    let socket: WebSocket | null = null;
    let pingTimer: any = 0;
    let reconnectTimer: any = 0;

    function connect() {
      const token = getStoredToken();
      const query = token ? `?token=${encodeURIComponent(token)}` : "";
      const url = `${getSocketOrigin()}/ws${query}`;
      
      console.log(`[WebSocket] Connecting to ${getSocketOrigin()}/ws...`);
      setStatus("connecting");
      
      socket = new WebSocket(url);
      
      socket.onmessage = (event) => {
        if (event.data === "pong") return;
        try {
          const payload = JSON.parse(event.data) as SocketEvent;
          setEvents((previous) => {
            const next = [...previous, payload];
            return next.length > 500 ? next.slice(-500) : next;
          });
          retry = 1000;
        } catch (e) {
          console.warn("[WebSocket] Failed to parse message", e);
        }
      };

      socket.onopen = () => {
        console.log("[WebSocket] Connection established");
        setStatus("open");
        retry = 1000;
        pingTimer = window.setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) {
            socket.send("ping");
          }
        }, 15000);
      };

      socket.onclose = (event) => {
        setStatus("closed");
        window.clearInterval(pingTimer);
        if (!active) return;
        
        console.log(`[WebSocket] Closed (code: ${event.code}). Retrying in ${retry}ms...`);
        reconnectTimer = window.setTimeout(connect, retry);
        retry = Math.min(retry * 2, 15000);
      };

      socket.onerror = (error) => {
        console.error("[WebSocket] Error occurred", error);
        socket?.close();
      };
    }

    connect();
    return () => {
      active = false;
      window.clearInterval(pingTimer);
      window.clearTimeout(reconnectTimer);
      if (socket) socket.close();
    };
  }, []);

  return { events, status };
}
