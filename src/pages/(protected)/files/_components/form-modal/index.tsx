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
import { useEffect, useState } from 'react';
import { TRequestCreateDocument } from '@/api/document/type';
import { Loader2 } from 'lucide-react';
import { truncateFileName } from '@/lib/utils';
import { useFiles } from '@/hooks/use-files';
import { useFetchSetting } from '@/pages/(protected)/setting/_hook/use-fetch-setting';

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
  const [editDoc, setEditDoc] = useState(true);

  const form = useForm<TDocumentFormData>({
    mode: 'onChange',
    resolver: zodResolver(DocumentSchema)
  });

  const { files } = useFiles();

  const handleSubmit = (data: TDocumentFormData) => {
    const file = files[0]?.file;

    const formData = new FormData();

    if (file) {
      formData.append('file', file);
      formData.append('metadata', 'UPLOAD');
    }

    if (data.portal_id) {
      formData.append('portal_id', data.portal_id);
    }

    if (data.document_name) {
      formData.append('document_name', data.document_name);
    }

    onSubmit(formData);
  };

  useEffect(() => {
    form.reset(defaultValues);
  }, []);

  useEffect(() => {
    const file = files?.[0] || [];
    if (!file.file) return;

    form.setValue('document_path', file?.file?.name);
    form.setValue('document_name', file?.file?.name?.split('.')[0]);
  }, [files, form]);

  const mimeMap: Record<string, string> = {
    pdf: 'application/pdf',
    docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    png: 'image/png',
    txt: 'text/plain'
  };

  function parseAcceptedExtensions(extensions: string[]) {
    const result: Record<string, string[]> = {};

    extensions.forEach((ext) => {
      const mime = mimeMap[ext.toLowerCase()];
      if (mime) {
        if (!result[mime]) result[mime] = [];
        result[mime].push(`.${ext}`);
      }
    });

    return result;
  }

  const query = useFetchSetting();
  const dataSetting = query?.data?.data || [];
  const accepted = dataSetting?.find(
    (menu) => menu.name === 'Attachment file types'
  )?.value;
  const maxFile = dataSetting?.find(
    (menu) => menu.name === 'Attachment file size'
  )?.value;
  const accpetedFile = accepted ? JSON.parse(String(accepted)) : ['pdf'];
  const acceptedTypes = parseAcceptedExtensions(accpetedFile);

  return (
    <Dialog
      open={open}
      onOpenChange={() => {
        if (!open) {
          setEditDoc(true);
        }
        onOpenChange();
      }}
    >
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
              {mode === 'edit' && editDoc ? (
                <div>
                  <div className="flex items-end justify-between pb-1 pt-3">
                    <div className="text-sm font-semibold">File accepted</div>
                    <div
                      className="text-sm hover:cursor-pointer hover:text-destructive"
                      onClick={() => setEditDoc(false)}
                    >
                      Clear
                    </div>
                  </div>
                  <div className="flex flex-col justify-center gap-2">
                    <div className="flex justify-between rounded-md border px-4 py-3">
                      <div className="flex items-center gap-4 text-sm">
                        <div className="flex flex-col">
                          <span className="inline-block max-w-[300px] text-sm font-semibold">
                            {truncateFileName(
                              defaultValues?.document_name ?? '-',
                              30
                            )}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <FormField
                  control={form.control}
                  name="document_path"
                  render={() => {
                    return (
                      <FormItem>
                        <FormLabel>Document *</FormLabel>
                        <FormControl>
                          <FileUpload
                            accept={acceptedTypes}
                            maxFiles={1}
                            maxSize={maxFile ? Number(maxFile) : 10}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    );
                  }}
                />
              )}
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
                          disabled={mode === 'create'}
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  );
                }}
              />
            </div>
            {mode === 'edit' ? (
              <div>
                <FormField
                  control={form.control}
                  name="portal_id"
                  render={({ field }) => {
                    return (
                      <FormItem>
                        <FormLabel>Portal ID</FormLabel>
                        <FormControl>
                          <Input placeholder="Portal ID" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    );
                  }}
                />
              </div>
            ) : null}

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
