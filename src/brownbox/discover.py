"""Stage 3: find candidate intents in the DEV conversations, bottom-up.

1. An LLM writes each conversation's goal in one line: what the customer wanted, not how it ended.
2. The goals are embedded and over-clustered: more clusters than we expect intents.
3. An LLM names each cluster. Merging and splitting them is a human job, in stage 4.

Only DEV conversations are used. Output: results/discovery/.
"""

import json
import random
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Literal

import numpy as np
from fastembed import TextEmbedding
from numpy.typing import NDArray
from pydantic import BaseModel, Field
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score

from brownbox import llm
from brownbox.models import Conversation
from brownbox.parse import load

OUT = Path(__file__).resolve().parents[2] / "results" / "discovery"
GOAL_MODEL = "claude-opus-5-5"
NAME_MODEL = "claude-opus-5-5"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
N_CLUSTERS = 35  # Deliberately more than we expect intents: merging is easier than splitting.
K_SWEEP = range(15, 60, 5)
EXAMPLES_PER_NAME = 20
WORKERS = 8
SEED = 42


class Goal(BaseModel):
    goal: str = Field(description="One short line, starting with a verb: what the customer wanted.")
    kind: Literal["inform", "act"]
    secondary_goal: str | None = Field(
        description="A second, separate request in the same conversation, written the same way."
    )


class ClusterName(BaseModel):
    name: str = Field(description="2 to 5 words naming what these customers want done.")
    description: str = Field(description="One sentence describing the requests in this group.")
    coherence: Literal["tight", "mixed"]
    mixed_with: str | None = Field(description="If mixed: what else is in the group.")


GOAL_SYSTEM = """You read a customer support conversation from BrownBox, an online retailer, \
and write down what the customer wanted.

Rules:
- Describe the customer's request, not how the conversation ended or what the agent offered.
- One short line starting with a verb, from the customer's side: "Return a damaged item for \
a refund".
- Keep it generic: say "item" or "order" instead of product names. Leave out names, order \
numbers and dates.
- If the opening message is vague, use what the customer asks for once they explain.
- If the customer makes a second, separate request, put it in secondary_goal. Follow-up questions \
about the same request are not a second request. Otherwise secondary_goal is null.
- kind is "act" if they want something done or changed (return, cancel, change an address, reset \
a password) and "inform" if they only want information (a policy, a status, how to do something).

Examples:
- "My headphones arrived with a cracked case, I want to send them back." The agent offers a \
replacement, which the customer accepts.
  -> goal: "Return a damaged item", kind: act, secondary_goal: null
- "When will my order arrive? Also, can I still change the delivery address?"
  -> goal: "Find out when an order will arrive", kind: inform, \
secondary_goal: "Change the delivery address for an order"
- "I have a question about my account." Later: "I can't log in, I forgot my password."
  -> goal: "Reset a forgotten password", kind: act, secondary_goal: null"""

NAME_SYSTEM = """You are given customer goals from one group of support conversations at \
BrownBox, an online retailer. Name what these customers want done.

- name: 2 to 5 words, from the customer's side, e.g. "Return damaged item", \
"Track a late delivery".
- description: one sentence covering the requests in the group.
- coherence: "tight" if the goals are one kind of request; "mixed" if they are clearly two or \
more different requests. If mixed, name the most common one and say what else is there in \
mixed_with."""


def format_transcript(conv: Conversation) -> str:
    return "\n\n".join(
        f"{'Customer' if t.role == 'customer' else t.speaker}: {t.text}" for t in conv.turns
    )


def summarise(conv: Conversation) -> Goal:
    req = llm.Request(
        model=GOAL_MODEL,
        system=GOAL_SYSTEM,
        user=format_transcript(conv),
        max_tokens=2000,
        effort="low",
    )
    return llm.structured(req, Goal).output


def embed(texts: list[str]) -> NDArray[np.float32]:
    vectors = np.array(list(TextEmbedding(EMBED_MODEL).embed(texts)), dtype=np.float32)
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def cluster(vectors: NDArray[np.float32], k: int) -> NDArray[np.int64]:
    """Ward clustering on normalised vectors: deterministic, and every goal lands somewhere."""
    labels: NDArray[np.int64] = AgglomerativeClustering(n_clusters=k).fit_predict(vectors)
    return labels


def name_cluster(goals: list[str]) -> ClusterName:
    sample = random.Random(SEED).sample(goals, min(len(goals), EXAMPLES_PER_NAME))
    req = llm.Request(
        model=NAME_MODEL,
        system=NAME_SYSTEM,
        user="\n".join(f"- {g}" for g in sorted(sample)),
        max_tokens=2000,
        effort="medium",
    )
    return llm.structured(req, ClusterName).output


def run_all[I, O](fn: Callable[[I], O], items: list[I], label: str) -> list[O]:
    """Run fn over items in parallel, keep their order, and print progress as it goes."""
    done: dict[int, O] = {}
    with ThreadPoolExecutor(WORKERS) as pool:
        futures = {pool.submit(fn, item): i for i, item in enumerate(items)}
        for future in as_completed(futures):
            done[futures[future]] = future.result()
            if len(done) % 50 == 0 or len(done) == len(items):
                print(f"  {label}: {len(done)}/{len(items)}", flush=True)
    return [done[i] for i in range(len(items))]


def main() -> None:
    convs = load("dev")
    print(f"summarising {len(convs)} DEV conversations with {GOAL_MODEL}...", flush=True)
    goals = run_all(summarise, convs, "goals")

    vectors = embed([g.goal for g in goals])
    sweep = {
        k: float(silhouette_score(vectors, cluster(vectors, k), metric="cosine")) for k in K_SWEEP
    }
    labels = cluster(vectors, N_CLUSTERS)

    members: dict[int, list[int]] = {c: [] for c in range(N_CLUSTERS)}
    for i, c in enumerate(labels):
        members[int(c)].append(i)
    print(f"naming {N_CLUSTERS} clusters with {NAME_MODEL}...", flush=True)
    names = run_all(name_cluster, [[goals[i].goal for i in members[c]] for c in members], "names")

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "goals.jsonl").open("w") as f:
        for conv, goal, c in zip(convs, goals, labels, strict=True):
            f.write(json.dumps({"id": conv.id, "cluster": int(c), **goal.model_dump()}) + "\n")
    clusters = [
        {
            "cluster": c,
            **names[c].model_dump(),
            "size": len(members[c]),
            "act_share": sum(goals[i].kind == "act" for i in members[c]) / len(members[c]),
            "ids": [convs[i].id for i in members[c]],
        }
        for c in members
    ]
    (OUT / "clusters.json").write_text(json.dumps(clusters, indent=2))
    (OUT / "report.md").write_text(report(convs, goals, labels, clusters, sweep))
    print(f"wrote {OUT.relative_to(OUT.parents[1])}/: goals.jsonl, clusters.json, report.md")


def report(
    convs: list[Conversation],
    goals: list[Goal],
    labels: NDArray[np.int64],
    clusters: list[dict[str, object]],
    sweep: dict[int, float],
) -> str:
    n = len(convs)
    by_size = sorted(clusters, key=lambda c: -int(str(c["size"])))
    lines = [
        "# Discovery report",
        "",
        f"{n} DEV conversations. Goals by `{GOAL_MODEL}`, embeddings `{EMBED_MODEL}`, "
        f"Ward clustering into {N_CLUSTERS} clusters, names by `{NAME_MODEL}`.",
        "",
        "## Clusters by size",
        "",
        "| # | Name | Size | Share | Act | Coherence |",
        "|---|---|---|---|---|---|",
    ]
    for c in by_size:
        size = int(str(c["size"]))
        act = float(str(c["act_share"]))
        lines.append(
            f"| {c['cluster']} | {c['name']} | {size} | {size / n:.1%} | {act:.0%} "
            f"| {c['coherence']} |"
        )

    lines += ["", "## Each cluster", ""]
    for c in by_size:
        ids = [int(i) for i in c["ids"]]  # type: ignore[attr-defined]
        index = {conv.id: k for k, conv in enumerate(convs)}
        lines += [f"### {c['cluster']}. {c['name']} ({c['size']})", "", str(c["description"])]
        if c["mixed_with"]:
            lines.append(f"\n**Mixed with:** {c['mixed_with']}")
        lines.append("")
        for i in sorted(random.Random(SEED).sample(ids, min(len(ids), 6))):
            lines.append(f"- {goals[index[i]].goal} `#{i}`")
        lines.append("")

    secondary = [(conv.id, g) for conv, g in zip(convs, goals, strict=True) if g.secondary_goal]
    lines += [
        "## Second requests",
        "",
        f"{len(secondary)} of {n} conversations ({len(secondary) / n:.0%}) have a second request.",
        "",
    ]
    lines += [f"- {g.goal} → **{g.secondary_goal}** `#{i}`" for i, g in secondary[:15]]

    kinds = Counter(g.kind for g in goals)
    lines += [
        "",
        "## Inform vs act",
        "",
        f"act {kinds['act']} ({kinds['act'] / n:.0%}), inform {kinds['inform']} "
        f"({kinds['inform'] / n:.0%})",
        "",
        "## Choosing the number of clusters",
        "",
        "Silhouette (cosine) for each k. Higher means tighter, better-separated clusters. "
        f"We over-cluster on purpose (k = {N_CLUSTERS}) and merge by hand.",
        "",
        "| k | silhouette |",
        "|---|---|",
    ]
    lines += [f"| {k} | {s:.3f} |" for k, s in sweep.items()]

    lines += [
        "",
        "## Spot-check: 10 random goals against the customer's own words",
        "",
        "Check each goal says what the customer wanted, not how it ended.",
        "",
    ]
    for k in sorted(random.Random(SEED).sample(range(n), 10)):
        first = [t.text for t in convs[k].turns if t.role == "customer"][:2]
        lines += [
            f"**#{convs[k].id}** goal: *{goals[k].goal}* (cluster {int(labels[k])})",
            "",
            *[f"> {text[:300]}" for text in first],
            "",
        ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
