import { getDocs } from '@/api/document/api';
import { TDocParams, TResponseListDocument } from '@/api/document/type';
import { useQuery, UseQueryOptions } from '@tanstack/react-query';

export const documentListQueryKey = 'get-document-list';

const useGetListDocument = (
  params?: TDocParams,
  options?: Omit<UseQueryOptions<TResponseListDocument>, 'queryKey' | 'queryFn'>
) => {
  return useQuery<TResponseListDocument>({
    queryKey: [documentListQueryKey, params],
    queryFn: () => getDocs(params),
    ...options
  });
};
export default useGetListDocument;
