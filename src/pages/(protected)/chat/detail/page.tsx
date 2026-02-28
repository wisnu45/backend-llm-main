import { useEffect, useRef, useState } from 'react';
import { useGetDetailHistory } from '../_hook/use-get-history-chat';
import { useNavigate, useParams } from 'react-router-dom';
import { ChatItem } from '../component/ChatItem';
import useCreateChat, {
  type NetworkAwareError
} from '../_hook/use-create-chat';
import { Loader } from '../component/Loader';
import InputDataWithForm from '../component/InputDataWithForm';
import NetworkErrorCard from '../component/NetworkErrorCard';
import { PromptPreview } from '../component/prompt-preview';
import { ModernLoadingIndicator } from '../component/loading-indicator';
import { TChatFormData } from '../schema';
import { useChatForm } from '../_hook/use-chat-form';
import { useFetchSettingFeature } from '../../setting/_hook/use-fetch-setting-feature';
import { Cross2Icon } from '@radix-ui/react-icons';
import { toast } from '@/components/ui/use-toast';

const DetailPage = () => {
  const { chatId } = useParams();
  const query = useGetDetailHistory({ chat_id: chatId || '' });
  const mutation = useCreateChat();
  const navigate = useNavigate();
  const queryFeature = useFetchSettingFeature();
  const [isPopupOpen, setIsPopupOpen] = useState(false);
  const [popupFile, setPopupFile] = useState<File | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const settingFeature = queryFeature?.data?.data;
  const getMenuValue = (name: string) =>
    settingFeature?.find((menu) => menu.name.toLocaleLowerCase() === name)
      ?.value;
  const errorConnectionMessage = String(
    getMenuValue('error connection') ||
      'Koneksi internet terputus. Coba lagi nanti'
  );
  const serverErrorMessage = String(
    getMenuValue('message error') ||
      'Terjadi kesalahan pada server. Silakan coba lagi nanti'
  );

  const {
    loading,
    previewPrompt,
    previewFiles,
    showPreview,
    error,
    handleSubmit,
    handleError,
    handleRetry,
    handleSuccess
  } = useChatForm({
    chatId: chatId || '',
    onSuccess: () => {
      query.refetch();
    },
    onError: (isNetworkError) => {
      // Additional error handling if needed
      console.log(
        'Chat error occurred:',
        isNetworkError ? 'Network error' : 'Server error'
      );
    }
  });

  // For main layout scrolling, we'll let the hook use window scroll by not passing containerRef
  // The floating input will respond to the main document scroll

  useEffect(() => {
    if (!query.data?.data.length && !query.isLoading) {
      navigate('/chat');
      return;
    }
    query.refetch();
  }, [chatId, query.data, query.isLoading]);

  useEffect(() => {
    const container = chatContainerRef.current;
    if (!container) return;

    const scrollToBottom = () => {
      window.scrollTo({
        top: document.body.scrollHeight,
        behavior: 'smooth'
      });
    };

    const observer = new ResizeObserver(scrollToBottom);
    observer.observe(container);

    // Initial scroll
    scrollToBottom();

    return () => {
      observer.disconnect();
    };
  }, []);

  const handleFormSubmit = (formData: TChatFormData) => {
    const payload = handleSubmit(formData);

    if (payload) {
      mutation.mutate(
        {
          ...payload,
          with_document: payload.with_document,
          chat_id: chatId || ''
        },
        {
          onSuccess: () => {
            handleSuccess();
            query.refetch();
          },
          onError: (err: any) => {
            const networkError = err as NetworkAwareError;
            if (networkError.isNetworkError) {
              handleError(true, formData);
            } else {
              handleError(false);
            }
            if (err?.response?.status === 429) {
              toast({
                title: 'Sudah mencapai batas penggunaan',
                description: `${err?.response.data.message || 'Please try again later.'}`,
                variant: 'destructive'
              });
            }
          }
        }
      );
    }
  };

  const closePopup = () => {
    setIsPopupOpen(false);
    setPopupFile(null);
  };

  const handleNetworkRetry = () => {
    const payload = handleRetry();
    if (payload) {
      mutation.mutate(
        {
          ...payload,
          with_document: payload?.with_document || [],
          chat_id: chatId || ''
        },
        {
          onSuccess: () => {
            handleSuccess();
            query.refetch();
          },
          onError: (err: Error) => {
            const networkError = err as NetworkAwareError;
            if (networkError.isNetworkError) {
              // Convert payload back to TChatFormData format for handleError
              const formData: TChatFormData = {
                prompt: payload?.question || '',
                // attachments: payload?.attachments || [],
                with_document: payload?.with_document || [], // We don't have this in payload, but handleError doesn't actually use it
                is_browse: payload?.is_browse || false,
                is_company: payload?.is_company || false,
                is_general: payload?.is_general || false
              };
              handleError(true, formData);
            } else {
              handleError(false);
            }
          }
        }
      );
    }
  };
  const lastData = query?.data?.data.at(-1) || null;

  return (
    <div>
      <div
        className="flex-1"
        style={{ paddingBottom: 'calc(var(--chatbox-height, 128px) + 16px)' }}
      >
        <div ref={chatContainerRef} className={`mx-auto min-h-full w-[95%]`}>
          {query.isLoading ? (
            <Loader />
          ) : (
            query?.data?.data?.map((message, index) => {
              return (
                <div key={index}>
                  <ChatItem key={index} data={message} />
                </div>
              );
            })
          )}

          {showPreview && (
            <div>
              <PromptPreview text={previewPrompt} files={previewFiles} />
            </div>
          )}

          {loading && (
            <div>
              <ModernLoadingIndicator />
            </div>
          )}

          {error.show && (
            <div>
              <NetworkErrorCard
                onRetry={handleNetworkRetry}
                message={
                  error.isNetwork ? errorConnectionMessage : serverErrorMessage
                }
                isNetworkError={error.isNetwork}
              />
            </div>
          )}
        </div>
      </div>

      <InputDataWithForm
        onSubmit={handleFormSubmit}
        isLoading={loading}
        isFloating={true}
        lastData={lastData || undefined}
        setPopupFile={setPopupFile}
        setIsPopupOpen={setIsPopupOpen}
      />

      {isPopupOpen && popupFile && (
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={closePopup}
        >
          <div
            className="max-w-screen relative h-full max-h-screen w-full p-2 md:p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="relative h-full w-full overflow-hidden rounded-lg bg-white shadow-xl">
              {popupFile?.type?.startsWith('image') ? (
                <div className="flex h-full w-full flex-col items-center justify-center gap-3 p-4">
                  <img
                    src={URL.createObjectURL(popupFile)}
                    alt={popupFile?.name}
                    className="h-full w-full object-contain"
                  />
                </div>
              ) : popupFile?.type === 'application/pdf' ? (
                <div className="flex h-full w-full flex-col items-center justify-center gap-3 p-4">
                  <iframe
                    src={URL.createObjectURL(popupFile) || ''}
                    title={popupFile?.name}
                    className="h-full w-full"
                  />
                </div>
              ) : (
                <div className="flex h-full w-full flex-col items-center justify-center gap-3 p-4">
                  <span className="text-6xl">📄</span>
                  <p className="text-lg font-semibold">{popupFile?.name}</p>
                  <p className="text-sm text-gray-500">
                    Preview tidak tersedia untuk file ini
                  </p>
                  <a
                    href={URL.createObjectURL(popupFile)}
                    download={popupFile?.name}
                    className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
                  >
                    Download file
                  </a>
                </div>
              )}

              <button
                type="button"
                onClick={closePopup}
                className="absolute right-3 top-3 z-50 rounded-full bg-red-600 p-2 text-white shadow-lg hover:bg-red-700"
              >
                <Cross2Icon className="h-6 w-6" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DetailPage;

