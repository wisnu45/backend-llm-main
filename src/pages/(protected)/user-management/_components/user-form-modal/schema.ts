import * as z from 'zod';

const BaseUserSchema = z.object({
  name: z
    .string({ message: 'Name is required' })
    .min(1, { message: 'Name is required' })
    .min(2, { message: 'Name must be at least 2 characters' }),
  username: z
    .string({ message: 'Username is required' })
    .min(1, { message: 'Username is required' })
    .min(3, { message: 'Username must be at least 3 characters' })
    .regex(/^[a-zA-Z0-9_-]+$/, {
      message:
        'Username can only contain letters, numbers, hyphens and underscores'
    }),
  isPortalUser: z.boolean().default(false),
  role_id: z
    .string({ message: 'Role is required' })
    .min(1, { message: 'Please select a role' })
});

export const CreateUserSchema = BaseUserSchema.extend({
  password: z
    .string({ message: 'Password is required' })
    .min(6, { message: 'Password must be at least 6 characters' })
});

export const EditUserSchema = BaseUserSchema;

export const UserFormSchema = BaseUserSchema.extend({
  password: z.string().optional()
});
export type TUserFormData = z.infer<typeof UserFormSchema>;
