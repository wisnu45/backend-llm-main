import { createDoc } from '@/api/document/api';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from '@/components/ui/use-toast';
import { documentListQueryKey } from './get-list-document';

const useCreateDocument = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationKey: ['create-doc'],
    mutationFn: createDoc,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [documentListQueryKey],
        type: 'all'
      });
      toast({
        title: 'Document created successfully!',
        variant: 'default'
      });
    },
    onError: (error) => {
      toast({
        title: 'Failed to create document',
        description: error?.message || 'An unexpected error occurred',
        variant: 'destructive'
      });
    }
  });
};

export default useCreateDocument;
