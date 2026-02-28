export type TRoleSettingItem = {
  role_id: string;
  setting_id: string;
  value: unknown;
};

export type TRequestSaveRoleSettings = TRoleSettingItem[];
