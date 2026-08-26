const SUBMISSION_KEY = "dhakanest_recommendation_submission_v1";

export function createRecommendationSubmissionKey(
  uuidFactory: () => string = () => crypto.randomUUID(),
): string {
  const key = uuidFactory();
  if (typeof window !== "undefined") {
    sessionStorage.setItem(SUBMISSION_KEY, key);
  }
  return key;
}

export function getRecommendationSubmissionKey(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(SUBMISSION_KEY);
}
