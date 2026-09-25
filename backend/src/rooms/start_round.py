from shared.http import ok


def handler(event, context):
    # TODO person 3: bump round, call ai.prompt_gen.generate_prompt(previous_prompts),
    # set state "drawing" + endsAt, publish "round_started".
    return ok({"round": 1, "prompt": "A penguin running a lemonade stand", "endsAt": 0})
