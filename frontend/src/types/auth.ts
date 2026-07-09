export type UserRole = "tenant" | "landlord" | "admin";
export type PublicRegisterRole = "tenant" | "landlord";

export type User = {
  id: string;
  name: string;
  email: string;
  phone?: string | null;
  role: UserRole;
  is_active: boolean;
};

export type RegisterRequest = {
  name: string;
  email: string;
  phone: string;
  password: string;
  role: PublicRegisterRole;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type LoginUser = {
  id: string;
  name: string;
  email: string;
  role: UserRole;
};

export type RegisterResponse = {
  message: string;
  user: User;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  user: LoginUser;
};
