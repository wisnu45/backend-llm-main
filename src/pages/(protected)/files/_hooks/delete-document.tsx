import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from '@/components/ui/use-toast';
import { documentListQueryKey } from './get-list-document';
import { deleteDoc } from '@/api/document/api';

const useDeleteDocument = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationKey: ['delete-document'],
    mutationFn: deleteDoc,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [documentListQueryKey],
        type: 'all'
      });
      toast({
        title: 'Document deleted successfully!',
        variant: 'default'
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to delete document',
        description:
          error?.response?.data?.error || 'An unexpected error occurred',
        variant: 'destructive'
      });
    }
  });
};

export default useDeleteDocument;
