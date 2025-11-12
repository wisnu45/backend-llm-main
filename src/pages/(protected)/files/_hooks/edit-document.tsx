import { editDoc } from '@/api/document/api';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from '@/components/ui/use-toast';
import { documentListQueryKey } from './get-list-document';
import { TRequestCreateDocument } from '@/api/document/type';

const useEditDocument = (id: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationKey: ['edit-document'],
    mutationFn: (req: TRequestCreateDocument) => editDoc(req, { id }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [documentListQueryKey],
        type: 'all'
      });
      toast({
        title: 'Document edited successfully!',
        variant: 'default'
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to edit document',
        description:
          error?.response?.data?.error || 'An unexpected error occurred',
        variant: 'destructive'
      });
    }
  });
};

export default useEditDocument;
