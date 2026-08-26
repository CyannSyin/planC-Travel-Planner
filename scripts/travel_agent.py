"""Interactive natural-language entry point for the PlanC travel agent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from planner.agent import OpenAIIntentInterpreter, TravelAgent
from planner.storage import PlanRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan a trip through natural-language dialogue")
    parser.add_argument("message", nargs="?", help="Initial travel request")
    parser.add_argument("--model", help="Agent model; defaults to AGENT_MODEL or LLM_MODEL")
    parser.add_argument("--database", type=Path, default=Path("data/planner.db"))
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument("--json", action="store_true", help="Print the complete turn as JSON")
    return parser.parse_args()


def save_plan(output_dir: Path, turn) -> Path | None:
    if not turn.plan:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{turn.plan.city.lower().replace(' ', '-')}-{turn.plan.plan_id[:8]}.json"
    path.write_text(
        json.dumps(turn.plan.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def render_turn(turn, args: argparse.Namespace) -> None:
    if args.json:
        print(json.dumps(turn.to_dict(), ensure_ascii=False, indent=2))
        return
    print(f"\nPlanC: {turn.message}")
    output_path = save_plan(args.output_dir, turn)
    if output_path:
        print(f"行程已保存到 {output_path}")


def main() -> int:
    args = parse_args()
    try:
        agent = TravelAgent(
            interpreter=OpenAIIntentInterpreter(model=args.model),
            repository=PlanRepository(args.database),
        )
    except Exception as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1

    print("PlanC AI 旅行规划师。直接描述需求；/reset 重新开始；/quit 退出。")
    pending = args.message
    while True:
        try:
            message = pending if pending is not None else input("\n你: ").strip()
            pending = None
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if message == "/quit":
            return 0
        if message == "/reset":
            agent.reset()
            print("PlanC: 已清空当前行程，我们重新开始。")
            continue
        if not message:
            continue

        try:
            turn = agent.respond(message)
            render_turn(turn, args)
        except Exception as error:
            print(f"\nPlanC: 暂时无法完成规划：{error}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
