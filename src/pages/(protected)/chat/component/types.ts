export interface FileLink {
  title: string;
  url: string;
}

export interface ChatItemData {
  id: string;
  question: string;
  answer: string;
  created_at: string | Date;
  file_links?: FileLink[];
  // metadata?: FileLink[];
  source_documents?: FileLink[];
  chat_id: string;
  feedback: '1' | '-1' | null;
  is_browse?: boolean;
  is_company?: boolean;
  is_general?: boolean;
}
