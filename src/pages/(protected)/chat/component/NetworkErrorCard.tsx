import { AlertTriangleIcon, RotateCcwIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface NetworkErrorCardProps {
  onRetry?: () => void;
  message?: string;
}

const NetworkErrorCard = ({
  onRetry,
  message = 'Koneksi internet terputus. Coba lagi nanti'
}: NetworkErrorCardProps) => {
  return (
    <div className="mx-auto mb-4 w-full max-w-2xl">
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <div className="flex items-start gap-3">
          <AlertTriangleIcon className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
          <div className="flex-1">
            <div className="text-sm font-medium text-red-800">
              Koneksi Bermasalah
            </div>
            <div className="mt-1 text-sm text-red-700">{message}</div>
            {onRetry && (
              <div className="mt-3">
                <Button
                  onClick={onRetry}
                  variant="outline"
                  size="sm"
                  className="border-red-300 bg-transparent text-red-700 hover:bg-red-100"
                >
                  <RotateCcwIcon className="mr-2 h-4 w-4" />
                  Coba Lagi
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default NetworkErrorCard;
