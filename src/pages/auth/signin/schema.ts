import * as z from 'zod';

const BaseSchema = z.object({
  username: z
    .string({ message: 'Username is required' })
    .min(1, { message: 'Username is required' }),
  password: z
    .string({ message: 'Password is required' })
    .min(1, { message: 'Password is required' })
});

export const LoginSchema = BaseSchema;
export type TLoginFormData = z.infer<typeof LoginSchema>;
