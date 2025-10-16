import { ChatItemData } from '@/pages/(protected)/chat/component/types';

export interface Result {
  answer: string;
  source_documents: SourceDocument[];
}

export interface SourceDocument {
  content: string;
  metadata: Metadata;
}

export interface Metadata {
  page: number;
  source: string;
}

export interface TChatRequest {
  question: string;
  chat_id?: string;
  is_browse: boolean;
  is_company: boolean;
  is_general: boolean;
  attachments?: File[];
  with_documents?: File[];
}

export interface TChatResponseRequest {
  feedback: number | string;
  chat_id: string;
}

export interface TClearChatRequest {
  chat_id: string;
}

export interface TDeleteBulkChatRequest {
  chat_ids: string[];
}

export interface TRenameChatRequest {
  chat_id: string;
  title: string;
}

export interface TPinChatRequest {
  chat_id: string;
  pinned: boolean;
}

export type TRecentChats = {
  chat_id: string;
  title: string;
  id: string;
  pinned: boolean;
};
export interface TGetHistoryRequest {
  data: TRecentChats[];
  message: string;
}

export interface TNewSesionResponse {
  message: string;
  chat_id: string;
  user_id: string;
  data: {
    message: string;
    chat_id: string;
  };
}

export type TChatResponse = {
  chat_id: string;
};
export interface TGetDetailHistoryData {
  data: ChatItemData[];
  chat_id: string;
  message: string;
}
