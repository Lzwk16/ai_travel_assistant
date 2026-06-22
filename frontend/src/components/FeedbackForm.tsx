import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getFeedback, submitFeedback } from "../../lib/api";
import { formatError } from "../format";
import type { FeedbackRead } from "../../lib/types";

const STARS = [1, 2, 3, 4, 5];

// Rate a completed trip for feedback. The rating becomes part of the feedback
// corpus that later seeds agent memory (agent-state roadmap §9 / §6 seam).
export default function FeedbackForm({ tripId }: { tripId: number }) {
  const queryClient = useQueryClient();

  // A 404 here just means "not rated yet" — a normal state, so we don't retry
  // or surface it as an error. `existing` is simply undefined until rated.
  const { data: existing } = useQuery<FeedbackRead>({
    queryKey: ["feedback", tripId],
    queryFn: () => getFeedback(tripId),
    retry: false,
  });

  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Prefill from existing feedback so the form supports re-rating.
  useEffect(() => {
    if (existing) {
      setRating(existing.rating);
      setComment(existing.comment ?? "");
    }
  }, [existing]);

  const mutation = useMutation({
    mutationFn: () =>
      submitFeedback(tripId, { rating, comment: comment.trim() || null }),
    onSuccess: (saved) => {
      queryClient.setQueryData(["feedback", tripId], saved);
      setError(null);
    },
    onError: (err) => setError(formatError(err)),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (rating < 1) {
      setError("Please pick a star rating first.");
      return;
    }
    mutation.mutate();
  }

  return (
    <section className="card">
      <h3>Rate this trip</h3>
      {existing && (
        <p className="muted">
          You rated this {existing.rating}★ — update below to change it.
        </p>
      )}
      <form onSubmit={onSubmit}>
        {error && <div className="error">{error}</div>}
        <div className="stars" role="radiogroup" aria-label="Rating">
          {STARS.map((n) => (
            <button
              type="button"
              key={n}
              className={n <= rating ? "star on" : "star"}
              aria-label={`${n} star${n > 1 ? "s" : ""}`}
              aria-pressed={n === rating}
              onClick={() => setRating(n)}
            >
              ★
            </button>
          ))}
        </div>
        <label htmlFor="fb-comment">Comment (optional)</label>
        <textarea
          id="fb-comment"
          value={comment}
          maxLength={2000}
          rows={3}
          onChange={(e) => setComment(e.target.value)}
          placeholder="What worked, what you'd change…"
        />
        <div style={{ marginTop: "0.75rem" }}>
          <button type="submit" disabled={mutation.isPending}>
            {mutation.isPending
              ? "Saving…"
              : existing
                ? "Update rating"
                : "Submit rating"}
          </button>
        </div>
      </form>
    </section>
  );
}
