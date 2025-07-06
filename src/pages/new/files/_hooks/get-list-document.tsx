import { getDocs } from '@/api/document/api';
import { useQuery } from '@tanstack/react-query';

export const documentListQueryKey = 'get-document-list';

const useGetListDocument = () => {
  return useQuery({
    queryKey: [documentListQueryKey],
    queryFn: getDocs
  });
};

export default useGetListDocument;
