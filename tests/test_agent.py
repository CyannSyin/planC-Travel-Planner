from __future__ import annotations

import unittest

from planner.agent import IntentInterpretation, TravelAgent, TravelIntent
from tests.test_product import sample_pois


class StubInterpreter:
    def __init__(self, interpretations):
        self.interpretations = iter(interpretations)

    def interpret(self, message, current_intent):
        return next(self.interpretations)


class TravelAgentTest(unittest.TestCase):
    def test_asks_for_missing_required_information_before_planning(self):
        interpreter = StubInterpreter(
            [
                IntentInterpretation(
                    intent=TravelIntent(num_days=2, source="osm"),
                    summary="你想旅行两天。",
                    question="想去哪个城市？",
                )
            ]
        )
        agent = TravelAgent(interpreter=interpreter, pois=sample_pois())

        turn = agent.respond("想玩两天")

        self.assertEqual("needs_input", turn.status)
        self.assertEqual("想去哪个城市？", turn.message)
        self.assertIsNone(turn.plan)

    def test_plans_from_natural_language_intent(self):
        intent = TravelIntent(
            city="Test City",
            num_days=2,
            source="osm",
            preferences="喜欢博物馆，节奏轻松",
            max_pois=6,
            max_daily_hours=4,
        )
        agent = TravelAgent(
            interpreter=StubInterpreter(
                [IntentInterpretation(intent=intent, summary="我会安排轻松的两日游。")]
            ),
            pois=sample_pois(),
        )

        turn = agent.respond("去 Test City 两天，喜欢博物馆，轻松一点")

        self.assertEqual("planned", turn.status)
        self.assertEqual(2, len(turn.plan.days))
        self.assertIn("已生成行程", turn.message)
        self.assertTrue(all(day.total_minutes <= 240 for day in turn.plan.days))

    def test_follow_up_merges_context_and_replans(self):
        initial = TravelIntent(
            city="Test City", num_days=2, source="osm", max_pois=6
        )
        changed = TravelIntent(
            city="Test City",
            num_days=2,
            source="osm",
            preferences="每天十点出发",
            max_pois=6,
            start_time="10:00",
        )
        agent = TravelAgent(
            interpreter=StubInterpreter(
                [
                    IntentInterpretation(intent=initial, summary="先安排两日游。"),
                    IntentInterpretation(intent=changed, summary="已改为每天十点出发。"),
                ]
            ),
            pois=sample_pois(),
        )

        first = agent.respond("去 Test City 两天")
        second = agent.respond("每天十点再出发")

        self.assertEqual("09:00", first.plan.days[0].visits[0].arrival_time)
        self.assertEqual("10:00", second.plan.days[0].visits[0].arrival_time)
        self.assertNotEqual(first.plan.plan_id, second.plan.plan_id)
        self.assertIn("已重新规划", second.message)

    def test_expanding_days_repairs_retained_max_pois(self):
        intent = TravelIntent(city="Test City", num_days=4, source="osm", max_pois=2)
        request = intent.to_plan_request()
        self.assertEqual(4, request.max_pois)


if __name__ == "__main__":
    unittest.main()
