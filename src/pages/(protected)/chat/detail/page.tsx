import { ScrollArea } from '@/components/ui/scroll-area';
import { useEffect, useRef } from 'react';
import { useGetDetailHistory } from '../_hook/use-get-history-chat';
import { useNavigate, useParams } from 'react-router-dom';
import { ChatItem } from '../component/ChatItem';
import useCreateChat from '../_hook/use-create-chat';
import { Loader } from '../component/Loader';
import InputDataWithForm from '../component/InputDataWithForm';
import { PromptPreview } from '../component/prompt-preview';
import { ModernLoadingIndicator } from '../component/loading-indicator';
import { TChatFormData } from '../schema';
import { useChatForm } from '../_hook/use-chat-form';

const DetailPage = () => {
  const { chatId } = useParams();
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLElement | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const query = useGetDetailHistory({ session_id: chatId || '' });
  const mutation = useCreateChat();
  const navigate = useNavigate();

  const {
    loading,
    previewPrompt,
    previewFiles,
    showPreview,
    handleSubmit,
    resetForm
  } = useChatForm({
    chatId: chatId || '',
    onSuccess: () => {
      query.refetch();
    },
    onError: () => {
      // Handle error if needed
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
      mutation.mutate(payload, {
        onSuccess: () => {
          resetForm();
          query.refetch();
        },
        onError: () => {
          resetForm();
        }
      });
    }
  };

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
        </div>
        <div ref={chatEndRef} />

        <InputDataWithForm
          onSubmit={handleFormSubmit}
          isLoading={loading}
          scrollContainerRef={scrollContainerRef}
          isFloating={true}
        />
      </ScrollArea>
    </>
  );
};

export default DetailPage;
