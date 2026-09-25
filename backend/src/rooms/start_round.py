from shared.http import ok


def handler(event, context):
    # TODO person 3: if state is "lobby", read optional {totalRounds} (clamp 1-10, default 3)
    # and {mode} ("draw" | "survive" | "wit" | "mixed", default "mixed"),
    # {elimination} (default false) and {reviveAfter} (clamp 1-5, default 2) into META.
    # Clear META.outcome for the new round.
    # If round >= totalRounds: return error("Game over", 409).
    # Bump round. roundMode = mode, or for "mixed": ["draw", "survive", "wit"][(round - 1) % 3].
    # Call ai.prompt_gen.generate_prompt(roundMode, previous_prompts),
    # set state "drawing" + endsAt, publish "round_started".
    return ok({"round": 1, "prompt": "A penguin running a lemonade stand", "endsAt": 0})
