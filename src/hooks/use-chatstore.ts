import { Message } from '@/types/chat';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type booleanValue = 'isTyping' | 'isCopied';

interface ChatStore {
  messages: Message[];
  shouldFetch: boolean;

  setChat: (value: Message[]) => void;
  addChat: (value: Message) => void;
  setFetch: (value: boolean) => void;
  setBoolean: (id: string, key: booleanValue, value: boolean) => void;
  resetChat: () => void;
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set) => ({
      messages: [],
      shouldFetch: false,

      setChat: (values) => set({ messages: values }),
      addChat: (value) =>
        set(({ messages }) => ({ messages: [...messages, value] })),
      setFetch: (value) => set({ shouldFetch: value }),
      setBoolean: (id, key, value) =>
        set(({ messages }) => {
          const updatedMessages = messages.map((message) =>
            message.id === id ? { ...message, [key]: value } : message
          );

          return { messages: updatedMessages };
        }),
      resetChat: () =>
        set({
          messages: []
        })
    }),
    {
      name: 'combiphar-chats'
    }
  )
);
