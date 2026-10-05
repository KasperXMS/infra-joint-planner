# Resident checkpoint: LongBench cell78

2026-10-06. Frozen LongBench representative2 /P1 /Slow /D, n=1.
Original attempt1 settled at23:37:27.588066Z, sequence156. Valid unevaluated
failure: `logical_loop_failed / AgentLoopError / manager turn budget exhausted`.
No terminal answer, format validity or evaluator score; these remain UNKNOWN,
not zero. Old42results remain closed/unpooled; execution001/control007 unchanged.

| Measure | Original observed value |
| --- | --- |
| Manager /Verifier /physical calls | 20 /3 /4 |
| Prepared model actions /actual inference | 0 /0 |
| Successful tools /failed tools | 3BM25 /1oversize read |
| Created specialists | 0 |
| E2E | 168.352s |
| Fixed initial placement | 2,119,778bytes /5.981s |
| Complete action transfer /complete tool work | UNKNOWN /UNKNOWN |
| Successful action transfer receipts | 0bytes /0s;not a complete failed-run total |
| Successful tool work /model backend work | 1.826s /0s |
| Failed physical action wrapper | .162s;not additional complete tool work |
| Manager /Verifier work | 149.114s /8.236s;not additive E2E |
| Cloud API | All23usagesknown,USD.1393583026614757,list-price not invoice |
| Actual SDKrecipient contexts checked | 23;originalprivacyadmissionpassed |
| Graph | 4nodes /0artifactedges /13snapshots;3success,1failure |
| Actual concurrent width /overlap | 3 /1.000s;single logical owner |

Actual path: fail-closed `read_artifact` of the complete original context
->three independent BM25actions executed in parallel onA4 ->quote/discard
model-proposal loop ->20-turn ceiling. No physical model action was prepared,
so zero actual inference is supported by action history, not merely a missing
`reached_model_inference` flag. Three BM25queries each requested20records.
The original Governmental context remains a complete ordered-record container;
the original natural document count is UNKNOWN, not claimedone.

## Quote exposure, feasibility and stopping

Tenquotes:4consumed /5discarded /1pending. All9nonpending exact cards appeared
in actual rootSDK input before commit/discard. The four commits executed:
oneoversize-read failure and three successful retrievals. The read card
reported feasible **physical selection**, not verified read-size legality;
the runtime's size limit subsequently returned `artifact_too_large`.
Do not interpret selection feasibility as guaranteed operator execution success.

Allsix model proposals used statically supported requirements, qualityclassnull.
Five discarded cards predicted `context_limit_exceeded`: the first combined
allthree retrieved artifacts; four later requests reused one retrieved artifact
with smaller prompts or different declared requirements. They are quoted
preflight outcomes, not actual failed inferences. The final prompt-only card
was context-feasible (conservativeinput1874 /context32768 /reservedoutput2048),
but remained pending with no subsequent Manager exposure or commit. Its model
service profile was UNKNOWN/samplecount0/minimumsupport3, not zero.

Verifiercall2 changed evidence_collection->synthesis before these model quotes.
Sevenquote phase-restriction receipts and8deduplicated SDKphase failures can
overlap; they do not add physical calls. There are17control-only batch receipts,
not claimed17distinct turns. Quote-control work6.231s. Independent D adoption
auditor finds0comparisonsets/cards/choices: ordinary Quote use is not use of
multi-candidate alternatives.

Primary cause: fixed Manager-turn budget exhaustion. Observable contributors:
context/composition recovery, synthesis-phase restrictions and quote/discard
overhead; reaching a feasible request only at the final turn did not leave a
commit turn. Semantic evidence adequacy and the Verifier's reasoning remain
pending complete private audit. Do not infer an intrinsic D failure, sufficient
evidence, network causality or a need to tune stopping from this single run.

Allfive model instances remained resident; Workerexit/tccleanup/privacy checks
passed. No reload/OOM/truncation/retry/modelsubstitution, hidden reduction,
warm-start subtraction or source/prompt/budget/scheduler change.

## Append-only provenance / remaining scope

Original admission canonical SHA-256:
`d45f80b69e89a34468f64471369b3816d63b24da6aeedd34c3051713f5a9591e`.
Original journal settlement SHA-256:
`f4316f30f4783334b35ab285821d39bd899a1a3094720635bca381d104754ee1`.
Exclusive remote analysis/resident-cell-078-summary-001.json file SHA-256:
`4a76d4c0ed0fb19c2b2d19346ff764a0839f8cfb7bb4caf3478d818abd7822be`.
The summary binds original result/trace/admission, journal and exit/residency
proof. No payload/gold/dataset/model export toPC or auditmodelcall.

Queue008PID2678456 and cell79atomicPID2957953 verifiedlive23:40:10.828438Z on
LongBench2/P2/Slow/C, reservedseq157at23:37:30Z.78classifiedof168; no79outcome
inferred. All168/private recipient/evidence/failure/adoption audits, frozen
pruning, actualPhaseII and finalreports/Q1–Q10 remain unfinished. Goalactive.
