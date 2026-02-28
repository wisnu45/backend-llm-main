import { useMutation } from '@tanstack/react-query';
import { postDocsFromPortal } from '@/api/document/api';

const useGetDocumentFromPortal = () => {
  return useMutation({
    mutationFn: postDocsFromPortal,
    onSuccess: (data) => {
      console.log('Data berhasil dikirim', data);
    },
    onError: (error) => {
      console.error('Terjadi error saat mengirim data', error);
    }
  });
};

export default useGetDocumentFromPortal;
