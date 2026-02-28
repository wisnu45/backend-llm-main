/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { io } from 'socket.io-client';

export const useSocket = (topic: string) => {
  const [isConnected, setIsConnected] = React.useState<boolean>(false);
  const [messages, setMessages] = React.useState<any>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const socketIo = io(import.meta.env.VITE_SOCKET_ENDPOINT);

    socketIo.on(topic, (message) => {
      setMessages(message);
    });

    socketIo.on('connect', () => {
      setIsConnected(true);
    });

    socketIo.on('connect_error', (err) => {
      setError(err.message);
    });

    return () => {
      socketIo.disconnect();
      setIsConnected(false);
    };
  }, [topic]);

  return { messages, error, isConnected };
};
