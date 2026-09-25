from shared.http import ok


def handler(event, context):
    # TODO person 3: if state is "lobby", read optional {totalRounds} (clamp 1-10, default 3)
    # and {mode} ("draw" | "survive" | "wit" | "mixed", default "mixed"),
    # {elimination} (default false), {reviveAfter} (clamp 1-5, default 2)
    # and {themeEvery} (0 off / 1 every round / 2 every 2nd round, default 2) into META.
    # Clear META.outcome for the new round.
    # Themed round (shared.themes.is_themed(round, themeEvery)): theme = pick_theme(used ids),
    #   prompt = generate_prompt(previous, theme=prompt_theme(theme, roundMode), mode=roundMode),
    #   META.theme = themes.public(theme), state "theme", themeEndsAt = now + INTRO_SECONDS;
    #   the round only starts (state "drawing" + endsAt) in begin_round.
    # Otherwise clear META.theme and go straight to "drawing".
    # If round >= totalRounds: return error("Game over", 409).
    # Bump round. roundMode = mode, or for "mixed": ["draw", "survive", "wit"][(round - 1) % 3].
    # Call ai.prompt_gen.generate_prompt(roundMode, previous_prompts),
    # set state "drawing" + endsAt, publish "round_started".
    return ok({"round": 1, "prompt": "A penguin running a lemonade stand", "endsAt": 0})
