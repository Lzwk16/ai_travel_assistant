import { useQuery } from "@tanstack/react-query";
import { getMe } from "../../lib/api";
import type { UserRead } from "../../lib/types";

// The signed-in user (GET /auth/me). Cached for the session; a 401 from the
// shared request() helper clears the token, so this naturally invalidates.
export function useMe() {
  return useQuery<UserRead>({
    queryKey: ["me"],
    queryFn: getMe,
    staleTime: Infinity,
  });
}
