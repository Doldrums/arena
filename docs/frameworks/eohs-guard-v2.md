# EoH-S: bounded handling of an impossible native pair

`eoh-s-gateway-v2` is a separate recipe at the same source pin
`FeiLiu36/EoH-S@8310b056ab0d4ea83d194f1d9e8c7873c0a3b892`.
The original recipe, failed run and its evidence remain unchanged.

The first `gpt-5.6-sol` pilot, `1cdf3a3ba31b45e1a9588a4b567b6ffc`,
evaluated two generated functions on the genuine native OBP training data.
Both had the same 33-component score vector (mean
`-0.03778783872900766`). Native duplicate-score handling marks the second
function invalid; complementary survival retains only one valid function.
Native `run()` then advances its generation to 2. Its complementary selector
requires two functions and raises; the native search catches this exception
and retries without increasing the sample or generation counter. The outer
2400-second deadline terminated the process. No completed complementary search
or four-generation result is established.

Source anchors: `code/llm4ad/method/eohs/population.py:189` (registration),
`:213` (duplicate scores), `:68` (survival), `:293` (pair rejection);
`code/llm4ad/method/eohs/eohs.py:233` (search/retry), `:317` (run).
The original sample record SHA-256 is
`06ce99b916e9a0b8318974112d2d9e2913b81349fd6ecd56997eaab3dd145d84`.
It remains under that run's private `artifacts/results/` directory. The queue's
terminal timeout is authoritative; its inner process receipt still says
`running` because the outer deadline killed the writer.

The new driver verifies the exact native loop/population file hashes before
imports. It invokes the same native selector first. Only its exact
fewer-than-two-valid-functions error is converted into a dedicated stop that
escapes the native retry loop. The sampler thread records its partial state,
releases the evaluator pool and returns; after native joining, the driver exits
75. `selection-guard-v2.json` explicitly records
`partial_insufficient_population`, `native_completed:false`, native scores,
population/code hashes, generation and registered sample count.

Before that stop, native behavior is unchanged. There are no extra proposals,
padded duplicates, replacement pairs, score changes or fallback operators.
An ordinary native return and an unexpected native error have separate states.
The existing task, provider seam, eight registered samples, four-generation
target, population two, single evaluator and 2400-second outer limit remain.
An insufficient population is a partial search, not an improved result.

`scripts/deployment/check_eohs_guard_v2.py` uses the actual pinned population
and sampler-thread methods, with network denied. It replays duplicate-score
registration, proves the singleton exits with 75, checks that a healthy pair
still uses native selection and verifies hook restoration. It executes no
candidate program, evaluator or model. The separate preparation script writes
seven exact-model templates and plans without control changes or admission.

On the VM the network-denied native fixture passed as UID 998 at
`/srv/arena/build/eohs-guard-v2-conformance-owner/native-thread-20260921/conformance.json`:
the actual sampler thread joined, the partial exit was 75, healthy native pair
selection worked, and both hooks were restored. It made zero model or candidate
evaluation calls. Local focused tests passed 43 cases. Seven plans were prepared
and reproduced as UID 998 under
`/srv/arena/configs/eohs-guard-v2-pilots-20260921`; their control merge was checked
in memory only. They bind the isolated staged app at
`/srv/arena/build/eohs-guard-v2-app-20260921`. Deployment to another app path
requires a new active-app plan verification; these preparation hashes are not
portable across application paths. No run was admitted by preparation.

For comparison, MCTS-v2 run `b6f638a6a8e041138573c4a671f6176d`
reached actual tree search, then stopped at its explicit eight-proposal guard.
It preserved eight evaluation artifacts: six finite native objectives and two
generated-code `NameError` failures. Two valid seeds required three attempts;
native operator weights `[0,1,2,2,1]` then require one e2, two m1 and two m2
expansions. The first m2 needed a retry, so the second m2 would require proposal
nine. No cap or failure statistic was changed. This is a bounded partial
native search, not a transport failure or native completion.
