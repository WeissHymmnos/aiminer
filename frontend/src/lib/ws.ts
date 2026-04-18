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

  useEffect(() => {
    let active = true;
    let retry = 1000;
    let socket: WebSocket | null = null;
    let pingTimer = 0;
    let reconnectTimer = 0;

    function connect() {
      const token = getStoredToken();
      const query = token ? `?token=${encodeURIComponent(token)}` : "";
      socket = new WebSocket(`${getSocketOrigin()}/ws${query}`);
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as SocketEvent;
          setEvents((previous) => [...previous.slice(-499), payload]);
          retry = 1000;
        } catch {
          return;
        }
      };
      socket.onopen = () => {
        pingTimer = window.setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) {
            socket.send("ping");
          }
        }, 15000);
      };
      socket.onclose = () => {
        window.clearInterval(pingTimer);
        if (!active) {
          return;
        }
        reconnectTimer = window.setTimeout(connect, retry);
        retry = Math.min(retry * 2, 10000);
      };
      socket.onerror = () => {
        socket?.close();
      };
    }

    connect();
    return () => {
      active = false;
      window.clearInterval(pingTimer);
      window.clearTimeout(reconnectTimer);
      if (socket) {
        socket.close();
      }
    };
  }, []);

  return events;
}
