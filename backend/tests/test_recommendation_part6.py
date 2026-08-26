"""Recommendation Part 6 deterministic explanation tests."""

from unittest import TestCase
from unittest.mock import patch

from app.schemas.recommendation_schema import TenantRecommendationRequest
from app.services.recommendation_explanation_service import (
    build_recommendation_reasons,
)
from app.services.wsm_service import rank_knn_candidates
from tests.test_recommendation_part5 import make_knn_response


def ranked_candidate(
    specification: dict | None = None,
    **preference_changes,
):
    preferences, knn = make_knn_response(
        [specification or {}],
        **preference_changes,
    )
    response = rank_knn_candidates(
        knn_response=knn,
        preferences=preferences,
    )
    return preferences, response.candidates[0]


def reason_by_category(candidate, category: str):
    return next(
        reason
        for reason in candidate.recommendation_reasons
        if reason.category == category
    )


class ExplanationContentTests(TestCase):
    def test_strong_location_uses_estimated_drive_wording(self) -> None:
        _, candidate = ranked_candidate()
        reason = reason_by_category(candidate, "location")
        self.assertEqual(reason.strength, "strong")
        self.assertIn("Estimated", reason.text)
        self.assertIn("drive", reason.text)
        self.assertNotIn("live", reason.text.lower())
        self.assertNotIn("traffic", reason.text.lower())

    def test_satisfied_max_commute_uses_limit_wording(self) -> None:
        preferences, candidate = ranked_candidate()
        commute = candidate.commutes[0].model_copy(
            update={"max_commute_minutes": 30, "within_max_commute": True}
        )
        changed = candidate.model_copy(update={"commutes": [commute]})
        reasons = build_recommendation_reasons(
            candidate=changed,
            preferences=preferences,
        )
        location = next(item for item in reasons if item.category == "location")
        self.assertIn("Within your 30-minute commute limit", location.text)
        self.assertIn("estimated", location.text)

    def test_preferred_and_flexible_budget_wording_are_distinct(self) -> None:
        _, preferred = ranked_candidate(
            {"asking_rent_bdt": 20_000},
            maximum_rent_bdt=30_000,
        )
        self.assertIn(
            "preferred maximum budget",
            reason_by_category(preferred, "budget").text,
        )

        _, flexible = ranked_candidate(
            {"asking_rent_bdt": 31_500},
            maximum_rent_bdt=30_000,
            over_budget_percent=5,
        )
        flexible_reason = reason_by_category(flexible, "budget")
        self.assertIn("within your allowed 5% flexibility", flexible_reason.text)
        self.assertNotEqual(flexible_reason.strength, "strong")

    def test_space_reason_uses_actual_requirements_and_area(self) -> None:
        _, candidate = ranked_candidate(
            {"bedrooms": 3, "bathrooms": 2, "area_sqft": 1_200},
            minimum_bedrooms=3,
            minimum_bathrooms=2,
            minimum_area_sqft=1_000,
            maximum_area_sqft=1_400,
        )
        reason = reason_by_category(candidate, "space")
        self.assertIn("bedroom and bathroom requirements", reason.text)
        self.assertIn("1,200 sq ft", reason.text)
        self.assertIn("preferred size range", reason.text)

    def test_amenity_overlap_is_exact_and_absent_preference_is_silent(self) -> None:
        _, candidate = ranked_candidate(
            {"amenities": ["Lift", "CCTV", "Legacy Gym"]},
            nice_to_have_amenities=["Lift", "Parking", "CCTV"],
        )
        reason = reason_by_category(candidate, "amenities")
        self.assertIn("Matches 2 of your 3", reason.text)
        self.assertIn("Lift, CCTV", reason.text)
        self.assertNotIn("Legacy", reason.text)

        _, no_preference = ranked_candidate(
            {"amenities": ["Lift", "Parking"]},
            nice_to_have_amenities=[],
        )
        self.assertNotIn(
            "amenities",
            {item.category for item in no_preference.recommendation_reasons},
        )

    def test_fairness_reason_uses_stored_assessment_without_prediction(self) -> None:
        with patch("app.ml.predictor.predict_monthly_rent") as prediction:
            _, candidate = ranked_candidate(
                {"rent_assessment": {"difference_percent": -5.0}}
            )
        prediction.assert_not_called()
        reason = reason_by_category(candidate, "rent_fairness")
        self.assertIn("model-estimated rent", reason.text)
        self.assertIn("5.0% difference", reason.text)
        self.assertNotIn("objectively", reason.text)

    def test_low_scores_are_not_described_as_strong(self) -> None:
        preferences, candidate = ranked_candidate()
        changed = candidate.model_copy(
            update={
                "destination_access_score": 0.2,
                "budget_score": 0.2,
                "space_score": 0.2,
                "rent_fairness_score": 0.2,
                "property_similarity_score": 0.2,
            }
        )
        reasons = build_recommendation_reasons(
            candidate=changed,
            preferences=preferences,
        )
        self.assertTrue(all(reason.strength != "strong" for reason in reasons))
        self.assertNotIn("rent_fairness", {reason.category for reason in reasons})


class ExplanationSelectionTests(TestCase):
    def test_reason_order_respects_tenant_priority(self) -> None:
        priorities = {
            "location": 1,
            "budget": 5,
            "space": 2,
            "amenities": 1,
            "rent_fairness": 1,
        }
        _, candidate = ranked_candidate(
            {"asking_rent_bdt": 10_000},
            maximum_rent_bdt=30_000,
            priorities=priorities,
        )
        self.assertEqual(candidate.recommendation_reasons[0].category, "budget")

    def test_same_input_produces_identical_structured_reasons(self) -> None:
        preferences, candidate = ranked_candidate(
            {"amenities": ["Lift", "Parking"]},
            nice_to_have_amenities=["Lift", "Parking"],
        )
        first = build_recommendation_reasons(
            candidate=candidate,
            preferences=preferences,
        )
        second = build_recommendation_reasons(
            candidate=candidate,
            preferences=preferences,
        )
        self.assertEqual(first, second)
        self.assertLessEqual(len(first), 5)

    def test_explanations_preserve_scores_rank_and_candidate_order(self) -> None:
        preferences, knn = make_knn_response([{}, {}, {}])
        response = rank_knn_candidates(
            knn_response=knn,
            preferences=preferences,
        )
        self.assertEqual([item.rank for item in response.candidates], [1, 2, 3])
        self.assertEqual(
            [item.final_suitability_score for item in response.candidates],
            sorted(
                [item.final_suitability_score for item in response.candidates],
                reverse=True,
            ),
        )
        self.assertTrue(
            all(item.recommendation_reasons for item in response.candidates)
        )

        payload = response.model_dump(mode="json")
        forbidden = {"confidence", "probability", "accuracy", "reason_score"}

        def walk(value: object) -> None:
            if isinstance(value, dict):
                self.assertTrue(forbidden.isdisjoint(value))
                for item in value.values():
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(payload)

    def test_rebuilding_reasons_cannot_change_final_score_or_rank(self) -> None:
        preferences, candidate = ranked_candidate()
        before = (candidate.final_suitability_score, candidate.rank)
        build_recommendation_reasons(
            candidate=candidate,
            preferences=preferences,
        )
        self.assertEqual(before, (candidate.final_suitability_score, candidate.rank))

    def test_validated_preference_shape_remains_accepted(self) -> None:
        preferences, _ = ranked_candidate()
        restored = TenantRecommendationRequest.model_validate(
            preferences.model_dump(mode="json")
        )
        self.assertEqual(restored, preferences)
