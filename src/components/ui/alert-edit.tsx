import { zodResolver } from '@hookform/resolvers/zod';
import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import * as z from 'zod';
import { Button } from './button';
import { Form, FormControl, FormField, FormItem, FormMessage } from './form';
import { Input } from './input';

const renameSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .max(100, 'Name must be less than 100 characters')
});

type RenameFormData = z.infer<typeof renameSchema>;

interface RenameModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (newName: string) => void;
  loading?: boolean;
  title?: string;
  description?: string;
  initialValue?: string;
}

const RenameModal: React.FC<RenameModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  loading = false,
  title = 'Rename Chat',
  description = 'Enter a new name for this chat.',
  initialValue = ''
}) => {
  const form = useForm<RenameFormData>({
    resolver: zodResolver(renameSchema),
    defaultValues: {
      name: initialValue
    }
  });

  useEffect(() => {
    form.reset({ name: initialValue });
  }, [initialValue, form]);

  const onSubmit = (data: RenameFormData) => {
    onConfirm(data.name);
  };

  const handleClose = () => {
    form.reset({ name: initialValue });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg">
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="mb-4 text-sm text-gray-500">{description}</p>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <Input
                      placeholder="Enter new name"
                      {...field}
                      disabled={loading}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={handleClose}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? 'Saving...' : 'Save'}
              </Button>
            </div>
          </form>
        </Form>
      </div>
    </div>
  );
};

export default RenameModal;
