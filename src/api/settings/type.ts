import { TResponse } from '@/commons/types/response';

export type TSetting = {
  data_type: string;
  description: string;
  name: string;
  role_id: string;
  setting_id: string;
  type: string;
  unit: string;
  value: boolean | string | number;
};

export type TResponseListSettings = TResponse<TSetting[]>;

export type TSettingDocument = {
  data_type: string;
  description: string;
  id: string;
  name: string;
  type: string;
  unit: any | null;
  value: string | boolean;
};

export type TSettingInput = {
  id: string;
  name: string;
  description: string;
  type: string;
  unit: string | null;
  data_type: string;
  value: string;
};

export type TResponseSettingDocument = TResponse<TSettingDocument[]>;

export type TRequestEditSetting = TSettingInput;
