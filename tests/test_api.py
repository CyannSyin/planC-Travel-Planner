from __future__ import annotations

import unittest

from planner.agent import IntentInterpretation, TravelAgent, TravelIntent
from planner.api import SessionStore
from tests.test_product import sample_pois


class SequentialInterpreter:
    def interpret(self, message, current_intent):
        start_time = "10:00" if current_intent else "09:00"
        return IntentInterpretation(
            intent=TravelIntent(
                city="Test City",
                num_days=2,
                source="osm",
                max_pois=6,
                start_time=start_time,
            ),
            summary="已理解你的行程需求。",
        )


class SessionStoreTest(unittest.TestCase):
    def setUp(self):
        self.store = SessionStore(
            lambda: TravelAgent(
                interpreter=SequentialInterpreter(),
                pois=sample_pois(),
            ),
            max_sessions=2,
        )

    def test_reuses_conversation_state(self):
        session_id, session = self.store.get_or_create(None)
        first = session.agent.respond("去 Test City 两天")
        same_id, same_session = self.store.get_or_create(session_id)
        second = same_session.agent.respond("每天十点出发")

        self.assertEqual(session_id, same_id)
        self.assertEqual("09:00", first.plan.days[0].visits[0].arrival_time)
        self.assertEqual("10:00", second.plan.days[0].visits[0].arrival_time)

    def test_reset_removes_session(self):
        session_id, _ = self.store.get_or_create(None)
        self.assertTrue(self.store.remove(session_id))
        new_id, _ = self.store.get_or_create(session_id)
        self.assertNotEqual(session_id, new_id)


if __name__ == "__main__":
    unittest.main()
