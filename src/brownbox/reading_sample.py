"""Write a random sample of DEV conversations to a markdown file for reading by hand."""

import random

from brownbox.parse import load
from brownbox.paths import NOTES, ROOT

OUT = NOTES / "reading-sample.md"
SEED = 7
N = 50

HEADER = """# Reading sample: {n} DEV conversations

Random sample (seed {seed}) from the DEV split only. Read these before seeing any LLM output.
Write notes in your own words. Per conversation, the `My notes:` line is for a quick label.

## My notes

**Candidate intents** (name, rough count, what the customer wants done):
-

**Odd things / data quirks:**
-

**Boundaries I'm unsure about** (pairs that could be confused):
-

---
"""


def main() -> None:
    dev = load("dev")
    sample = random.Random(SEED).sample(dev, N)
    parts = [HEADER.format(n=N, seed=SEED)]
    for k, conv in enumerate(sample, start=1):
        parts.append(f"\n## {k} of {N} · conversation {conv.id}\n\nMy notes: \n")
        for turn in conv.turns:
            text = turn.text.replace("\n", "  \n")
            if turn.role == "customer":
                parts.append(f"\n**Customer:** {text}\n")
            else:
                parts.append(f"\n*{turn.speaker}:* {text}\n")
        parts.append("\n---\n")
    OUT.write_text("".join(parts))
    print(f"wrote {N} conversations to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
