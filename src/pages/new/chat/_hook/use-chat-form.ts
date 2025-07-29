import { useState } from 'react';
import { TChatFormData } from '../schema';
import { FileType } from '../component/prompt-preview';

interface UseChatFormProps {
  chatId: string;
  onSuccess?: () => void;
  onError?: () => void;
}

export const useChatForm = ({ chatId }: UseChatFormProps) => {
  const [loading, setLoading] = useState<boolean>(false);
  const [previewPrompt, setPreviewPrompt] = useState<string>('');
  const [previewFiles, setPreviewFiles] = useState<FileType[]>([]);
  const [showPreview, setShowPreview] = useState<boolean>(false);

  const handleSubmit = (formData: TChatFormData) => {
    if (!formData.prompt.trim()) return;

    setPreviewPrompt(formData.prompt);
    setPreviewFiles(formData.attachments || []);
    setShowPreview(true);
    setLoading(true);

    return {
      question: formData.prompt,
      session_id: chatId,
      is_browse: formData.is_browse
    };
  };

  const resetForm = () => {
    setPreviewPrompt('');
    setPreviewFiles([]);
    setShowPreview(false);
    setLoading(false);
  };

  return {
    loading,
    previewPrompt,
    previewFiles,
    showPreview,
    handleSubmit,
    resetForm
  };
};
