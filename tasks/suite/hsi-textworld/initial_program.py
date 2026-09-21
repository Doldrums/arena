"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def act(observation, valid_actions, history, llm):
    # Zero-shot seed: show the recent transcript and the valid commands, ask for one command.
    recent = history[-6:]
    transcript = "\n".join(f"> {a}\n{o[:400]}" for a, o, _ in recent)
    prompt = ("You are playing a text adventure. Maximise the game score.\n\nRecent transcript:\n" + transcript +
              "\n\nCurrent observation:\n" + observation[:1200] + "\n\nValid commands: " + ", ".join(valid_actions[:60]) +
              "\n\nReply with exactly one command from the list (or another short command).")
    reply = llm(prompt, max_tokens=20).strip().splitlines()[0].strip("`\"' ")
    return reply if reply else (valid_actions[0] if valid_actions else "look")
# EVOLVE-BLOCK-END
