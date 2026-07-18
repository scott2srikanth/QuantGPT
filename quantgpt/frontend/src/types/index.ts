export type HealthResponse = {
  status: string;
  version: string;
  environment: string;
  timestamp: string;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type RoleOut = {
  id: string;
  name: string;
  description: string | null;
};

export type UserOut = {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  roles: RoleOut[];
};
