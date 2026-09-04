# Question/evidence relevance audit

This audit checks the frozen Customer Service set against the complete context packet for each pair.
It verifies candidate membership, same-document provenance, bilingual ID parity, source-frame offsets, context hashes, block hashes, and a conservative content-token relevance proxy.
The token proxy is a deterministic guardrail, not a substitute for the Codex full-context review.

- Pairs: 100; language rows: 200
- Status: `{'pass': 100}`
- Evidence distribution: `{'2': 68, '5': 1, '3': 13, '4': 2, '1': 16}`
- Answer content coverage: min `0.4444`, mean `0.7631`
- Result: every selected block must contribute question/answer terms and every gold quote must resolve exactly.

| Pair | Status | Evidence | Answer coverage | Selected blocks |
|---|---|---:|---:|---|
| `Q-001` | pass | 2 | 0.81 | `833c7618`, `724d26e2` |
| `Q-002` | pass | 2 | 0.86 | `724d26e2`, `b9899548` |
| `Q-003` | pass | 5 | 0.75 | `bc51c3d9`, `3d9321dd`, `4270da4c`, `8ed480ba`, `8fd1b794` |
| `Q-004` | pass | 3 | 0.84 | `04fa120c`, `4cb893dc`, `0de5a970` |
| `Q-005` | pass | 2 | 0.86 | `eb2ebf98`, `89ec02e1` |
| `Q-006` | pass | 2 | 0.78 | `32161388`, `62f9a09d` |
| `Q-007` | pass | 2 | 0.86 | `32161388`, `c5c4c17f` |
| `Q-008` | pass | 3 | 0.81 | `a88667b7`, `85bd9c8e`, `5127b280` |
| `Q-009` | pass | 2 | 0.75 | `aaab89bf`, `88695618` |
| `Q-010` | pass | 2 | 0.79 | `6f0c387b`, `37f50132` |
| `Q-011` | pass | 2 | 0.79 | `36789817`, `bac92cce` |
| `Q-012` | pass | 2 | 0.79 | `7a457e5c`, `fa675707` |
| `Q-013` | pass | 2 | 0.72 | `44157573`, `cf1f57e0` |
| `Q-014` | pass | 2 | 0.59 | `441256a8`, `72dd6f50` |
| `Q-015` | pass | 4 | 0.75 | `84875d88`, `57b408ca`, `eb06abbc`, `f06eeb80` |
| `Q-016` | pass | 2 | 0.74 | `7e1a62c7`, `0ccb8b69` |
| `Q-017` | pass | 1 | 0.70 | `43434cb0` |
| `Q-018` | pass | 2 | 0.69 | `ecb1143f`, `82ef2627` |
| `Q-019` | pass | 2 | 0.77 | `6f442d4b`, `683f18e6` |
| `Q-020` | pass | 2 | 0.85 | `dbca2b5a`, `1190a45f` |
| `Q-021` | pass | 2 | 0.70 | `b60ce24d`, `ad49e55f` |
| `Q-022` | pass | 3 | 0.81 | `aba5c3ef`, `ae418564`, `d4e1d4fc` |
| `Q-023` | pass | 2 | 0.93 | `8eefd80d`, `31b5dd16` |
| `Q-024` | pass | 2 | 0.75 | `0528f0b9`, `b510a03e` |
| `Q-025` | pass | 2 | 0.70 | `4a519d38`, `12d6aaad` |
| `Q-026` | pass | 1 | 0.76 | `3fbed70d` |
| `Q-027` | pass | 2 | 1.00 | `0c80bfa0`, `92de127d` |
| `Q-028` | pass | 2 | 0.69 | `2a3ade55`, `82763a83` |
| `Q-029` | pass | 1 | 0.78 | `5a7fc3bd` |
| `Q-030` | pass | 2 | 0.81 | `e466a3e1`, `006d8e6b` |
| `Q-031` | pass | 2 | 0.76 | `0a3e9e25`, `818e0932` |
| `Q-032` | pass | 2 | 0.75 | `cf6a9c70`, `b1147279` |
| `Q-033` | pass | 1 | 0.88 | `9213a4bb` |
| `Q-034` | pass | 2 | 0.81 | `3a682a15`, `8aecb252` |
| `Q-035` | pass | 1 | 0.80 | `54a5ae0e` |
| `Q-036` | pass | 2 | 0.64 | `0b8cd0d8`, `537310b8` |
| `Q-037` | pass | 3 | 0.86 | `15938877`, `79d677ad`, `c63a4385` |
| `Q-038` | pass | 2 | 0.76 | `1c87234f`, `d4980606` |
| `Q-039` | pass | 2 | 0.62 | `7e090661`, `af255485` |
| `Q-040` | pass | 2 | 0.84 | `89cf7641`, `e2441363` |
| `Q-041` | pass | 2 | 0.87 | `aa1a9020`, `0cff8f5c` |
| `Q-042` | pass | 2 | 0.67 | `f2289449`, `0840bab1` |
| `Q-043` | pass | 2 | 0.82 | `33e10a89`, `65aa662f` |
| `Q-044` | pass | 1 | 1.00 | `89d399fa` |
| `Q-045` | pass | 2 | 0.68 | `6af6a140`, `b9937b70` |
| `Q-046` | pass | 1 | 0.88 | `f02b327f` |
| `Q-047` | pass | 1 | 0.81 | `304579c0` |
| `Q-048` | pass | 2 | 0.67 | `ebd82415`, `79da6936` |
| `Q-049` | pass | 2 | 0.73 | `88a61bbc`, `0f01b620` |
| `Q-050` | pass | 2 | 0.64 | `aeaf90b5`, `bb9735df` |
| `Q-051` | pass | 2 | 0.76 | `14bc83c7`, `9d1e53fd` |
| `Q-052` | pass | 2 | 0.47 | `e43b60ee`, `d7d2bc93` |
| `Q-053` | pass | 2 | 0.71 | `10f082e0`, `cf516841` |
| `Q-054` | pass | 2 | 0.84 | `f24fac39`, `48b55cf6` |
| `Q-055` | pass | 1 | 0.54 | `7059c14f` |
| `Q-056` | pass | 2 | 0.70 | `c31cd99a`, `f42f57b0` |
| `Q-057` | pass | 2 | 0.84 | `1b2c7958`, `e00425b6` |
| `Q-058` | pass | 1 | 0.80 | `e87e22a2` |
| `Q-059` | pass | 2 | 0.75 | `9a5a5bff`, `f5872d3c` |
| `Q-060` | pass | 2 | 0.92 | `ab459710`, `d2849132` |
| `Q-061` | pass | 2 | 0.58 | `f6fd63f2`, `93ffa849` |
| `Q-062` | pass | 2 | 0.79 | `0e8a4859`, `03a4fccb` |
| `Q-063` | pass | 3 | 0.94 | `a13c3553`, `9078acec`, `0b9dd330` |
| `Q-064` | pass | 2 | 0.69 | `5fc0a06a`, `01143d51` |
| `Q-065` | pass | 1 | 0.70 | `af31b6ec` |
| `Q-066` | pass | 2 | 0.74 | `b60d283b`, `d6a2438e` |
| `Q-067` | pass | 1 | 0.45 | `a3662689` |
| `Q-068` | pass | 2 | 0.87 | `51405423`, `feb09c00` |
| `Q-069` | pass | 3 | 0.74 | `fbf822a7`, `eae4f314`, `18a45189` |
| `Q-070` | pass | 2 | 0.86 | `01cd477a`, `8dba79ed` |
| `Q-071` | pass | 2 | 0.44 | `183e963a`, `33088b55` |
| `Q-072` | pass | 3 | 0.79 | `15ed12eb`, `25c77477`, `09ef238c` |
| `Q-073` | pass | 1 | 0.80 | `04f1b52b` |
| `Q-074` | pass | 2 | 0.64 | `8533530e`, `29f43702` |
| `Q-075` | pass | 2 | 0.72 | `5e5c51b3`, `b2cee766` |
| `Q-076` | pass | 2 | 0.85 | `0fc19ad4`, `f28a4c35` |
| `Q-077` | pass | 2 | 1.00 | `494eba00`, `4f3d2903` |
| `Q-078` | pass | 2 | 0.71 | `1c16631a`, `fd0ce992` |
| `Q-079` | pass | 3 | 0.63 | `a705dc8c`, `de3de3b9`, `bafbe93c` |
| `Q-080` | pass | 2 | 0.71 | `de3de3b9`, `acfcfc10` |
| `Q-081` | pass | 1 | 0.47 | `aee81160` |
| `Q-082` | pass | 3 | 0.80 | `695ad5a7`, `a6546993`, `6bb5767a` |
| `Q-083` | pass | 2 | 0.92 | `0c1c7d8a`, `83b0f8da` |
| `Q-084` | pass | 1 | 0.73 | `0121bbc3` |
| `Q-085` | pass | 2 | 0.80 | `18c63118`, `e8fbf22f` |
| `Q-086` | pass | 2 | 0.64 | `64c7ce15`, `2f0fbedc` |
| `Q-087` | pass | 2 | 0.88 | `594cc248`, `13759793` |
| `Q-088` | pass | 2 | 0.72 | `d3189db7`, `8989f72f` |
| `Q-089` | pass | 1 | 0.89 | `3252b308` |
| `Q-090` | pass | 2 | 0.70 | `57de6a0a`, `cb248990` |
| `Q-091` | pass | 2 | 0.64 | `87c05b8e`, `44b909e7` |
| `Q-092` | pass | 3 | 0.75 | `067a1684`, `d9934c94`, `3ac82c6c` |
| `Q-093` | pass | 2 | 1.00 | `b76b2605`, `e3bace6b` |
| `Q-094` | pass | 2 | 0.75 | `0af88c60`, `e8550a88` |
| `Q-095` | pass | 3 | 0.67 | `2cc3db60`, `7b507311`, `dee55ef8` |
| `Q-096` | pass | 4 | 0.73 | `84bf0b6c`, `c929ed63`, `1d4788df`, `9c7f8f5e` |
| `Q-097` | pass | 2 | 0.91 | `1d4788df`, `9c7f8f5e` |
| `Q-098` | pass | 2 | 0.86 | `6456b41d`, `65a39d84` |
| `Q-099` | pass | 3 | 0.85 | `407577d5`, `647b4f2b`, `36995834` |
| `Q-100` | pass | 3 | 0.75 | `1e648057`, `75118c37`, `64c16e90` |

A `review` status means the deterministic guardrail found a possible mismatch; it must be inspected before retrieval.
