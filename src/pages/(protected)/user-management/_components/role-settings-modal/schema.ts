import { z } from 'zod';

export const RoleSettingsSchema = z.record(
  z.string(),
  z.union([z.string(), z.boolean(), z.number()]).optional()
);

export type TRoleSettingsFormData = z.infer<typeof RoleSettingsSchema>;

export type TRoleSettingField = {
  id: string;
  name: string;
  description: string;
  data_type: 'string' | 'boolean' | 'number';
  role_id: string;
  setting_id: string;
  value: string | boolean | number;
};
