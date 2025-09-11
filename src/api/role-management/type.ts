export type TRoleSettingItem = {
  role_id: number;
  setting_id: string;
  value: string;
};

export type TRequestSaveRoleSettings = TRoleSettingItem[];
