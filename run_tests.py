"""
run_tests.py – Exhaustive test runner over all configured dimensions.

Dimensions looped automatically:
  - queries        (defined in QUERIES)
  - models         (defined in MODELS)
  - reasoning      [True, False]
  - system_prompts (defined in SYSTEM_PROMPTS)
  - tool combos    (powerset of ALL_TOOLS  → enabled_tools)
  - preload combos (powerset of PRELOADABLE → preloaded_info)

Total runs = len(QUERIES) × len(MODELS) × 2 × len(SYSTEM_PROMPTS)
           × 2^len(ALL_TOOLS) × 2^len(PRELOADABLE)

Tip: comment out entries in MODELS or SYSTEM_PROMPTS to reduce scope.
"""

import itertools
from tools.time import TimeTool
from tools.geo import GeoTool
from tools.user_data import UserDataTool
from tools.search import SearchTool
from tools.rag import RAGTool
from main import AICall
from db import ResultsDB

# ------------------------------------------------------------------ #
# Dimensions                                                           #
# ------------------------------------------------------------------ #
# Add new models here to test them, consider run time
MODELS = [
    #"qwen3.5:0.8b",
    "qwen3.5:9b",
    #"qwen3.5:27b",
    #"gemma4:e4b",
    #"gemma4:12b",
]

SYSTEM_PROMPTS = {
    "user_data":      "If you have access to the user_data tools, check the data first before answering and save useful information if you deem it useful when being requested in the future.",
    "priority":       "RAG data has prio over web data, so use the RAG tool before the search tool if available. If neither are available, ignore this instruction.",
    "json_always":    "Antworte ausschließlich im JSON-Format. Kein Fließtext, keine Erklärungen außerhalb des JSON-Objekts.",
}

# Tool instances
_time   = TimeTool()
_geo    = GeoTool()
_user   = UserDataTool()
_search = SearchTool()
_rag    = RAGTool()

# Tools available for "enabled_tools" (callable by AI)
ALL_TOOLS = [_time, _geo, _user, _search, _rag]

# "full"    → all 2^5 combinations
# "single"  → no tools + each individual tool
# "reduced" → manually selected combinations
TOOL_COMBO_MODE = "reduced"

# Tools available for "preloaded_info" (injected directly into user_msg)
# Only tools that implement preload() meaningfully
PRELOADABLE = [_time, _geo, _user]

# Test queries – each paired with a short label for readability in DB/logs
QUERIES = [
    ("world_state",   "Who is my current head of state?"), # ambigous on purpose, test to see whether model detects location germany and current date
    ("search_query",  "What is the current consumer NVIDIA flagship GPU?"),
    ("events_query",  "Welche Events finden gerade in meiner Stadt statt?"),
    ("rag_query",     "Fasse die wichtigsten Inhalte der gespeicherten Dokumente zusammen."),
    ("profile_query", "Gib mir eine Empfehlung passend zu meinen gespeicherten Präferenzen. Passe sie gegebenenfalls an."),
    ("json_query",    "Liste drei Programmiersprachen und ihre Hauptanwendungsgebiete. Antworte ausschließlich als valides JSON."),
]

# ------------------------------------------------------------------ #
# Powerset helper                                                      #
# ------------------------------------------------------------------ #

def powerset(lst):
    """Return all subsets of lst, including empty set."""
    return [
        list(combo)
        for r in range(len(lst) + 1)
        for combo in itertools.combinations(lst, r)
    ]


def get_tool_combos():
    if TOOL_COMBO_MODE == "full":
        return powerset(ALL_TOOLS)

    if TOOL_COMBO_MODE == "single":
        return [
            [],
            *[[tool] for tool in ALL_TOOLS],
        ]

    if TOOL_COMBO_MODE == "reduced":
        return [
            [],
            [_time, _rag, _search],
            [_geo, _rag, _search],
            [_time, _geo, _search, _rag],
            [_time, _user]
        ]

    raise ValueError(f"Unknown TOOL_COMBO_MODE: {TOOL_COMBO_MODE}")

# ------------------------------------------------------------------ #
# Runner                                                               #
# ------------------------------------------------------------------ #


def run_all(dry_run: bool = False):
    db = ResultsDB()
 
    tool_combos    = powerset(ALL_TOOLS)    # 2^5 = 32
    # Only test the two extremes: 
    # 1. no information preloaded
    # 2. all preloadable information preloaded 
    preload_combos = [
      [],
      PRELOADABLE,
    ]
 
    total = (
        len(QUERIES)
        * len(MODELS)
        * 2  # reasoning on/off
        * len(SYSTEM_PROMPTS)
        * len(tool_combos)
        * len(preload_combos)
    )
 
    print(f"Total configured runs: {total}")
    if dry_run:
        print("Dry run – exiting without executing.")
        return
 
    def is_redundant(tools, preloads):
        """Skip combinations where a tool is both preloaded and available as callable tool.
        Preloading and tool-calling the same source gives identical context twice."""
        preload_types = {type(t) for t in preloads}
        tool_types    = {type(t) for t in tools}
        return bool(preload_types & tool_types)
 
    count = 0
    skipped = 0
    errors = 0
 
    for (query_name, query), model, reasoning, (prompt_name, system_prompt), tools, preloads in itertools.product(
        QUERIES,
        MODELS,
        [False, True],
        SYSTEM_PROMPTS.items(),
        tool_combos,
        preload_combos,
    ):
        if is_redundant(tools, preloads):
            skipped += 1
            print(f"  → skipped\n")
            continue
 
        count += 1
        tool_names    = [t.__class__.__name__ for t in tools]
        preload_names = [t.__class__.__name__ for t in preloads]
 
        label = (
            f"[{count+skipped}/{total}] {query_name} | {model} | "
            f"reasoning={'on' if reasoning else 'off'} | prompt={prompt_name} | "
            f"tools={tool_names} | preload={preload_names}"
        )
        print(label)
 
        try:
            call = AICall(
                enabled_tools=tools,
                preloaded_info=preloads,
                system_prompt=system_prompt,
                reasoning=reasoning,
                model=model,
                query=query,
                db=db,
            )
            response = call.ai_call()
            preview = (response or "")[:100].replace("\n", " ")
            print(f"  → {preview}\n")
 
        except Exception as e:
            errors += 1
            print(f"  [ERROR] {e}\n")
 
    print(f"\nDone. {count} runs, {skipped} skipped (redundant), {errors} errors.")
    print(f"Results saved to results.db\n")
    print("Quick summary (last 10 runs):")
    for row in db.summary()[:10]:
        print(
            f"  run {row['id']:>4} | {row['model']:<15} | "
            f"{row['query'][:45]:<45} | tools={row['tool_call_count']} | {row['duration_ms']}ms"
        )


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    run_all(dry_run=dry_run)
