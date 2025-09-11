import * as z from 'zod';

const RoleSchema = z.object({
  name: z
    .string({ message: 'Role name is required' })
    .min(1, { message: 'Role name is required' })
    .min(2, { message: 'Role name must be at least 2 characters' }),
  description: z
    .string({ message: 'Description is required' })
    .min(1, { message: 'Description is required' }),
  is_local: z.boolean().default(true),
  is_portal: z.boolean().default(false)
});

export const RoleFormSchema = RoleSchema;
export type TRoleFormData = z.infer<typeof RoleFormSchema>;
