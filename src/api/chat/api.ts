import api from '@/lib/api';

import {
  TChatRequest,
  TChatResponseRequest,
  TClearChatRequest,
  TDeleteBulkChatRequest,
  TGetDetailHistoryData,
  TGetHistoryRequest,
  TNewSesionResponse,
  TRenameChatRequest,
  TPinChatRequest
} from './type';
import { TDefaultResponse } from '@/commons/types/response';

export const chat = async (req: TChatRequest): Promise<TDefaultResponse> => {
  const res = await api.post<TDefaultResponse>('/chats/ask', req);
  return res.data;
};

export const chatFeedback = async (
  req: TChatResponseRequest
): Promise<TDefaultResponse> => {
  const res = await api.patch<TDefaultResponse>(
    `/chats/feedback/${req.chat_id}`,
    {
      feedback: req.feedback
    }
  );
  return res.data;
};

export const clearChat = async (
  req: TClearChatRequest
): Promise<TDefaultResponse> => {
  const res = await api.delete<TDefaultResponse>(`/chats/${req.session_id}`);
  return res.data;
};

export const newChat = async (): Promise<TNewSesionResponse> => {
  const res = await api.get<TNewSesionResponse>('/chats/generate-session');
  return res.data;
};

export const getHistory = async (): Promise<TGetHistoryRequest> => {
  const res = await api.get<TGetHistoryRequest>('/chats/history');
  return res.data;
};

export const getDetailHistory = async (
  req: TClearChatRequest
): Promise<TGetDetailHistoryData> => {
  const res = await api.get<TGetDetailHistoryData>(`/chats/${req.session_id}`);
  return res.data;
};

export const bulkDeleteChat = async (
  req: TDeleteBulkChatRequest
): Promise<TDefaultResponse> => {
  const res = await api.post<TDefaultResponse>('/chats/bulk-delete', req);
  return res.data;
};

export const renameChat = async (
  req: TRenameChatRequest
): Promise<TDefaultResponse> => {
  const res = await api.patch<TDefaultResponse>(
    `/chats/rename/${req.chat_id}`,
    {
      title: req.title
    }
  );
  return res.data;
};

export const pinChat = async (
  req: TPinChatRequest
): Promise<TDefaultResponse> => {
  const res = await api.patch<TDefaultResponse>(`/chats/pin/${req.chat_id}`, {
    pinned: req.pinned
  });
  return res.data;
};
