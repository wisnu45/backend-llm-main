export type EnhanceTypes = 'prefix' | 'postfix';

export type CreateEnhanceInput = {
  type: EnhanceTypes;
  value: string;
};

export type UpdateEnhanceInput = {
  id: string;
  type: EnhanceTypes;
  value: string;
};

export type DeleteEnhanceInput = {
  id: string;
};

export type ListEnhanceResponse = {
  data: string[];
};

export type EnhanceMutationResponse = {
  message: string;
};

export type Enhance = {
  id: string;
  type: EnhanceTypes;
  value: string;
  timestamp: string;
};
