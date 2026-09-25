from shared.http import ok


def handler(event, context):
    # TODO person 3: if state is "lobby", read optional {totalRounds} (clamp 1-10, default 3) into META.
    # If round >= totalRounds: return error("Game over", 409).
    # Bump round, call ai.prompt_gen.generate_prompt(previous_prompts),
    # set state "drawing" + endsAt, publish "round_started".
    return ok({"round": 1, "prompt": "A penguin running a lemonade stand", "endsAt": 0})
