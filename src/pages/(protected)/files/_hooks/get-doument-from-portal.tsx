import { useMutation } from '@tanstack/react-query';
import { getDocsFromPortal } from '@/api/document/api';

const useGetDocumentFromPortal = () => {
  return useMutation({
    mutationFn: getDocsFromPortal
  });
};

export default useGetDocumentFromPortal;
