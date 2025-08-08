import { SessionToken } from '@/lib/cookies';
import { useMutation } from '@tanstack/react-query';

export const useOpenPdf = () => {
  return useMutation({
    mutationKey: ['download-file'],
    mutationFn: async (url: string) => {
      const secureUrl = url.startsWith('http://')
        ? url.replace('http://', 'https://')
        : url;
      const response = await fetch(secureUrl, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${SessionToken.get()}`
        }
      });
      if (!response.ok) {
        throw new Error('Network response was not ok.');
      }
      const blob = await response.blob();
      return blob;
    },
    onSuccess: (res) => {
      const objectUrl = URL.createObjectURL(res);
      console.log({ objectUrl });
      window.open(objectUrl, '_blank');
    },
    onError: (error, variables) => {
      console.error('Error fetching the PDF to open in a new tab:', error);
      window.open(variables, '_blank');
    }
  });
};
