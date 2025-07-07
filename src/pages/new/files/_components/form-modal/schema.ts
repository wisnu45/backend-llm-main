import * as z from 'zod';

const BaseSchema = z.object({
  document_name: z
    .string({ message: 'Document Name is Required' })
    .min(1, { message: 'Document Name is Required' }),
  document_path: z.string({ message: 'Document is Required' }),
  portal_id: z.string().optional()
});

export const DocumentSchema = BaseSchema;
export type TDocumentFormData = z.infer<typeof DocumentSchema>;
