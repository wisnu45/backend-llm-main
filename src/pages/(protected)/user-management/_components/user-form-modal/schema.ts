import * as z from 'zod';

const BaseUserSchemaObject = z.object({
  originalName: z.string().optional(),
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

export const CreateUserSchema = BaseUserSchemaObject.extend({
  password: z.string().optional()
}).superRefine((data, ctx) => {
  // Check originalName requirement
  if (
    !data.isPortalUser &&
    (!data.originalName || data.originalName.trim() === '')
  ) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Original Name is required when Portal User is disabled',
      path: ['originalName']
    });
  }

  // Check password requirement
  if (!data.isPortalUser && (!data.password || data.password.trim() === '')) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Password is required when Portal User is disabled',
      path: ['password']
    });
  }

  if (data.password && data.password.length < 6) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Password must be at least 6 characters',
      path: ['password']
    });
  }
});

export const EditUserSchema = BaseUserSchemaObject.superRefine((data, ctx) => {
  if (
    !data.isPortalUser &&
    (!data.originalName || data.originalName.trim() === '')
  ) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Original Name is required when Portal User is disabled',
      path: ['originalName']
    });
  }
});

export const UserFormSchema = BaseUserSchemaObject.extend({
  password: z.string().optional()
});

export type TUserFormData = z.infer<typeof UserFormSchema>;
