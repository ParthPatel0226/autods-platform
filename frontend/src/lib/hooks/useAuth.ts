"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api/endpoints";
import type { User } from "@/lib/api/types";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("autods_token");
}

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: user, isLoading } = useQuery<User | null>({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const token = getToken();
      if (!token) return null;
      try {
        return await authApi.me();
      } catch {
        // Token invalid — clear it
        localStorage.removeItem("autods_token");
        document.cookie =
          "autods_session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        return null;
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
  });

  const logout = () => {
    localStorage.removeItem("autods_token");
    document.cookie =
      "autods_session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    queryClient.clear();
    router.push("/login");
  };

  return {
    user: user ?? null,
    isLoading,
    isAuthenticated: !!user,
    logout,
  };
}
