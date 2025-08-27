import { getDetailDoc } from '@/api/document/api';
import { useQuery } from '@tanstack/react-query';

export const documentDetailQueryKey = 'get-detail-doc';

const useGetDetailDocument = (id?: string) => {
  return useQuery({
    queryKey: [documentDetailQueryKey, { id }],
    queryFn: () => getDetailDoc({ id }),
    enabled: Boolean(id)
  });
};

export default useGetDetailDocument;
