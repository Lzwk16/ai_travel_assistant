import { useQuery } from "@tanstack/react-query";
import { listTrips } from "../../lib/api";
import type { TripRead } from "../../lib/types";

const TERMINAL = new Set(["completed", "failed"]);

// Trips list with the async polling lifecycle: keep refetching every 3s while
// any trip is still pending/running, then stop once all are terminal (§5).
export function useTrips() {
  return useQuery<TripRead[]>({
    queryKey: ["trips"],
    queryFn: listTrips,
    refetchInterval: (query) => {
      const trips = query.state.data;
      if (!trips) return false;
      const anyActive = trips.some((t) => !TERMINAL.has(t.status));
      return anyActive ? 3000 : false;
    },
  });
}
