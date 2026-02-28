import { useState } from 'react';
import { TChatFormData } from '../schema';
import { FileType } from '../component/prompt-preview';

interface UseChatFormProps {
  chatId: string;
  onSuccess?: () => void;
  onError?: (isNetworkError?: boolean) => void;
}

export const useChatForm = ({
  chatId,
  onSuccess,
  onError
}: UseChatFormProps) => {
  const [loading, setLoading] = useState<boolean>(false);
  const [previewPrompt, setPreviewPrompt] = useState<string>('');
  const [previewFiles, setPreviewFiles] = useState<FileType[]>([]);
  const [showPreview, setShowPreview] = useState<boolean>(false);
  const [error, setError] = useState<{ isNetwork: boolean; show: boolean }>({
    isNetwork: false,
    show: false
  });
  const [lastFailedRequest, setLastFailedRequest] =
    useState<TChatFormData | null>(null);

  const handleSubmit = (formData: TChatFormData, isRetry: boolean = false) => {
    if (!formData.prompt.trim()) return;

    // Only clear error for new submissions, not retries
    if (!isRetry) {
      setError({ isNetwork: false, show: false });
      setLastFailedRequest(null);
    }

    setPreviewPrompt(formData.prompt);
    setPreviewFiles(formData.with_document || []);
    setShowPreview(true);
    setLoading(true);

    return {
      question: formData.prompt,
      chat_id: chatId,
      is_browse: formData.is_browse,
      is_company: formData.is_company,
      is_general: formData.is_general,
      with_document: formData.with_document
    };
  };

  const resetForm = () => {
    setPreviewPrompt('');
    setPreviewFiles([]);
    setShowPreview(false);
    setLoading(false);
  };

  const handleError = (
    isNetworkError: boolean = false,
    failedFormData?: TChatFormData
  ) => {
    setLoading(false);
    setShowPreview(false);
    setPreviewPrompt('');
    setPreviewFiles([]);

    if (failedFormData) {
      setError({ isNetwork: isNetworkError, show: true });
      setLastFailedRequest(failedFormData);
    } else {
      // Clear error if no failed form data
      setError({ isNetwork: false, show: false });
      setLastFailedRequest(null);
    }

    onError?.(isNetworkError);
  };

  const handleRetry = () => {
    if (lastFailedRequest) {
      // Pass isRetry=true to preserve network error state during retry
      return handleSubmit(lastFailedRequest, true);
    }
    return null;
  };

  const handleSuccess = () => {
    // Clear all error states on successful submission
    setError({ isNetwork: false, show: false });
    setLastFailedRequest(null);
    resetForm();
    onSuccess?.();
  };

  return {
    loading,
    previewPrompt,
    previewFiles,
    showPreview,
    error,
    handleSubmit,
    handleError,
    handleRetry,
    handleSuccess,
    resetForm
  };
};
