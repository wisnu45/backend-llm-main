export interface TCreateRequest {
  type: string;
  value: string;
}

export interface TDeleteRequest {
  id: string;
}

export interface TUpdateRequest {
  id: string;
  type: string;
  value: string;
}
