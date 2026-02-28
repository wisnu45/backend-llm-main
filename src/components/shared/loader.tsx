import { LoaderCircle as Icon } from 'lucide-react';

export function LoaderCircle() {
  return (
    <div className="flex h-20 w-full items-center justify-center">
      <Icon className="size-10 animate-spin" />
    </div>
  );
}
