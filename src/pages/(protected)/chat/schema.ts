import * as z from 'zod';

export const ChatFormSchema = z.object({
  prompt: z
    .string({ message: 'Prompt is required' })
    .min(1, { message: 'Prompt is required' })
    .max(1000, { message: 'Prompt must be less than 1000 characters' }),
  // attachments: z.array(z.instanceof(File)).optional().default([]),
  with_document: z.array(z.instanceof(File)).optional().default([]),
  is_browse: z.boolean().default(false),
  is_company: z.boolean().default(false),
  is_general: z.boolean().default(false)
});

export type TChatFormData = z.infer<typeof ChatFormSchema>;
