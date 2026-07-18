/**
 * Shared types between QuantGPT frontend, future SDKs, and (eventually) workers.
 * These mirror the backend Pydantic schemas in backend/app/schemas/schemas.py.
 */

export type HealthResponse = {
  status: "ok" | "degraded" | "fail";
  version: string;
  environment: string;
  timestamp: string;
};

export type HealthComponent = {
  name: string;
  status: "ok" | "fail";
  detail?: string | null;
};

export type HealthDetailResponse = HealthResponse & {
  components: HealthComponent[];
};

export type RoleName = "admin" | "trader" | "viewer";

export type RoleOut = {
  id: string;
  name: RoleName;
  description: string | null;
};

export type UserOut = {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  roles: RoleOut[];
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type OpenAlgoStatus = {
  base_url: string;
  reachable: boolean;
  api_key_configured: boolean;
  websocket_url: string;
  detail?: string | null;
};
