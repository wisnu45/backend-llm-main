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
  TPinChatRequest,
  TChatResponse
} from './type';
import { TDefaultResponse } from '@/commons/types/response';

// export const chat = async (req: TChatRequest): Promise<TDefaultResponse<TChatResponse>> => {
//   const res = await api.post<TDefaultResponse>('/chats/ask', req);
//   return res.data;
// };

// export const chat = async (
//   req: TChatRequest
// ): Promise<TDefaultResponse<TChatResponse>> => {

//   console.log('CEK REQ DI API CHAT', req)
//   const res = await api.post<TDefaultResponse<TChatResponse>>(
//     '/chats/ask',
//     req
//   );
//   return res.data;
// };

export const chat = async (
  req: TChatRequest
): Promise<TDefaultResponse<TChatResponse>> => {
  const formData = new FormData();
  formData.append('question', req.question || '');
  formData.append('is_browse', String(req.is_browse || false));
  formData.append('is_general', String(req.is_general || false));
  formData.append('is_company', String(req.is_company || false));
  if (req.chat_id) {
    formData.append('chat_id', String(req.chat_id || null));
  }

  if (Array.isArray(req.with_document)) {
    req.with_document.forEach((file) => {
      if (file) {
        formData.append('with_document', file);
      }
    });
  } else if (req.with_document) {
    formData.append('with_document', req.with_document);
  }

  const res = await api.post<TDefaultResponse<TChatResponse>>(
    '/chats/ask',
    formData
  );

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
  const res = await api.delete<TDefaultResponse>(`/chats/${req.chat_id}`);
  return res.data;
};

export const newChat = async (): Promise<TNewSesionResponse> => {
  const res = await api.get<TNewSesionResponse>('/chats/generate-session');
  return res.data;
};

export const getHistory = async (): Promise<TGetHistoryRequest> => {
  const res = await api.get<TGetHistoryRequest>('/chats');
  return res.data;
};

export const getDetailHistory = async (
  req: TClearChatRequest
): Promise<TGetDetailHistoryData> => {
  const res = await api.get<TGetDetailHistoryData>(`/chats/${req.chat_id}`);
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
