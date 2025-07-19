import { getDocs } from '@/api/document/api';
import { TDocParams } from '@/api/document/type';
import { useQuery } from '@tanstack/react-query';

export const documentListQueryKey = 'get-document-list';

const useGetListDocument = (params?: TDocParams) => {
  return useQuery({
    queryKey: [documentListQueryKey, params],
    queryFn: () => getDocs(params)
  });
};
export default useGetListDocument;
