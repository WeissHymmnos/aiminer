import { useEffect, useState } from "react";
import { getStoredToken } from "./api";

export type SocketEvent = Record<string, unknown>;

export function useSocketFeed() {
  const [events, setEvents] = useState<SocketEvent[]>([]);

  useEffect(() => {
    let active = true;
    let retry = 1000;
    let socket: WebSocket | null = null;
    let pingTimer = 0;
    let reconnectTimer = 0;

    function connect() {
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const token = getStoredToken();
      const query = token ? `?token=${encodeURIComponent(token)}` : "";
      socket = new WebSocket(`${protocol}://${window.location.host}/ws${query}`);
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
