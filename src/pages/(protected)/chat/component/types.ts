export interface FileLink {
  filename: string;
  download_url: string;
}

export interface ChatItemData {
  id: string;
  question: string;
  answer: string;
  created_at: string | Date;
  file_links?: FileLink[];
  session_id: string;
  chat_id: string;
  feedback: '1' | '-1' | null;
}
