import * as z from 'zod';

const RoleSchema = z.object({
  name: z
    .string({ message: 'Role name is required' })
    .min(1, { message: 'Role name is required' })
    .min(2, { message: 'Role name must be at least 2 characters' }),
  permission_ids: z
    .array(z.string())
    .min(1, { message: 'At least one permission must be selected' })
});

export const RoleFormSchema = RoleSchema;
export type TRoleFormData = z.infer<typeof RoleFormSchema>;
