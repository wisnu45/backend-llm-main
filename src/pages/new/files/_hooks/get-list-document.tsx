import { getDocs } from '@/api/document/api';
import { useQuery } from '@tanstack/react-query';

export const documentListQueryKey = 'get-document-list';

const useGetListDocument = (search: string, page: number, limit: number) => {
  return useQuery({
    queryKey: [documentListQueryKey, search, page, limit],
    queryFn: () => getDocs(search, page, limit)
  });
};
export default useGetListDocument;
