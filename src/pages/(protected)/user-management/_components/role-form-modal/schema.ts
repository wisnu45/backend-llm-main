import * as z from 'zod';

const RoleSchema = z.object({
  name: z
    .string({ message: 'Role name is required' })
    .min(1, { message: 'Role name is required' })
    .min(2, { message: 'Role name must be at least 2 characters' }),
  chat: z.boolean().default(false),
  file_management: z.boolean().default(false),
  history: z.boolean().default(false),
  chat_attachment: z.boolean().default(false),
  user_management: z.boolean().default(false),
  max_chat_topic: z.number().min(1).max(100).default(10),
  chat_topic_expired_days: z.number().min(1).max(365).default(30),
  max_chat: z.number().min(1).max(1000).default(100)
});

export const RoleFormSchema = RoleSchema;
export type TRoleFormData = z.infer<typeof RoleFormSchema>;
