import * as z from 'zod';

const UserSchema = z.object({
  name: z
    .string({ message: 'Name is required' })
    .min(1, { message: 'Name is required' })
    .min(2, { message: 'Name must be at least 2 characters' }),
  email: z
    .string({ message: 'Email is required' })
    .min(1, { message: 'Email is required' })
    .email({ message: 'Please enter a valid email address' }),
  role_id: z
    .string({ message: 'Role is required' })
    .min(1, { message: 'Please select a role' })
});

export const UserFormSchema = UserSchema;
export type TUserFormData = z.infer<typeof UserFormSchema>;
