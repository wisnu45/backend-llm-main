import { ScrollArea } from '@/components/ui/scroll-area';
import { useEffect, useRef } from 'react';
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

const DetailPage = () => {
  const { chatId } = useParams();
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLElement | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const query = useGetDetailHistory({ chat_id: chatId || '' });
  const mutation = useCreateChat();
  const navigate = useNavigate();
  const queryFeature = useFetchSettingFeature();

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

  // Simplified scroll container setup - use ScrollArea ref directly
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollContainerRef.current = scrollAreaRef.current;
    }
  }, []);

  useEffect(() => {
    if (!query.data?.data.length && !query.isLoading) {
      navigate('/chat');
      return;
    }
    query.refetch();
  }, [chatId, query.data, query.isLoading]);

  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'end'
      });
    }
  }, [query.data?.data.length, loading, showPreview, query.isLoading]);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [query?.data?.data, loading, showPreview]);

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
          onError: (err: Error) => {
            // Check if this is a network error
            const networkError = err as NetworkAwareError;
            if (networkError.isNetworkError) {
              handleError(true, formData);
            } else {
              handleError(false);
            }
          }
        }
      );
    }
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
    <>
      <ScrollArea ref={scrollAreaRef} className="scrollbar-hide flex-1">
        <div className={`mx-auto min-h-full w-[95%] pb-44`}>
          {query.isLoading ? (
            <Loader />
          ) : (
            query?.data?.data?.map((message, index) => {
              const isLast = index === (query?.data?.data?.length ?? 0) - 1;
              return (
                <div
                  ref={isLast && !loading && !showPreview ? chatEndRef : null}
                  key={index}
                >
                  <ChatItem key={index} data={message} />
                </div>
              );
            })
          )}

          {showPreview && (
            <div ref={scrollAreaRef}>
              <PromptPreview text={previewPrompt} files={previewFiles} />
            </div>
          )}

          {loading && (
            <div ref={scrollAreaRef}>
              <ModernLoadingIndicator />
            </div>
          )}

          {error.show && (
            <div ref={scrollAreaRef}>
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
        <div ref={chatEndRef} />

        <InputDataWithForm
          onSubmit={handleFormSubmit}
          isLoading={loading}
          scrollContainerRef={scrollContainerRef}
          isFloating={true}
          lastData={lastData || undefined}
        />
      </ScrollArea>
    </>
  );
};

export default DetailPage;
