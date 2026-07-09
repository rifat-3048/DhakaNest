"use client";

import { apiRequest } from "@/lib/api";
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  User,
  UserRole,
} from "@/types/auth";

const TOKEN_KEY = "dhakanest_access_token";
const USER_KEY = "dhakanest_user";

export function registerUser(payload: RegisterRequest) {
  return apiRequest<RegisterResponse>("/auth/register", {
    method: "POST",
    body: payload,
  });
}

export async function loginUser(payload: LoginRequest) {
  const result = await apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: payload,
  });

  saveAuth(result.access_token, result.user);
  return result;
}

export function getCurrentUser(token: string) {
  return apiRequest<User>("/auth/me", {
    token,
  });
}

export function saveAuth(token: string, user: LoginResponse["user"]) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function logoutUser() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getDashboardPath(role: UserRole) {
  return `/${role}/dashboard`;
}
