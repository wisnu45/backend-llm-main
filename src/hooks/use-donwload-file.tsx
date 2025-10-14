import { SessionToken } from '@/lib/cookies';
import { useMutation } from '@tanstack/react-query';

export const useOpenPdf = () => {
  return useMutation({
    mutationKey: ['download-file'],
    mutationFn: async (url: string) => {
      const secureUrl = url;
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
    onSuccess: (blob, url) => {
      const fileExtension = url.split('.').pop()?.toLowerCase();
      const isPdf = blob?.type?.includes('pdf');
      const isImage = ['jpg', 'jpeg', 'png', 'gif'].includes(
        fileExtension || ''
      );

      if (isPdf || isImage) {
        const objectUrl = URL.createObjectURL(blob);
        window.open(objectUrl, '_blank');
      } else {
        const downloadLink = document.createElement('a');
        downloadLink.href = URL.createObjectURL(blob);
        downloadLink.download = url.split('/').pop() || 'file';
        downloadLink.click();
      }
    },
    onError: (error, variables) => {
      console.error('Error fetching the PDF to open in a new tab:', error);
      window.open(variables, '_blank');
    }
  });
};
