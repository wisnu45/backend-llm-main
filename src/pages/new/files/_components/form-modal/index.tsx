import { FileUpload } from '@/components/shared/file-upload';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import { useForm } from 'react-hook-form';
import { DocumentSchema, TDocumentFormData } from './schema';
import { zodResolver } from '@hookform/resolvers/zod';
import { Input } from '@/components/ui/input';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage
} from '@/components/ui/form';
import { Button } from '@/components/ui/button';
import { useEffect } from 'react';
import { useFiles } from '@/hooks/use-files';
import { TRequestCreateDocument } from '@/api/document/type';
import { Loader2 } from 'lucide-react';

interface Props {
  loading?: boolean;
  open?: boolean;
  onOpenChange: () => void;
  mode: 'create' | 'edit';
  defaultValues?: Partial<TDocumentFormData>;
  onSubmit: (data: TRequestCreateDocument) => void;
}

const FormModal = ({
  defaultValues,
  open,
  onOpenChange,
  onSubmit,
  mode,
  loading
}: Props) => {
  const metaMap: Record<Props['mode'], { title: string; desc: string }> = {
    create: {
      title: 'Add New File',
      desc: 'Add a new document to be used in AI training.'
    },
    edit: {
      title: 'Edit File',
      desc: 'Edit document used in AI model training.'
    }
  };

  const form = useForm<TDocumentFormData>({
    mode: 'onChange',
    resolver: zodResolver(DocumentSchema)
  });

  const { files } = useFiles();

  const handleSubmit = () => {
    const file = files[0].file;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('metadata', 'UPLOAD');

    onSubmit(formData);
  };

  useEffect(() => {
    form.reset(defaultValues);
  }, []);

  useEffect(() => {
    const file = files?.[0] || [];
    form.setValue('document_path', file?.file?.name);
    form.setValue('document_name', file?.file?.name?.split('.')[0]);
  }, [files, form]);

  return (
    <Dialog open={open} onOpenChange={loading ? undefined : onOpenChange}>
      <DialogContent
        className="no-scrollbar sm:max-w-md"
        onInteractOutside={(e) => e.preventDefault()}
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>{metaMap[mode].title}</DialogTitle>
          <DialogDescription>{metaMap[mode].desc}</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(handleSubmit)}
            className="flex flex-col gap-2"
          >
            <div>
              <FormField
                control={form.control}
                name="document_path"
                render={() => {
                  return (
                    <FormItem>
                      <FormLabel>Document *</FormLabel>
                      <FormControl>
                        <FileUpload
                          accept={{
                            'application/pdf': ['.pdf']
                          }}
                          maxFiles={1}
                          maxSize={10}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  );
                }}
              />
            </div>
            <div>
              <FormField
                control={form.control}
                name="document_name"
                render={({ field }) => {
                  return (
                    <FormItem>
                      <FormLabel>Document Name *</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Document Name"
                          disabled
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  );
                }}
              />
            </div>

            <DialogFooter className="mt-2 sm:justify-start">
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Save'
                )}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
};

export default FormModal;
