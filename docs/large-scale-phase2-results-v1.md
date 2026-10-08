# Resident Phase II results — in progress

At2026-10-08 18:09HKT, original118LongBench4/P2/Slow/B0 and119LongBench4/
P1/Slow/B1 both completed/valid/evaluatorpresent, problems[]/incidents[]/
terminalfailureNone/process0/all4Workersverifiedexited/resident5pass/
tc cleanup_errorNone+exactqdiscrestore.118admissionc854e1f6...dc55c/
result88929414...48e09/tracefd2ff1f3...5942e(312events);
119admissionfb88ac33...1d45a/result93fa62c8...81fe2/tracec0449d83...4bb85
(328events). Actualruntime0ff/20-64-20/1200s/fixedBlindQwenVerifier unchanged;
Manager118Qwen/119DeepSeek bindingsmatch. Same020ownedlive10:08:54UTC:
119admitted/120settled=120preserved/0pending/0unresolved/1excluded/73unstarted,
journal5396c121...7cb78. Original117 remainsvalidfailure/evaluationmissing
(not0), no replacement. Full112verified/nextfull128before129. No tuning,
sourcechange orpartialqualityaggregate; all192/all193/finalaudits remain due.

At2026-10-08 18:02HKT, original118LongBench4/P2/Slow/B0 attempt1 ownedlive,
atomic3782341/start198074724, exactargv/revision0ff/ManagerQwen/fixedBlind
QwenVerifier/config25781799...46173/capabilitydaf64110...e013 verified10:02:27UTC.
Same020owner pair unchanged;117admitted/118settled+1pending=119preserved/
0unresolved/1excluded/74unstarted, journal396d7f52...002b8. Original117 valid
semantic failure remains preserved (executionfalse/evaluationmissing,not0).
No replacement/retry/tuning; nextfull128before129/all192/all193/finalaudits due.

At2026-10-08 18:00HKT, original117LongBench4/P1/Fast/E settled as valid semantic
failure, NOT normal completion. Executionfalse/evaluationabsent (missing,not0):
logical_loop_failed/AgentLoopError, "Blind verifier returned complete without
a successful manager model candidate". Existing frozen terminal guard and its
focused regression PASS(exit0), no implementation/harness change orretry.
Admissionproblems[]/incidents[]/process0/all4Workersverifiedexited/resident5pass/
tc cleanup_errorNone+exactrestore. Admission1a87d754...07f69/result29db8b33...
77927/trace2049a9a2...0ad10(297events). Narrowterminalclassification:
stopping/Verifiercompletionprotocol; deepersemantic/context causes deferred
to finalmanualaudit. See `large-scale-resident-phase2-cell0117-stopping-audit-v1.md`.
Same020ownedlive10:00:13UTC,117admitted/118settled=118preserved/0pending/
0unresolved/1excluded/75unstarted; journale274d57a...c4557. No118reservationyet.
Full112verified/nextfull128; all192/all193/finalaudits/qualityanalysis remain due.

At2026-10-08 17:57HKT, original117LongBench4/P1/Fast/E attempt1 is ownedlive,
atomic3777669/start198044780. Exactfrozenargv/revision0ff/ManagerDeepSeek/
fixedBlindQwenVerifier/config8fe0c1b1...34a1a/capabilitydaf64110...e013 verified
09:56:38UTC. Same020owner pair unchanged;116admitted/117settled+1pending=
118preserved/0unresolved/1excluded/75unstarted, journal3d39c6ba...13a89.
No result/qualityclaim yet; no retry/replacement/config orsemantic tuning.
Full112verified; nextfull128 before129/all192/all193/finalaudits remain due.

At2026-10-08 17:54HKT, original115LongBench5/P2/Slow/B1 and116LongBench5/
P1/Fast/B0 both completed/valid/evaluatorpresent. Both have problems[]/
operationalincidents[]/terminalfailureNone/process0/all4Workersverifiedexited/
resident5pass/tc cleanup_errorNone+exactqdiscrestore.115admissionf7c938fb...
247b9/result4f21051e...f7666/tracead4aa644...1a5e(249events);
116admissionb148ef44...83159/result16f9984c...75458/trace4f6642f7...c1dc7
(142events). ActualManager115Qwen/116DeepSeek/fixedBlindQwenVerifier/revision0ff/
20-64-20budgets/1200s service timeout unchanged. Same020supervisor3735395/
197731107/controller3735396/197731109 ownedlive09:54:19UTC;116admitted/
117settled=117preserved/0pending/0unresolved/1excluded/76unstarted. Journal
ba5c5912...92371; original117 notyetreserved. Full112verified/nextfull128
before129; no retry/replacement/qualityaggregate/tuning ornewimplementation.
All192/all193/finalrecipient/private/manual/retention/adoption/quality/Q1–Q10
reports remain required.

At2026-10-08 17:47HKT, original114LongBench5/P1/Slow/A completed/valid/
evaluatorpresent, problems[]/terminalfailureNone/process0/all4Workersverified
exited/resident5pass/tc cleanup_errorNone+exactrestore. Admissionf074cd42...ab3ad/
resulte2e3dedf...8202f/tracef2e8b7f1...976b4(164events). Same020ownedlive;
original115LongBench5/P2/Slow/B1 atomic3768591/start197990267 verifiedexact
argv/revision0ff/ManagerQwen/fixedVerifierQwen/confige817062f...f92f4/
capabilitydaf64110...e013 at09:46:49UTC.114admitted/115settled+1pending=
116preserved/0unresolved/1excluded/77unstarted, journal04047174...a14e2.
No newfinding/retry/replacement/qualityaggregate orsemantic tuning. Full112
verified; nextordinaryfull128 before129. All192/all193/finalaudits remain due.

At2026-10-08 17:42HKT, original113LongBench5/P2/Fast/E completed/valid/
evaluatorpresent, admissionproblems[]/terminalfailureNone, exit0/all4Workers
verifiedexited/resident5pass/tc cleanup_errorNone+exactqdiscrestore. Admission
c47aedc3...f2aee/resultd52448a3...95424/trace9517f931...154a2(241events).
113admitted/114settled=114preserved/0pending/0unresolved/1excluded/79unstarted;
journalb3a6943b...f541a. Same020ownedlive, checking unchanged environment
beforeoriginal114. No retry/replacement/qualityaggregate orsemantic tuning.
Full112 remainsverified/nextfull128; all192/all193/finalaudits remain required.

At2026-10-08 17:39HKT, original113LongBench5/P2/Fast/E attempt1 is live:
atomic3759059/start197929230 exactfrozenargv/revision0ff/ManagerQwen/
VerifierQwen/20-64-20budgets/1200s service timeout verified. Its reservation
09:36:00.812417UTC follows full11209:31:52 andindependentreadback09:34:48;
no cadence bypass. Same020ownedlive,112admitted/113settled+1pending=
114preserved/0unresolved/1excluded/79unstarted. Journal4a70b416...47e2fc.
Trace172events/latestaction.started; no terminal result orqualityclaim yet.
Nextfull128 before129; no retry/replacement/implementation/prompt change.
All192/all193 andfinalaudit reports remain required.

At2026-10-08 17:35HKT, full112 checkpoint completed09:31:52UTC, SHA
b02d164a...5c481; independent owning-node readback09:34:48UTC persisted
5caa70e9...584c9. All113 traces/admission provenance digests and1831 actualSDK
requests (825Manager/824fixedBlindVerifier/182specialist) match;147actualsources
unchanged, currentmanifest/control012/ledger012 match. Actualrecipient scans,
Verifier binding and non-Manager feedback isolation pass. Exact root feedback
matches208profile/418ledger/211rules are visibility only, not adoption/quality.
112admitted/113preserved/0pending/0unresolved/1excluded/80unstarted;
no113reservation at independentreadback. Journal ea2c5236...c0db9 is the exact
130193-byte checkpoint prefix. Nextfull128; any newfinding gates immediately.
See `large-scale-resident-phase2-checkpoint0112-v1.md`. No retry, execution change,
partialqualityaggregate or finalcompletionclaim; all192/all193/finalaudits due.

At2026-10-08 17:28HKT, original111 (MultiHop3/P2/Slow/B1) and112
(MultiHop3/P1/Fast/B0) both completed/valid with evaluator present, no terminal
failure or admission problems, process exit0, all4Workers verified exited,
resident5instances passed, and exact qdisc restoration/cleanup errorNone.
111 admission34ae5410...6fa81/result7335cf4c...e2d5b/traceba676330...fad98
(122events);112 admission47fd75f9...2894f/result8499ca49...7046b/
tracec44df6b1...6ba9e (215events). Actual revision0ff... and fixed Qwen Verifier
remain unchanged; Manager111Qwen/112DeepSeek match their registered cells.
Same020 controller3735396/start197731109 remains owned/live and CPU-active in
the ordinary full112 audit; receipt not yet present at09:27:48UTC. No113
reservation:112admitted/113settled=113preserved/0pending/0unresolved/1excluded/
80unstarted, journal ea2c5236...c0db9. Full112 must pass before113; do not
restart020 or repeat any original attempt. This is execution/provenance
confirmation, not partial quality aggregation or final semantic audit.
All192/all193 and the final recipient/private/manual/retention/adoption/
quality/Q1–Q10 reports remain required.

At2026-10-08 17:18HKT, original110MultiHop3/P1/Slow/A attempt1 completed and
passed originaladmission:executioncompleted/evaluatorpresent, problems[], no
terminalfailure, exit0/all4Workersverifiedexited/residencypass5instances,
tc cleanupNone/qdisc restoredexact. Trace268events/SHA529d169a...d0e28,
admission1c96b114...259c9/result e4fa1293...c2a0a. No score/qualityaggregate read.
Same020ownedlive, original111MultiHop3/P2/Slow/B1 started, atomic3744060/
start197805997 exactargv/revision0ff/budgets verified17:18UTC.110admitted/
111settled+1pending=112preserved/0unresolved/1excluded/81unstarted. Journal
c5fe1d17...e41ca extends original prefix; nextfull112 remainsbefore113.
No retries/replacement/sourcechange; all192/all193/finalaudits still required.

At2026-10-08 17:03HKT, new020 launchedONCE/ownedlive: supervisor3735395/
start197731107/controller3735396/start197731109; supervisorSHA7a565d50...43784.
Independentlive receipt d508a1c3...81d957 verifies exactargv/startticks/source147
andactualfirst-actionfinalguard rejection beforeprivatebody/output. Bootstrap
47a04d9d...3250e0/currentmanifest e8bb0da9...bf0a8e remain pinned. Startup109
admitted/110preserved/0pending/0unresolved/1excluded/83unstarted; noatomic110
reservation yet09:03:41UTC. Neverrepeat020/creators/bootstrap, retry109 orrestart
019. Nextordinaryfull112 before113; all192/all193/finalaudits/Q1–Q10 incomplete.
Actualruntime004/revision0ff... unchanged; no quality or completion claim.

At2026-10-08 17:01HKT, independentbootstrap93165 TERMINALexit0/owner3725356
absent; receipt47a04d9d...3250e0 verifiesall110preserved attempts/1785actualSDK
requests (802Manager/801BlindVerifier/182specialist), source147/all144ancestor
hashes unchanged, exact15reviewpairs/sole71exclusion/journal04e336a9...eb08a.
Newactual finaladapter rejected incompleteall192/all193 beforeprivatebody/output.
109admitted/110preserved/0pending/0unresolved/1excluded/83unstarted. No020yet;
newlaunch permittedonlyonce fororiginal110 underexactbootstrap/sourcepins,
thenindependentlive-finalguard check. No109retry/privatequalityaggregate or
goalcompletionclaim; nextordinaryfull112 before113, finalall192/all193 due.

At2026-10-08 16:44HKT, authority38560 TERMINALexit0/owner3717258 absent.
Newv2manifest e8bb0da9...bf0a8e/control01221b9695c...c0f/ledger012b02fd8fd...510df;
authorityreceipt185400ce...d2dff0,15 exactreviewpairs. Effective109admitted/
110preserved/0unresolved/0pending/1excluded/83unstarted; journalunchanged.
Independentall110 SDK/source bootstrap93165/3725356/start197609667 submitted
ONCE08:42:46UTC, verifiedlive08:44:40UTC; completionreceiptABSENT, no020.
Neverrepeatold/newcreators, authority orbootstrap. Waitsameowner, thenonlyon
exactbootstrap success permit020/original110. No109retry, qualityaggregate or
goalcompletionclaim; full112 before113/all192/all193 andfinalaudits remain.

At2026-10-08 16:25HKT, actual readonly v2 fullfive-group preflight48054 exited0;
real81header dispatch reproduced. Newexclusive109-002 creator97815 exited0,
owner3712940 absent08:24:37UTC;109sidecar0d4640d1...a0acb7 andcompletionreceipt
58b04c2b...4997c persisted. Originaljournal04e336a9...eb08a unchanged; no109retry,
newmodelcalls or privatequalityaggregation. Authority38560/3717258/start197503190
submittedONCE08:25:02UTC; control012/ledger012/v2manifest completion pending.
No bootstrap/020 yet; finalall192/all193/full112 still required. Oldfailed
creator60298/failurereceipt/all144v1sources remain preserved.

At2026-10-08 16:13HKT, additive v2 source757483d passed fullpytest2854/7existing
skips/315.03s, whole Ruff/project+three-scriptstrictPyright/diff; actual4090Linux
1268/0 across38files/19.73s. Actual147-source pin1f7f4b06...43af1 retains all144
frozenancestor hashes. Freshsource-only namespacecontrol-002/archive189members
f1dc9fdc...27f57; validation receipts local82f9624a...ddeda9/Linux51072465...da1cf.
Independentreview confirms real81header dispatch and unchanged finalguards.
Readonly actualcompletepreflight48054/3710239/start197415627 is live08:13:28UTC
(exactowner/stateR/CPU17958); leafproof passed, fullfive-group proof not yet
claimed. No newcreator/authority/bootstrap/020 or109retry. Counts remain108
admitted/110preserved/1unresolved/0pending/1excluded/83unstarted. Full112 and
all192/all193 plus finalprivate/manual/quality/adoption/Q1–Q10 remain required.

At2026-10-08 15:58HKT, offline109creator60298 exited1 beforeanywrite; ownergone,
109sidecar+completionreceipt absent, strictinactive passes, journalunchanged.
Preservedfailuree7e16776...4682: exactold81header is metadata-bound-derived-record-
field-proof-v1, not newwrapper's assumed phase2-source-propagated header.
Genuineoffline dispatchbug; all144v1sources/validationreceipts preserved, no
experimentretry. Additivev2+actual81header/fullpreflight regressions underway;
no authority/bootstrap/020. Still108admitted/110preserved/1unresolved/0pending/
1excluded/83unstarted. Nextfull112; all192/all193/finalaudits still required.

At2026-10-08 15:52HKT,109offline-only source376bb25 passed fullpytest2768/7,
actual4090Linux1182/0 across35 files, Ruff/project+four-scriptstrictPyright/diff.
Actual144-source pin ed90bbcb...88b9 retains every138ancestor; no execution change.
Readonly109dryproof reproduced1derivedfield+readlimit/collision/context/phase,
6Manager schema wires/4actual selected wires, reviewedcanonicalc65b1178...6494.
Creator60298/3702007/start197298645 launchedONCE07:50:56UTC and independently
verifiedlive07:52:02UTC; sidecar/completionreceipt absent, never repeat.
019 remains terminal/no110started;108admitted/110preserved/1unresolved/0pending/
1excluded/83unstarted, journal04e336a9...eb08a unchanged. No109retry,020/authority/
bootstrap or qualityclaim. Full112 still due; all192/all193 and finalaudits remain.

At2026-10-08 15:13HKT, original108MultiHop6/P2/Fast/A completed at07:07:35UTC:
executioncompleted/evaluatorpresent, originaladmission valid/problems[], allWorkers
verifiedexited; trace96e45470...2d52. Original109MultiHop3/P2/Fast/E completed
with evaluatorpresent but sole raw gate`typed_action_failure_requires_audit:validation_failed`;
019 exited1 at07:11:09UTC, both owned handles absent, no110 reservation.
108admitted/110preserved+settled/0pending/1unresolved/1excluded/83unstarted,
journal04e336a9...eb08a. Narrow failure evidence: specialist BM25 requested
absent`text` on aggregate; additional context90133+2048>32768, read89768>65536,
synthesis guard and output-ID collision retained. Exact source/provenance review
pending; no wildcard waiver, semantic retry, feedback/prompt/runtime change or
quality claim. Nextordinary112 remains pending; finalall192/all193 still required.

At2026-10-08 15:04HKT, same019 owns original108MultiHop6/P2/Fast/A attempt1:
atomic3678180/start197017955 live.107admitted/108settled+1pending=109preserved/
0unresolved/1excluded/84unstarted; journal926f5415...6805 extends frozen107
baselinec942...636f. No108 completion/quality claim, no107retry/018restart,
no runtime/config/prompt/budget/evaluator change. Nextordinary112 pending;
all192/all193 and all finalaudits/quality/Q1–Q10 remainincomplete.

At2026-10-08 15:00HKT, independently gated019 is owned/live: supervisor3676203/
start196998739, controller3676204/start196998742, supervisorSHAa0d2e1d7...0113.
Live receipt854bc771...8648 checks exactargv/startticks and actualnewfinalguard
refusal beforeprivatebody/output. Bootstrap161c...4ee0 pinned; original107 is
not retried,018 remains terminal.019 resumesoriginal108 under sameexecution/
models/prompts/SDK/budget/tasks/scheduler and16-cell cadence, nextfull112.
At startup107admitted/108preserved/0pending/0unresolved/1excluded/85unstarted;
no qualityaggregate/privatebodyaudit or all192/all193 completion claim.

At2026-10-08 14:58HKT, independent new bootstrap13650 closedexit0, ownerabsent,
receipt161c28e4...4ee0: all108 attempts/1759actualSDKrequests(793Manager,
792fixedBlindVerifier,174specialist),138actualsources/all135ancestors retained.
New finaladapter's incomplete guard rejects beforeprivatebody/output. Exact14
source-bound pairs/5maps, native105evaluationNone,107originalcompletion and71
exclusion retained; no qualityaggregate/manualsemantic review.107admitted/
108preserved/0pending/0unresolved/1excluded/85unstarted, journalc942...636f.
No019/original108 launch during readback; gated new019 continuation is now
available. Nextordinary112; all192/all193 and all finalaudits/Q1–Q10 remain.

At2026-10-08 14:41HKT, native-renewed001 authority closedexit0:
manifest16cc82e2...903a/control21b9695c...1c0f/ledger15f1da9c...0ecb,
14 preserved source-bound pairs, all5 original proof groups/no new waiver.
Manifest view107admitted/108preserved/0pending/0unresolved/1excluded/85unstarted,
originaljournalc942...636f unchanged. Independent bootstrap13650/owner3666967/
start196883167 submittedONCE, all108 recipient requests/138actualsources and
originalincomplete-finalguard to be checked. No019/original108 launch yet.
No new model/Worker/tuning/privatebodyaudit/qualityaggregate. Nextordinary112;
all192/all193 and all finalaudits/Q1–Q10/reports still required.

At2026-10-08 14:24HKT,107's exclusive initial-field creator97337 finishedexit0:
new sidecar02ec7481...2808, creatorreceipt71e453cb...d5a0, exact3misuses/9
Manager schema wires, originalcompletion/evaluatorpresence preserved, no retry.
New authority creator87999/owner3658983/start196777726 is submitted ONCE for
control011/ledger011/native-renewed001; no bootstrap/019 launch yet. Existing
native001 still admits106/108preserved/one unresolved until renewal closes;
journalc942...636f unchanged. Nextordinary112; all192/all193 plus final
private/manual/failure/retention/adoption/quality/Q1–Q10 remain incomplete.

At2026-10-08 14:17HKT,107's separate initial-field creator is owned/live
PID3655315/start196732934, exclusive session97337; do not resubmit. No durable
107 sidecar or renewed authority/019 queue exists yet.018 remains terminal,
106admitted/108preserved/oneunresolved/no pending; journalc942...636f unchanged.
Offline-only implementationb4e45c5 passed fullpytest2530/7 existing skips,
focused216, actual4090Linux944/0skip, Ruff/strictPyright/diff. Actual138-source
closure retains every135ancestor hash; no measuredexecution or semantic change.
Proof creation is not a new model/experiment run or retry. Nextordinary112.
All192/all193 and finalprivate/manual/adoption/retention/quality/Q1–Q10 remain.

At2026-10-08 13:51HKT,018 is terminal(exit1 at05:45:19.840039UTC), with no108
reservation. Original107MultiHop6/P1/Slow/B1 **completed and invoked evaluator**,
but three initial-shard BM25 `text` requests instead of declared `body` triggered
the conservative typed-validation gate. Frozen pure field proof passes3misuses/
9actualManager SDK schema wires with unchanged operator sources. No outage or
method/API audit problem; no retry/tuning/new model call.106admitted/108preserved/
0pending/1unresolved/1excluded/85unstarted, journalc9429559...636f. Separate
offline same-five-group renewal integration is in progress; no107sidecar/new
authority/bootstrap/019launch yet. Nextordinary112; original192/all193 and all
final private/manual/retention/adoption/quality/Q1–Q10/report requirements remain.
See [cell107 audit](large-scale-resident-phase2-cell0107-initial-field-audit-v1.md).

At2026-10-08 13:44HKT, original106MultiHop6/P2/Slow/B0 naturally settledvalid
at05:39:24.843344UTC, executioncompleted and original evaluator invoked; Worker
shutdown verified. Admissionfilecde6fe9c...6429/canonicalreceiptd469f363...b676;
no correctness claim. Same018ownedlive, original107MultiHop6/P1/Slow/B1 attempt1
atomic3638660/start196514571 live; trace761225bytes/260headers, lastactionstart
05:42:47.151029Z.106admitted/107settled+1pending=108preserved/0unresolved/
1excluded/85unstarted; journale57588ea...0085. Nextordinary112 pending; no
retry/tuning/privatebodyaudit/qualityaggregate. Original192/all193 plus all
finalprivate/manual/terminal/failure/retention/adoption/quality/Q1–Q10 remain.

At2026-10-08 13:37HKT, independently gated new018 is live: supervisor3633931/
start196483150, controller3633932/start196483152, supervisorSHA80fd098c...b160.
Live receipt5b39773a...61ca checks exact argv/startticks and actual new final
guard refusal beforeprivatebody/output. Original106MultiHop6/P2/Slow/B0 attempt1
atomic3635073/start196494959 is live.105admitted/106settled+1pending=107preserved,
0unresolved/1excluded/86unstarted; journal920e4cb0...51a8 extends original105's
03aec...8828c prefix. No105retry/017restart or measuredexecution/configchange;
nextordinary112. Original192/all193 and all finalprivate/manual/failure/
retention/adoption/quality/Q1–Q10/report obligations remain incomplete.
See [cell105 audit](large-scale-resident-phase2-cell0105-native-json-audit-v1.md).

Independent native001 bootstrap completed exit0; receipt SHA256
`c1fd724845148d6a9fb4cf45e11c648f071dbde69c6d95421247bdd986ce383f`.
105admitted nominal/106preserved/0pending/0unresolved/1excluded/87unstarted;
all106traces and1727actualSDKrequest hashes verified (777Manager/776fixed Blind
Verifier/174specialist).135actualsources/all132historical hashes match.
193profile/400ledger/205rules rootmatches establish visibility only, not adoption.
Actual new final adapter refuses incomplete all192/all193 inventory before
private body/output. No quality aggregate/manual body audit. Original105's
semantic failure and missing evaluation are preserved; a fresh018 may now
resume original106, not retry105 or restart017. Nextordinary112; all remaining
original192/all193 plus finalprivate/manual/failure/retention/adoption/quality/
Q1–Q10/report requirements remain incomplete. See [cell105 audit](large-scale-resident-phase2-cell0105-native-json-audit-v1.md).

At2026-10-08 13:17HKT, native001 authority completed exit0, SHA256
`b3c48708b7595812dcac624dbfc82942bc6b7bf5cc17bcf581aa674e506ff96d`.
All13 historical raw/effective pairs, original71 exclusion/replacement, all five
proof groups, execution004 and schedule are preserved. Creator verifies
105admitted/106preserved/0pending/0unresolved/1excluded; admitted includes valid
semantic failures, not105execution successes. Original105 remains completionfalse
and evaluationnull, rawjournal03aec...8828c unchanged. Independent bootstrap1887/
PID3626140/start196379922 is live and must check all106actual recipient contexts,
135actual sources/all132ancestors and actual incomplete-final guard. No106
dispatch/018launch yet. Nextordinary112; original192/all193 and all final
private/manual/retention/adoption/quality/Q1–Q10/report obligations are incomplete.
See [cell105 audit](large-scale-resident-phase2-cell0105-native-json-audit-v1.md).

At2026-10-08 13:06HKT, original105's exclusive source-bound native JSON
sidecar creator has completed exit0; sidecar SHA256
`da3d543320a59237e029d8921559b4b4c0c62ff808463312edf382004a1750cc`.
Measured execution and raw journal are unchanged; its failure completionfalse/
evaluationnull are preserved, no retry or new model call. New native001
authority creator12553/PID3620915/start196309434 is live; no106reservation,
bootstrap or018 launch yet. Offline sourcefreeze05aafae passes2423fulltests/
7existingWindows skips,109newtests,837actualLinux tests withoutskip, Ruff and
strictPyright. Actual135-source closure retainsall132old hashes, pine978...ad4c8.
Current dispatch authority still104effective/106preserved/1unresolved until the
new full five-group authority and independent bootstrap succeed. Nextordinary112;
original192/all193 and final private/manual/quality/Q1–Q10 remain incomplete.
See [cell105 audit](large-scale-resident-phase2-cell0105-native-json-audit-v1.md).

At2026-10-08 12:48HKT, controller017 is terminal(exit1), all of its owned
process handles are absent and journal03aec69d...8828c is unchanged. Original105
MultiHop6/P1/Fast/E failed when the Manager generated syntactically invalid
consult_specialist JSON. The frozen pure SDK reviewer reproduces this exact
failure with unchanged native/SDK sources and strict schema; classification is
workflow composition, not provider outage. Completionfalse/evaluationnull are
preserved. No105retry/replacement and no106reservation. Current authority:
104effective/106preserved/0pending/1unresolved/1excluded/87unstarted.
Separate five-group offline audit integration is in progress; no new authority
or resumed queue is yet claimed. Nextordinary112; no private/manual body audit
or partial quality aggregate. Original192/all193 and all final requirements
remain incomplete. See [cell105 audit](large-scale-resident-phase2-cell0105-native-json-audit-v1.md).

At2026-10-08 05:28HKT, original104MultiHop5/P1/Fast/A attempt1 naturally
settled valid at21:26:14.686412UTC; execution_completed=true and Worker shutdown
verified. Original admission file SHA256
`c707e0085f568d2720c1038255b8c7a9a05f3943bc9da29e5cbccc15edb42c80`;
canonical journal receipt
`79cd4461ce50937db84c402526d13cb5aa5160711848555da274c286cdd82a16`.
Long physical-action waiting was not treated as a crash or replacement. The
metadata monitor initially looked for action.succeeded; corrected to include
the actual action.completed event, without altering measured execution or trace.
Completion receipts are not semantic success/quality claims.
Same017 now owns original105MultiHop6/P1/Fast/E attempt1 atomic3440677/start
193551940; at21:28:11UTC trace638152bytes/220headers and fresh reasoning-start
receipt.104eligible/105settled+1pending=106preserved,0unresolved/1excluded,
87unstarted; journalaabf6672...dc8681. Next ordinary full112; no retry,
replacement, tuning or new authority. Original192/all193 plus final private/
manual/retention/adoption/quality/Q1–Q10/report scope remains incomplete.

At2026-10-08 05:12HKT, independent filtered001 bootstrap completed exit0;
receipt `ab6c9b92003f3fd4601be93553c5c55a9d3ebb759d7d1787f4d3167248334f58`
verifies103eligible/104preserved/all104traces and1,680actual SDK requests
(753Manager/753fixed Blind Verifier/174specialist),132actual imported sources
and127unchanged ancestors. Actual incomplete final guard rejects before private
body/output. New017 supervisor3430507/start193456665 and controller3430508/start
193456667 are independently owned/live; live receipt7c0ca263...9d8b1 proves
the unchanged strict-inactivity guard also rejects during execution.
Original104MultiHop5/P1/Fast/A attempt1 atomic3430989/start193461914 is now live:
103eligible/104settled+1pending=105preserved,0unresolved/1excluded,88unstarted.
Next ordinary full112; no103retry/old016restart, measured execution004/0ff0e9b,
schedule and all semantic/physical comparison contracts remain unchanged.
Original192/all193 and final private/manual/terminal/failure/retention/adoption/
quality/Planner/workload/Q1–Q10 obligations remain incomplete. No partial quality
aggregate. See [cell103 continuation audit](large-scale-resident-phase2-cell0103-filtered-field-audit-v1.md).

At2026-10-08 04:59HKT, original103's source-bound filtered-field sidecar is
closed and new filtered-environment001 authority creator exited0. Manifest
SHA256 `e1f11c2c1d03d7793d31784a026c848aba77bec887aed81887009e7a4e5d0d58`
adds only103's filtered proof, preserving all previous review groups and the
sole original71 exclusion/replacement. Creator reproduces103eligible/
104preserved/0pending/0unresolved/1excluded; journalb122...d138 is unchanged.
Independent bootstrap71270/3424856/start193383987 is live, not yet passed;
104dispatch remains unstarted. No103retry, tuning, new benchmark call or final
private/manual audit. Next ordinary112; original192/all193 and all final
quality/retention/adoption/Planner/workload/Q1–Q10/report obligations remain.
See [cell103 audit](large-scale-resident-phase2-cell0103-filtered-field-audit-v1.md).

At2026-10-08 03:13HKT, normal full96checkpoint completed, SHA256
`fa35c7e7836ae299e9a8c60af277b84aea38b9be75d592ba71292e00f09b4c3c`.
Independent readback59d595e91ac02a18f0efe1701255a52bbd52188c579d0d06adda641a09d4d2ef
verifies96effective/97preserved/0pending/0unresolved/1excluded at the checkpoint,
all97trace hashes and1,572actual SDK requests(710Manager/710Verifier/152specialist).
The exact journal prefix through96 is preserved and97reservation is after the
checkpoint. Same016ownedlive; new97Video6/P1/Fast/E attempt1atomic3364465/start
192737040 running:96effective/97settled+1pending=98preserved,95unstarted.
Next ordinary full112, immediate newfinding stop remains unchanged. No retry,
tuning, private semantic body scan or partial quality aggregate. See
[checkpoint96 audit](large-scale-resident-phase2-checkpoint0096-v1.md).
Original192/all193 and all final audit/report requirements remain incomplete.

At2026-10-08 03:01HKT, new016supervisor3357525/start192673770 and controller
3357526/start192673771 are independently owned/live. Original new96MultiHop5/
P2/Fast/B0 attempt1atomic3357918/start192677949 is actually running;95effective/
96settled+1pending=97preserved,0unresolved/1excluded,96genuinely unstarted.
Live receipt SHA256 `f82fb1c30b310d2c36ded963c7566722d60821646e24b39e0f519112cb6ccebf`
pins supervisor/current003authority/bootstrap003 and actual commands/start ticks.
The actual final private guard rejects with `private body audit requires inactive
queue and atomic actions` before private body/output. No95retry/old015restart;
measured execution004/0ff0e9b remains unchanged. Full96checkpoint is still pending
and gates97. Original192/all193 and final private/manual/terminal/failure/
retention/adoption/quality/Q1–Q10 reports remain required and incomplete.

At2026-10-08 02:58HKT, independent bootstrap003 completed exit0, receipt SHA256
`fc9649b581fb31926c0dc2a227c0a2db36925ae8ca272cdbc424380a7678c078`.
Full current control/all96traces and1,560actual request hashes pass,95effective/
96preserved/0pending/0unresolved/1excluded. Recipients:704Manager/704fixed Blind
Verifier/152specialist; exact feedback matches358ledger/177rules/179profile are
visibility evidence, not causal adoption. Original127-source final pin8f1c...da7
is unchanged; actual incomplete-final probe rejects before private body/output.
Manifest003bfa91c54...dcc55 and journal5e793191...fc36a match. Next separate action
is016/new96, not a95retry or old015restart.97unstarted; all original192/all193,
normal96 and final private/manual/terminal/failure/retention/adoption/quality/
Q1–Q10 requirements remain incomplete. No aggregate quality claims.

At2026-10-08 02:48HKT, renewal003 completed exit0. Manifest SHA256
`bfa91c544184fbaa473b0b0251ce3fc49931676b064e545b00e91f5a159dcc55` binds the
exact sole new95field proof and all preserved ancestor authorities. Its original
full proof revalidates95effective/96preserved/0pending/0unresolved/1excluded,
97genuinely unstarted. Independent bootstrap003/session63751 is now running;
016dispatch/new96 remain unstarted until it passes. Journal5e793191...fc36a and
measured execution004/0ff0e9b unchanged; no95retry, tuning or newbenchmark call.
Next ordinary full checkpoint96 and original192/all193 final scope unchanged.

At2026-10-08 02:39HKT, corrected offline creator38093 is terminal exit0;
original95sidecar SHA25cd189659e77ab0e8e0c0392cb1817c2d9de18670c4b2e8309104a63f4a59a8
is preserved and journal5e793191...fc36a is unchanged. The first003invocation
rejected a wrong ledger filename prefix before authority writes. Corrected
003renewal session84408/PID3347179/start192533324 is actually CPU-live and doing
the existing full proof;manifest still absent at18:39:03UTC. No96reservation,
95retry or newbenchmark call. Independent bootstrap003/016launch remain pending;
95effective/96preserved is the required reviewed closure, not yet an independently
verified current dispatch authority. Original192/all193/normal96/full final
private/manual/terminal/failure/retention/adoption/quality/Q1–Q10 scope unchanged.

At2026-10-08 02:28HKT, legacy sidecar creator79253is actually terminal(exit1),
not live; it failed journal replay before writing because it omitted the pinned
environment71exclusion(first reject sequence143), with derived81also unsupported.
Separate offline creator-only repairc29f3c6 passes final2118pytest+7skips/Ruff/
strictPyright/diff and88actualLinux tests. Corrected creator38093/PID3343216/
start192474679 is actually owned/live/CPU-active; sidecar still absent. No new
benchmark run/retry/source or config change in the measured frozen execution.
94effective/96settled/0pending/1unresolved/1excluded/97unstarted;003renewal/
bootstrap003/016dispatch and normal96cadence remain pending. See
`large-scale-resident-phase2-field-creator-compatibility-v1.md`. All original
192/all193strict-inactive final audit/analysis requirements remain unfinished.

At2026-10-08 01:50HKT, original95has settled and controller015has stopped through
the required finding gate(returncode1). Original95runner exited0/completed/
formatvalid/evaluator1; raw finding is typed `validation_failed`, not a new
operational failure.94effective/96settled preserved/0pending/1unresolved/
1excluded,97genuinely unstarted. Journal SHA256
`5e79319170a95c674e687a4865100668458676b8d26acd57c3c36bd85a9fc36a`.
Existing initial-field dry proof passes3exact text-vs-body misuses and9actual
Manager schema wires. Companion metadata/source proof identifies3same-run
reserved-output-ID guards/9phase guards/2static conservative context rejects;
no cross-run store pollution or dynamic unavailability is inferred. The sole
exclusive sidecar creator79253/PID3319020/start192189884 is actually live and
not yet completed. No completed003renewal/bootstrap/016launch or96reservation
is asserted. No95retry, tuning, source change, auditmodel call, new private body
scan or partial quality aggregate. Fullpytest2101passed/7skips plus Ruff,
strictPyright/diff and71actualLinux regressions pass. See
`large-scale-resident-phase2-cell0095-initial-field-audit-v1.md`. Next normal
full96and original192/all193 strict-inactive final scope remain mandatory.

At2026-10-08 01:27HKT, source-bound lightweight process/journal observations
confirm93and94naturally settled/admitted:94effective/95settled preserved+
1pending=96attempts,0unresolved/1excluded,97unstarted. Same015controller
3285126/start191884991 and supervisor3285125/start191884988 remain owned/live;
new95MultiHop5/P1/Slow/E attempt1atomic3310839/start192101071 is running.
Journal SHA2562a00dcb3cbc4b5f9d3c0ee373238ceb1ec8363f221f9e67bdd1b90d4be71d53e.
93's longer wait was confirmed against its actual PID/start ticks and trace
file growth; no observation timeout was treated as a crash or restart. Only
event-header metadata was extracted, never prompt/answer bodies or private
evaluation/store content. The existing checkpoint callback remains compatible;
actual96receipt is still pending. No retry, source/prompt/budget/model/tool/
scheduler/evaluator change, per-cell full audit or partial quality aggregate.
All192/all193 strict-inactive final requirements remain mandatory/unproven.

At2026-10-08 01:05HKT, lightweight journal/PID/start-tick checks confirm91and92
settled/admitted without a new finding.92effective/93settled preserved+1pending=
94attempts,0unresolved/1excluded,99unstarted. Same015controller3285126/start
191884991 and supervisor3285125/start191884988 are owned/live; new93MultiHop5/
P1/Fast/B1 attempt1atomic3297209/start191962104 is actually running. Journal
SHA256c948f5fd567ee9b3f669b8a7b380392bc58a21c51226db4fa830ab5450124968.
An earlier observation of91's disappearing PID was reconciled against its actual
settlement and next92reservation, not treated as a crash or restart condition.
No per-cell full audit, private body read, partial quality aggregate, retry,
source/configuration/prompt/model/tool/budget/scheduler/evaluator change. Next
ordinary full96remains pending; all192/all193 final requirements unchanged.

At2026-10-08 00:53HKT, lightweight process/journal observation confirms90has
settled/admitted without a new finding.90effective/91settled preserved+1pending=
92attempts,0unresolved/1excluded. Same015controller/supervisor remain owned/live;
new91MultiHop3/P1/Slow/B1 attempt1atomic3289206/start191909895 is running.
Journal SHA25637649184f7b3ccf44d02f4344943f59ea684efe6974807ee8b007d3a32e40c12.
This is membership/verified wait, not per-cell full audit or partial quality
analysis. Next full96; original all192/all193 final scope unchanged.

At2026-10-08 00:50HKT, new015is actually owned/live, supervisor3285125/start
191884988 and controller3285126/start191884991. New90MultiHop3/P2/Slow/B0
attempt1atomic3285496/start191888412 is running:89effective/90settled+1pending=
91preserved,0unresolved/1excluded,102unstarted. Live receipt
`c74cad0a14d2ef3012f74830f92cbcd2efd63883fe9d9f420aead60a664d1e9b`
verifies current commands/source authority and actual live private-body rejection
before any final body/output. Measured execution004/0ff0e9b unchanged, no89retry
or014restart. Next full96; all original192/all193 final requirements remain.

At2026-10-08 00:46HKT, independent bootstrap002 completed successfully. Receipt
`2b1bf9c70190c7cfbc9cebdea2182fe799a3de950d1c231f1028a21ada3de0be`
revalidates full control/all90attempts,89effective/0pending/0unresolved/1excluded,
all90trace hashes and1,423actualSDKrequest hashes (643Manager/643Verifier/
137specialist). Current127-source final pin8f1c06eacda747f11c0747f9b3fa91a653da05f9dee442c8440fc8cf6ba41da7
is unchanged; actual incomplete-final guard rejects before body/output. Renewed002
is the current continuation authority, not old001/014. No89replacement;015not yet
launched at this closure. Original192/next96/all193 final scope stays unchanged.

Current renewed002 manifest creation completed exit0, SHA256
`5ec4215dea4573aba1c768de10a65712fc7eb1010f952abdb811d21230747439`.
Independent bootstrap002 is running (owned PID3278905/start191805566,
exec69006), revalidating full control,89effective/90preserved attempts and all
actual recipient wires. Its final receipt is not yet available;015not launched,
no90reservation/no89retry. This is progress plus a verified wait, not an approval
to bypass the old001 inventory fence. Next ordinary full checkpoint remains96.
Frozen execution004/0ff0e9b and all original final-audit requirements unchanged.

Current2026-10-08 00:18HKT:014actually stopped exit1 at16:08:13Z on new89
MultiHop3/P1/Fast/E initial-field gate.88effective/90settled preserved/0pending/
1new unresolved in old001view,1excluded,103unstarted; no90reservation/retry.
Original89completed/formatvalid/score1, all Workers exited/residency passed.
Unchanged initial reviewer proves3root text/body mistakes and9actualschema wires;
sidecarc3886c35b8ab76d36f59e5b80634928567bd6aa25cdb90c2b27d89f66139327e
preserves all raw evidence. Separate contextreject116746conservativeinput+
2048>32768 is notactualtoken count/dynamicunavailability/inference. Natural
continuation ends in3successful inferences and originalscore1, no semantic tuning.
Sameb3d83cfcode fullpytest/Ruff/strictPyright passed,42actualLinuxpass; append-only
renewal002creator running, independent readback stillneeded before015/new90.
See [narrow source-bound89audit](large-scale-resident-phase2-cell0089-initial-field-audit-v1.md).

Current2026-10-08 00:06HKT (16:06:12UTC): same014controller3247654/start
191509875 and supervisor3247653/start191509873 independently verified live.
87/88have naturally settled/admitted;88effective/89settled preserved+1pending=
90total attempts,0unresolved,1excluded,103unstarted. New89MultiHop3/P1/Fast/E
attempt1atomic3262458/start191600276 is actually live, no controller exit.
Admitted-cell counts are membership, not normal execution/correctness counts.
No restart/retry/new code/configuration or partial quality aggregate; latest
normal full boundary remains80, latest bootstrap84, next normal full96 still
absent. Full original192/all193 strict-inactive/manual/semantic/failure/retention/
terminal/adoption/quality-conditioned/Q1–Q10 and named reports remain required.

Current2026-10-07 23:56HKT: same014controller3247654/start191509875 and
supervisor3247653/start191509873 remain independently verified live.85and86
have naturally settled/admitted;86effective/87settled preserved+1pending=
88total attempts,0unresolved,1excluded,105unstarted. New87LongBench3/P1/Slow/E
attempt1atomic3255826/start191566782 is actually live. No restart/replacement/
configuration change; next normal full96receipt still absent. This is lightweight
process/journal observation, not another per-cell full audit or partial quality
aggregate. Current full-wire authority remains the84bootstrap; original192/
all193final private/manual/failure/retention/quality/Q1–Q10reports still required.

Current2026-10-07 23:49HKT: new014owned/live, controller3247654/start191509875,
supervisor3247653/start191509873. New85LongBench3/DeepSeek/Fast/B1 attempt1
atomic3247897/start191512794 is actually running.84effective,85settled preserved
+1pending=86attempts,0unresolved,1excluded,107unstarted. Live receipt
39dd3647d31c4b73cd82510e3c02b813d34e68db1d94360306f13f71f26e1e62
binds correct command/source/manifest; actual private guard rejects live queue
before scans, no probe output. cf49105audit closes84 withoutretry; b3d83cfcode
is external audit-only. Next full96notyetpresent; all192/all193finalanalysis
remainsrequired, no quality/method aggregate or semantic primarycause claim.

Update2026-10-07 23:45HKT: independent renewal closure passes84effective/
85preserved/0pending/0unresolved/1excluded. All85traces/1299actual requests
(597Manager/597fixedBlindVerifier/105specialist) verify; immutable bootstrap
SHA3be3514fecc3df07ea0c803d90d5a53f7ad7d0d466fa1b2e8477c08bb11238a5.
New127-file actual finalsource pin8f1c06eacda747f11c0747f9b3fa91a653da05f9dee442c8440fc8cf6ba41da7
preserves all125oldhashes/paths and original scanner/guard. Actual incomplete
all192/all193guard rejects beforebody; no probe output.014may now dispatch only
unstarted85onward; no84retry, original71onlyreplacement unchanged. No formal
newcell launched at this closure capture; nextfull96. Wholefinal analysis pending.

Update2026-10-07 23:35HKT: audit-only renewal commitb3d83cf validated with
2101pytest/7existing skips,42actual4090Linux tests,Ruff/strictPyright/diff pass.
Newmanifest001created once SHA171614c2b392d2449a4d28aa654c207cb2de6e993150684c06cf3dd4b215e90f,
control006/ledger006 created via unchanged original helpers. Independent full
bootstrap and current final-source pin/negative guard are running, queue still
stopped; no85reservation. Sole71replacement/derived81/initial84proofs retained,
no new replacement/semantic tuning/frozen execution change. This supersedes the
earlier claim that full tests or renewal creation remain pending, not the need
for complete192execution/all193final audit.

Current2026-10-07 23:21HKT:013stopped exit1 at15:04:01Z on cell84
MultiHop4/DeepSeek/Fast/B0.83effective/85preserved/0pending/1new unresolved
in oldmanifest view;108unstarted, no85dispatch/retry. Actual84 completed,
formatvalid,originalscore1; narrow unchanged reviewer proves3initial root
text-vs-body field mistakes, then natural legal continuation. Newsidecar
dbc052295c6dcfdb0220106053dea747537332ae5699819717a003ce95eb3f0d
does not edit original admission/result/trace/journal. Fullrenewal/finalreader
validation pending; old exactinventory manifest mustnot be reused as current.
No runtime/prompt/tool/budget/model/scheduler/evaluator change or privatebody
decode. Nextnormal96 onlyafter new current gate; all192/all193finalaudits remain.
See [actual finding and preserved recovery](large-scale-resident-phase2-cell0084-initial-field-audit-v1.md).

Current2026-10-07 22:48HKT: new013 actually owned/live,81effective settled/
83preserved/1pending/110unstarted. New82 MultiHop4/DeepSeek/Slow/A attempt1.
Original81 metadata-only derived-field proof passed, completed/formatvalid/score0
preserved and admitted without retry; synthesis/context companions remain separate
non-inference observations. No semantic primary-cause or benefit claim yet.
Bootstrap e4d0f472920793cfb3caba701b34ba6cf8119db244746213f1e23c2c444d63cd
reproduces82traces/1249actualSDKrequests. New manifest82456d1e79d90e7d7a2952b73fa7c8899945cf28c2afc791a849f66da25383cc.
New125-source final adapter preparation pins original scanner; partial/live guards
actually reject before body scans.2059fullpass/7skip,164Linux,Ruff/strictPyright.
Execution004 unchanged; next full96then112/...192 and immediate new-finding stops.
All192/all193 final private/manual/retention/failure/Q1–Q10 still pending.

Current2026-10-07 22:12HKT: full80audit independently closed, then012stopped
13:53:17Z on cell81 MultiHop4/Qwen/Fast/E validation_failed.80effective/
82preserved/0pending/1unresolved/111unstarted; no82reservation. Original81
completed,formatvalid,score0; specialist derived-record absent text proof pending.
Keep raw results/journal unchanged; no retry or semantic tuning. Full80receipt
ccebd85ce73a0702b6fa23cf57dd9263e989d48ea0e2a69d224d2c1f8c9b49f5,
independent90472f47410b66cbdd427eb1038621cc4334205bba5ef0a7ed69fc5a3c61be65
binds81traces/1229actualSDKrequests. Do not apply the old root-initial-only field
review to specialist-derived artifacts. All192/final private/manual audits pending.

Current2026-10-07 21:49HKT:80admitted/81preserved/0pending under actual live012;
full80cadence target not yet present at13:48:55Z, no controller exit. Distinguish
settlement from independent full audit closure. Original71excluded, sole identical
replacement valid; do not retry it or any existing valid cell. Separate final
offline bundle c30d903 validated/frozen, source inventory121files,1895fulltests/
29Linux tests/Ruff/strictPyright pass, original live guard actually rejects body
scan. This does not alter any measured cell or prove semantic completion.
All192+193-attempt final inactive private/manual/recipient/adoption/retention/
failure/Q1–Q10 and final named reports remain incomplete; no quality aggregate.

Current2026-10-07 21:31HKT:012owned/live,74admitted76preserved1pending117unstarted;
original71remains environmental-excluded, one authorized identical replacement
settled13:23:03Z with valid format/score1/residency/tc/Worker shutdown. Metadata
receipt d5765a9155234bdb0490d0acd92557ae4ca1b0c41433e2f207073b88f25c63ce.
Full bootstrap002 independently covers all71original traces/1097actual requests;
this is not a final audit of later cells. Next full80then96/...192; new findings
stop. Measured execution004 unchanged. All192+193-attempt final strict-inactive
private/manual/recipient/adoption/failure/retention/Q1–Q10 remain required.
Independent final-path review found report-only joins/persistence/source-binding
gaps; separate offline bundle preparation does not tune methods or live execution.
No aggregate accuracy, causal adoption or method winner claim.

Current2026-10-07 19:43HKT:010terminalexit1at11:36:16Z;70admitted settled/
71preserved/0pending/121unstarted,8original findings/1unresolved. New71Video5/
DeepSeek/Slow/E completed/format valid/score1but external GPU1Strata process
changed; residency failed, validation receipt absent, raw admission remains
confounder/FileNotFoundError. Original base admission independently passes,
not full residency admission. No72/replacement/restart; do not aggregate this
score as valid. See cell0071contention audit. Full64proof retained, next80not
created; all192and final strict-inactive private/manual/adoption audits remain.

Current2026-10-07 19:24HKT:67effective settled68preserved1pending124unstarted;
same010owned/live, new68LongBench5/Qwen/Fast/A attempt1atomic3092386,
result absent at11:24:41Z. Seven originals retained, zero effective confounders.
Full003-cell0064automatic audit independently closed at11:16:41Z:64traces/
982actual provider requests,458Manager/458Verifier/66specialist;114profile/
224ledger/108rule matches, exact journal/source/control bindings and original
recipient isolation/shutdown checks pass. ReceiptSHA
a9d3745c9c18c1abc1eff1468cf4b74a1c30500e0aaf4aecda0b7ccaa997fe49.
Closed audit scope64does not include later65–67; next full80. No private-body
audit or quality aggregation; visibility does not prove method adoption/benefit.
All192and strict-inactive private/manual/recipient/failure/adoption/Q1-Q10remain.

Current2026-10-07 19:02HKT:60effective settled61preserved1pending131unstarted;
seven original findings retained, zero unresolved effective confounders.
Control005/ledger005/manifest003 independently frozen/verified;010controller
3068687and new61LongBench6/Qwen/Fast/E attempt1atomic3068821owned/live
at11:01:56Z, result absent. Manifest
aea2755c4736143018459f66e6f79f6ce1f2bee6013931030608a30e35d1554a;
next automatic003-cell0064then80...192, immediate new-finding stop unchanged.
Original private guard rejects live010, body reads0. No retry or009restart,
production module/prompt/model/budget/scheduler/task/evaluator change or quality
aggregation. See cadence/field audit for exact evidence and unchanged-code tests.
All192execution and strict-inactive private/manual/adoption/Q1-Q10remain.

Cell60exact original proof now independently closed at10:45:21Z: three root
field misuses/seven actual SDK schemas/86evidence bindings, journal unchanged,
no retry. Sidecar4dde7767e8987eb7919e931d80fb2652ccbe74d0753ba5f1c0ba424fbb1f504f;
original completion/format/score0retained, semantic cause not inferred.
New005control/ledger creator46508running once;003manifest/010not created.
Current002view59effective60preserved0pending; no61dispatch. Production sources
unchanged; five test-only guards pass, full1843pass/7platformskip, actual Linux22
pass, Ruff/strictPyright/diff-check pass. See field audit for exact provenance.
All192and final private/manual/adoption/Q1-Q10remain required; no aggregate claim.

Current2026-10-07 18:41HKT:59effective60preserved0pending132unstarted;
seven raw findings/one unresolved effective confounder.009exited1 at10:36:27Z
after cell60MultiHop6/DeepSeek/Fast/A field gate; no61/retry/replacement.
Original result completed/format-valid/score0, but not yet admitted. Three
root BM25 requests used undeclared `text`; actual schema declares `body`.
Exact original proof creator85079owned/live, no new private bodies. See field
audit for immutable admission and isolated original-body/flat-bookkeeping
provenance. No control005/manifest003/010launch yet.64full checkpoint remains
pending; no pooled quality or cause attribution before all192private audits.

Current2026-10-07 18:28HKT:58effective settled/59preserved/1pending/133unstarted;
zero effective confounders, six raw findings retained. Cell58exact original
field proof, new004control/ledger and002cadence manifest independently verified.
New009controller3049930and cell59MultiHop6/Qwen/Slow/E attempt1atomic3050035
owned/live10:28:26Z, result absent. No retry/replacement or008restart. Manifest
6093f0311108cda588ea66356859fc558f27580ae938c3cccdb915a177159099;
next full checkpoint002-cell0064then80...192, immediate exception stops remain.
Original private guard rejects live009, body reads0. See cadence/field audit
for all evidence hashes. No execution/prompt/model/budget/scheduler/evaluator
change; no new quality aggregate, private semantic audit or final winner claim.

2026-10-07 18:17HKT: cell58exact original field proof is now independently
closed (three root misuses,16actual Manager requests,158evidence bindings).
Sidecar364db53bb08a9e8729a1411e49957180352f25278de69660fcacc814d5aaac65;
reviewed admission527eefa469da3936328463dc2e177a1e63239434b44500b06b0deeac873dfc00.
No raw/result/journal rewrite or retry; source-bound historical shape reuse,
zero new corpus/store-body decode. Original completion/format/score1retained.
008remains stopped; new004control/ledger creator62037owned/live10:20:36Z,
targets absent,002manifest and009launch not yet created. Old001view still57
effective/58preserved; do not claim58frozen/59running before independent
continuation verification. Normal full checkpoint64then80...192; new findings
still stop immediately. All192and final private/manual/adoption audits remain.

2026-10-07 18:00HKT exception stop:57effective cells/58preserved/0pending;
008exited1 at09:50:53Z, no59dispatch. Cell58MultiHop6/DeepSeek/Slow/B0 original
result completed/formatvalid/score1, but raw admission is a preserved field
validation finding. Three BM25 requests used `text` instead of the declared
`body`; exact unchanged field proof is running once, not yet admitted or waived.
Six raw findings/one unresolved effective confounder; no retry/replacement.
16cell cadence remains; new findings still stop immediately. No new corpus/store
body decode, no all192private audit or quality aggregation. See
large-scale-resident-phase2-field-review-v1.md. Do not restart008or repeat creator97236.

2026-10-07 17:12HKT protocol update: user requests full audit every16cells.
50effective settled/51preserved/1pending/141unstarted at independent09:08:59Z;
cell51Video6/Qwen/Slow/E runs on new008controller, not a repeat. Safe cutover
after50with no live atomic/pending; old007exit-2 is deliberate controller
shutdown, not a benchmark failure/exclusion. Original per-cell execution,
admission/recipient scan/fresh stores/tc cleanup/exception stops unchanged.
Next full checkpoint64, then80...192, including a final short remainder.
Manifest19d8b26b93b96e92c8bbdee155f70c9f0d1b903b17bd16e9a9af0c8d7ebf92e0;
008receipt9946be735662f0edf7342b661df58eb5cb8a1e8a294e414e27023001374517bc.
Detailed source/tests/guard/cadence audit in large-scale-resident-phase2-audit-cadence-v1.md.
045/041remain49scope; do not repeat per-cell full snapshots. All192strict-inactive
private/manual/failure/adoption/quality-conditioned final analyses incomplete.

Checkpoint2026-10-07 16:28HKT: snapshot045/feedback041 independently reproduced
08:27:00Z, all49trace/794actual provider-request hashes and population/journal/
control003 bindings, unchanged Phase I journal. SHA
a6db7f7b451d5f4a86d492bebe3b57a589cfd6a4c5a55ae4a33e04943b350ddf /
b956f5691b59efe8b353ae321ff3150b2dc31c567f2d01110aa2faaf2aa28d6b.
364Manager364Verifier66specialist/96profiles179ledgers87rules match;
fixed Verifier/recipient isolation pass.49effective49preserved0pending;
143remaining, same007continues. Next50unreserved08:26:38Z. Read-only recollection
54902 succeeded after74836 failed before writing on journal advance; no
benchmark/Planner retry/replacement. No score pooling/causal-adoption claim;
full192private/manual/failure/adoption/quality-conditioned analyses incomplete.

## Cell49 settled: valid raw-profile completion, original score1

2026-10-07 16:17HKT. Video6/Qwen/Fast/B1 attempt1 completed with original
admission/terminal format valid,score1; no retry/replacement/semantic tuning.
AuditSHA `0e04b9a19d7175d3f09de7c2536e51988fd7a1721a3db8afcb30875c2b17adb7`
independently reproduced08:15:09Z, all bound files/startup/terminal/original
admission/settlement/tc/shutdown/10SDK contexts. Four empty initial stores and
five stable resident identities verified. Raw model text equals canonical answer
and frozen deterministic projection; no additional LLM finalization.

| Recorded component | Cell49 |
| --- | --- |
| Manager / Verifier / specialist turns |5 /5 /0; no specialists created |
| Physical calls / model requests / successful inference receipts |3 /2 /1 |
| Typed observations |1context reject before inference;1semantic validation;1phase restriction |
| E2E |115.454779673s |
| Initial materialization, separate from Agent movement |233097342bytes /20.347444665s |
| Complete registered Agent movement |0bytes /0s; not all HTTP/RPC/prompt traffic |
| Complete tool work |17.297508302s |
| Inclusive successful Worker model-action work |19.033965704s; includes backend |
| Complete backend service / tokens / finish |18.910888825s /3394input,2output /stop |
| Frozen-list-price cloud API USD |0.193638744867723461645783228583956736071422; not invoice |
| Execution-grown graph |3action nodes /11artifact-flow edges /10snapshots /peak1action |

Sequence:sample_frames -> context-rejected model -> successful A4VL4B terminal
consuming3artifacts. Context reject is explicitly before inference; static class
matching is not full-envelope feasibility or evidence of dynamic unavailability.
Five profile events confirm visibility, not actual adoption, evidence retention
or causal quality-preserving cost improvement. No same-task baseline contrast
has been audited here; single-cell score1 is not a B1 winner claim.
49effective49preserved0pending;143remaining. Same007next50Video6/DeepSeek/Slow/B0.
Snapshot045 first creator74836 failed before write because journal advanced;
independent target-absence proof precedes read-only recollection54902, now running.
041not invoked before success;044/040retain47scope. No benchmark/Planner retry,
new private bodies, payload export or prompt/model/budget/scheduler changes.
All192strict-inactive private/manual/failure/adoption/quality-conditioned analyses
remain required; no pooled scores or causal-adoption claim.

## Cell48 settled: valid Ledger completion, original score0

2026-10-07 16:02HKT. LongBench5/DeepSeek/Fast/A attempt1 completed with original
admission/terminal format valid,score0. No retry/replacement/semantic tuning.
AuditSHA `33bff2aa7b326ee547207e8efaa13de94c855cbd9d8871085abcdaee089750d0`
independently reproduced08:00:24Z; original admission/settlement, all bound
files/startup/terminal/tc/Worker shutdown/10actual SDK contexts pass. Terminal
equals successful model text and frozen deterministic projection; no extra LLM
finalization. Live startup was independently obtained07:55:11Z, not inferred
post-hoc. Four empty stores/five stable resident identities verified.

| Recorded component | Cell48 |
| --- | --- |
| Manager / Verifier / specialist turns |5 /5 /0; no specialists created |
| Physical calls / model requests / successful inference receipts |8 /2 /1 |
| Typed observations |1context reject before inference;1phase restriction |
| E2E |76.336428865s |
| Initial materialization, separate from Agent movement |340278bytes /0.066558754s |
| Complete registered Agent movement |0bytes /0s; not all HTTP/RPC/prompt traffic |
| Complete tool work |0.572077228s |
| Inclusive successful Worker model-action work |21.388029802s; includes backend |
| Complete backend service / tokens / finish |21.345932155s /7381input,2output /stop |
| Frozen-list-price cloud API USD |0.078386323230444199364860016742183659097261; not invoice |
| Execution-grown graph |8action nodes /9artifact-flow edges /25snapshots /peak3actions |

Sequence:three BM25 -> context-rejected model -> three top_k_records ->
successful A4VL4B terminal consuming3artifacts. Context rejection is not backend
inference or proof of dynamic unavailability. Static matching alone does not
validate full request envelope. Generic reduction/recovery is observable, but
score0 subtype/evidence coverage and Ledger-induced causality remain unknown
until the complete-block private audit. Cell47 differs in Planner/network/method;
cell46 differs in network/method, so neither identifies an isolated A effect.
48effective48preserved0pending;144remaining. Same007next49Video6/Qwen/Fast/B1.
Snapshot045 creator74836 running, never duplicate;041not invoked.044/040remain
47-settled scope. Full192strict-inactive private/manual/failure/adoption and
quality-conditioned analyses remain required. No new private bodies, payload
export, source/prompt/model/budget/scheduler change or pooled accuracy claim.

Checkpoint2026-10-07 15:52HKT: snapshot044/feedback040 independently reproduced
07:51:40Z, all47trace/774actual provider-request hashes and population/journal/
control003 bindings. SHA20a69d5a3bfc6755c08eceee39aeccadae1670ddd7fcb2ca9421f5857154e432 /
87ec2a9bc3cb1a858cd61c71512b6ad015408323eac0b43644e3af9b7e4811e0.
354Manager354Verifier66specialist/91profiles174ledgers87rules match;
fixed Verifier/recipient isolation pass.47effective47preserved0pending;
145remaining, same007continues. Next48unreserved at07:51:41Z. No replacement,
score pooling or causal-adoption claim; full192private/manual/failure/adoption
audits and quality-conditioned final analyses remain incomplete.

## Cell47 settled: valid E completion, original score1

2026-10-07 15:41HKT. LongBench5/Qwen/Slow/E attempt1 completed with original
admission/terminal format valid,score1. No retry/replacement/semantic tuning.
AuditSHA `3340bdc606c7e27f162076b618cb3c6b93d840761f473f08bad8fb1edb3c00db`
independently reproduced07:39:48Z with all bound files/startup/terminal/tc/
Worker shutdown/10actual SDK contexts. Terminal equals successful model text
and frozen deterministic projection; no extra semantic finalizer.

| Recorded component | Cell47 |
| --- | --- |
| Manager / Verifier / specialist turns |5 /5 /0; no specialists created |
| Physical calls / model requests / successful inference receipts |8 /2 /1 |
| Typed observations |1context reject before inference;1semantic validation |
| E2E |92.815372110s |
| Initial materialization, separate from Agent movement |340278bytes /1.021389678s |
| Complete registered Agent movement |0bytes /0s; not all HTTP/RPC/prompt traffic |
| Complete tool work |1.454670356s |
| Inclusive successful Worker model-action work |24.340500416s; includes backend |
| Complete backend service / tokens / finish |24.248095095s /8321input,2output /stop |
| Frozen-list-price cloud API USD |0.111940659588886379037723063022362773887509; not invoice |
| Execution-grown graph |8action nodes /6artifact-flow edges /25snapshots /peak3actions |

Sequence:three BM25 -> context-rejected model -> three BM25 -> successful A4VL4B
terminal consuming3artifacts. Class matching does not guarantee full-envelope
feasibility; rejects are not backend inference/dynamic-unavailability proof.
Parallel ready retrieval is observable, not an isolated latency benefit. Score1
does not establish E adoption, retained evidence or a causal quality-cost gain.
Cell45 changes network AND method; cell46 changes Planner AND method. Neither
contrast identifies an isolated E effect.47effective47preserved0pending;
145remaining; same007next48LongBench5/DeepSeek/Fast/A.044creator75443running/
040not invoked;043/039remain46settled. No new private bodies/payload export or
source/prompt/model/budget/scheduler change. All192strict-inactive private/
manual/failure/adoption and quality-conditioned comparisons remain required.

Checkpoint2026-10-07 15:34HKT: snapshot043/feedback039 independently reproduced
07:33:27Z, all46trace/764actual provider-request hashes and population/journal/
control003 bindings. SHA17fe58dea277c0e634c21dc38cdf5f2a7c4645b299c1fd739f5261e94538cef5 /
d0377deb0262b2056eab915a6a38be57ad4008812f6fb92649856d71efc8857b.
349Manager349Verifier66specialist/91profiles169ledgers82rules match;
fixed Verifier and recipient isolation pass.46effective46preserved0pending;
146remaining, same007continues. Next47unreserved at07:33:29Z. No replacement,
pooled scores or causal-adoption claim; full192private/manual/failure/adoption
audits and quality-conditioned final analyses remain incomplete.

## Cell46 settled: valid Blind completion, original score0

2026-10-07 15:24HKT. LongBench5/DeepSeek/Slow/B0 attempt1 completed, original
admission/terminal format valid,score0. No retry/replacement/semantic tuning.
AuditSHA `3db19ef2cdfbf07d076abf6328887abc2979e31fb5bb73576906b2feb541049f`
independently reproduced07:22:30Z with all bound files/startup/terminal/tc/
Worker shutdown and18actual SDK contexts. Terminal equals successful model
text/frozen deterministic projection, without semantic finalization.

| Recorded component | Cell46 |
| --- | --- |
| Manager / Verifier / specialist turns |9 /9 /0; no specialists created |
| Physical calls / model requests / successful inference receipts |12 /3 /1 |
| Typed observations |2context rejects before inference;1semantic validation;1phase restriction |
| E2E |121.085567692s |
| Initial materialization, separate from Agent movement |340278bytes /1.011260211s |
| Complete registered Agent movement |0bytes /0s; not all HTTP/RPC/prompt traffic |
| Complete tool work |2.156071206s |
| Inclusive successful Worker model-action work |18.432844827s; includes backend |
| Complete backend service / tokens / finish |18.291845320s /6399input,2output /stop |
| Frozen-list-price cloud API USD |0.141447618225062783188721614690601788490418; not invoice |
| Execution-grown graph |12action nodes /9artifact-flow edges /37snapshots /peak3actions |

Sequence:three BM25 -> context-rejected model -> three BM25 -> context-rejected
model -> three BM25 -> successful A4VL4B terminal consuming3artifacts.
Context rejects are not backend inference or proof of dynamic unavailability.
Parallel retrieval is observable, not an isolated E2E benefit; Blind has0profile
events. Cell45 differs in Planner, network AND method, so its shorter trajectory
cannot establish an Aware advantage. Score0's semantic subtype remains unknown
until full private audit.46effective46preserved0pending;146remaining; same007
next47LongBench5/Qwen/Slow/E.043creator10234running/039not invoked;042/038remain45
settled. No new private-body reads/payload export or source/prompt/model/budget/
scheduler changes. All192strict-inactive, quality-conditioned analyses pending.

Checkpoint2026-10-07 15:18HKT: snapshot042/feedback038 independently reproduced
07:17:13Z, all45trace/746actual request hashes and population/journal/control003.
SHAf034585bb3d265965ac2b85a21220625b8dd383c04120173ff188fecae01916f /
ef93518ec934bcc25de4268c17ab90a46f4e37fdd849f08e207c4ada7d0b9533.
340Manager340Verifier66specialist/91profiles169ledgers82rules match; fixed
Verifier/recipient scans pass.45effective45preserved0pending;147remaining,
same007continues. Next46unreserved at07:17:15Z. No result replacement, accuracy
pooling or causal-adoption claim; all192private/manual/failure/adoption pending.

## Cell45 settled: context continuation, valid original score0

2026-10-07 15:07HKT. LongBench5/Qwen/Fast/B1 attempt1 completed, original
admission/terminal format valid,score0. No retry/replacement/trajectory tuning.
AuditSHA `0b04374fd6e8c9275ae8ab49412e33dbb3f410c58efe565d83552a8b92da7168`
independently reverified07:06:08Z, including startup metadata, unchanged
residency, tc restoration/Worker exit/terminal projection;14SDK contexts pass.
No independent live-start receipt was written because the run had settled before
its creator's unsettled assertion; no retroactive live-environ claim is made.

| Recorded component | Cell45 |
| --- | --- |
| Manager / Verifier / specialist turns |7 /7 /0; no specialists created |
| Physical calls / model requests / successful inference receipts |8 /2 /1 |
| Typed observations |1context reject before inference;1semantic validation;1phase restriction |
| E2E |84.272942893s |
| Initial materialization, separate from Agent movement |340278bytes /0.138583388s |
| Complete registered Agent movement |0bytes /0s; not all HTTP/RPC/prompt traffic |
| Complete tool work |0.547951926s |
| Inclusive successful Worker model-action work |23.819926551s; includes backend |
| Complete backend service / tokens / finish |23.791085483s /8187input,2output /stop |
| Frozen-list-price cloud API USD |0.099753780943143012795811796595755989316889; not invoice |
| Execution-grown graph |8action nodes /6artifact-flow edges /25snapshots /peak3actions |

Sequence:three BM25 -> context-rejected model -> three BM25 -> successful A4VL4B
terminal model consuming3artifacts. Independent ready retrieval actions do show
parallelism; this does not isolate its E2E benefit. Seven profile-feedback
events establish availability, not adoption or a causal action choice. Score0
does not identify retrieval, reasoning or profile-induced evidence loss; private
semantic attribution and matched quality-conditioned comparisons wait all192
and strict inactivity.45effective45preserved0pending,147remaining; same007
continues next46LongBench5/DeepSeek/Slow/B0.042creator33272 running,038not invoked;
041/037 remain44-settled scope. No private-body reads/payload export or source/
prompt/model/budget/scheduler changes.

Checkpoint2026-10-07 15:03HKT: snapshot041/feedback037 independently reproduced
07:02:52Z, every44trace/732actual request hashes and population/journal/
control003 bindings. SnapshotSHA8106d365c6fdd45f41ca8f98f1695d252fb9877b564fd66d9d84483ebf910711;
feedbackSHA56ffcc0f4b2b4b71a29465416c599751f10c9b99538af91ce7d744fa64929db6.
333Manager333Verifier66specialist/84profiles169ledgers82rules match;
fixed Verifier/recipient scans pass. Captured44settled/44preserved/0pending;
same007has now reserved45LongBench5/Qwen/Fast/B1. No live45result claimed.
No causal adoption/quality attribution, pooled scores or altered trajectories;
all192private/manual/failure/adoption/Q1-Q10 remain incomplete.

## Cell44 settled: valid Ledger completion, original score0 retained

2026-10-07 14:54HKT. Video4/Qwen/Fast/A attempt1 completed, original admission
valid, terminal format valid, score0. No retry, replacement or semantic tuning.
End audit SHA `3c120f3f0f4f6d8799071638b992a4775d0b4a0e0711b71fcc6eac900615497e`
independently reverified06:52:52Z; terminal equals successful A4VL4B output and
frozen deterministic projection, no extra LLM finalizer.8actual SDK contexts
pass original privacy/admission checks. Same007continues,44effective settled,
148remaining; snapshot041 still being verified,040/036 retain43-settled scope.

| Recorded component | Cell44 |
| --- | --- |
| Manager / Verifier / specialist turns |4 /4 /0; no specialists created |
| Physical calls / model requests / successful inference receipts |4 /3 /1 |
| Context rejects |2, both explicitly before inference |
| E2E |119.184342134s |
| Initial materialization, separate from Agent movement |9320768bytes /0.893052136s |
| Complete registered Agent movement |0bytes /0s; not all HTTP/RPC/prompt traffic |
| Complete tool work |1.622090922s |
| Inclusive successful Worker model-action work |25.270264869s; includes backend |
| Complete backend service / tokens / finish |25.146228276s /4548input,2output /stop |
| Frozen-list-price cloud API USD |0.225544061175407592447414927118351293532998; not invoice |
| Execution-grown graph |4action nodes /44artifact-flow edges /13snapshots /peak1action |

Sequence:sample_frames -> context-rejected invoke_model -> context-rejected
invoke_model -> successful invoke_model consuming4artifacts. Artifact-flow
edges are not44distinct action-to-action dependencies. Matching abstract model
classes did not guarantee context-envelope feasibility; rejects are not actual
backend inference or evidence of dynamic deployment unavailability. Score0
does not identify evidence loss, reasoning failure or ledger-induced changes.
Cell42 shares task/Planner but differs in network AND method; do not assign a
method effect from that contrast. Private semantic attribution and matched,
quality-conditioned analyses wait all192and strict inactivity. No new support/
corpus/store-body decoding, payload export, routing changes or accuracy pooling.

Checkpoint2026-10-07 14:44HKT: snapshot040/feedback036 independently reproduced
06:43:43Z, including all43trace/724actual request hashes and population/journal/
control003 bindings.43effective43preserved0pending/149remaining; same007continues.
329Manager329Verifier66specialist;84profiles165ledgers82rules match exactly.
Snapshot SHA2a6b6296b4961ea50d4bff161c49fd9b11fc28a64902f23e5cc481eb4b36b506;
feedback SHA89d8b84020581db2b9652fcb6a974e4165d110078fbf7716df96a213cb889af2.
No additional benchmark run/result replacement; full192private/adoption audits
pending. Visibility does not establish method effects or semantic evidence retention.

## Cell43 settled: context continuation, valid original score0

2026-10-07 14:35HKT. Video4/DeepSeek/Slow/B1 attempt1 completed with valid
terminal output and original evaluator score0. Admission valid, no retry.
Audit SHA `7189e1ce74a9ba5733defbc2f15b87c6a662dafc50ca4991b757ab2527623749`
independently binds all source/state/startup/terminal/tc/shutdown evidence and
8actual SDK contexts. No extra semantic finalizer.

| Recorded component | Cell43 |
| --- | --- |
| Manager / Verifier / specialist turns |4 /4 /0; no specialists created |
| Physical calls / model requests / successful inference receipts |3 /2 /1 |
| Typed observations |1context reject before inference;1phase restriction |
| E2E |120.972435369s |
| Initial materialization, separate from Agent movement |9320768bytes /26.083399571s |
| Complete registered Agent movement |0bytes /0s; not all HTTP/RPC/prompt traffic |
| Complete tool work |1.833074475s |
| Inclusive successful Worker model-action work |37.857244558s; includes backend service |
| Complete backend service / tokens / finish |37.694093936s /6719input,2output /stop |
| Frozen-list-price cloud API USD |0.151280288071858515260633279740629027757479; not invoice |
| Execution-grown graph |3action nodes /16artifact-flow edges /10snapshots /peak1action |

Sequence:sample_frames -> context-rejected invoke_model -> successful invoke_model
on resident-a4-vl4b-v1 with6terminal artifacts. Raw model text equals canonical
answer/frozen deterministic projection. Failed first model request explicitly
reached_model_inference=false; abstract static matching is not full-envelope
feasibility or dynamic-unavailability proof. Typed continuation is part of the
frozen native loop, not a harness retry or automatic repair.

Registered movement0 excludes prompt/RPC traffic; initial placement is separate.
Inclusive model-action work and backend service must not be double-counted.
Four predecision profile events do not prove profile adoption or caused revision.
Score0 does not establish evidence loss or its cause. Comparison to42 changes
Planner and method; comparison to41 changes network and method. These are not
isolated matched method effects. Full192strict-inactive private/matched audit
and quality-conditioned analysis remain pending; no winner/causal claim.

43effective/43preserved/zero pending,149remaining; same007continues,
next44Video4/Qwen/Fast/A. Snapshot040 creator76380 running/not completed;
feedback036 not invoked.039/035 retain42-settled scope. No source/prompt/model/
budget/scheduler change/private-body decoding/payload export/fresh full-test claim.

Checkpoint2026-10-07 14:27HKT: snapshot039/feedback035 independently reproduced
06:26:59Z, including all42trace/716actual request hashes and population/journal/
control003 bindings.42effective42preserved0pending/150remaining; same007continues.
325Manager325Verifier66specialist;80profiles165ledgers82rules match exactly.
Snapshot SHA0dd95c52642e9c609dc83127a3fd7978e4a00c3300fd4dcd8d96aa6902a6f497;
feedback SHAf1b51584322aa6634a8970d1f4f0dba99f2197a1545446af4adb71f33265e9d7.
No additional benchmark run/result replacement; full192private/adoption audits
pending. Visibility does not establish method effects or semantic evidence retention.

## Cell42 settled: valid correct Blind completion, not a method comparison

2026-10-07 14:20HKT. Video4/Qwen/Slow/B0 attempt1 completed with valid
terminal output and original evaluator score1. Admission valid, no retry.
Audit SHA `9805d2559b6dd287c82c4651b5b560da70721a40dbfb47fd33d03647eeb6db61`
independently binds source/state/startup/terminal/tc/shutdown evidence and
8actual SDK contexts. Terminal comes from successful physical model inference,
not an additional semantic finalizer.

| Recorded component | Cell42 |
| --- | --- |
| Manager / Verifier / specialist turns |4 /4 /0; no specialists created |
| Physical calls / model requests / successful inference receipts |2 /1 /1 |
| Typed observations |1semantic validation;1phase restriction; no context rejection |
| E2E |119.777923695s |
| Initial materialization, separate from Agent movement |9320768bytes /26.084566870s |
| Complete registered Agent movement |0bytes /0s; not all HTTP/RPC/prompt traffic |
| Complete tool work |1.717550502s |
| Inclusive successful Worker model-action work |44.021291312s; includes backend service |
| Complete backend service / tokens / finish |43.774389744s /7741input,2output /stop |
| Frozen-list-price cloud API USD |0.084320170345075007640282225381681925085371; not invoice |
| Execution-grown graph |2action nodes /7artifact-flow edges /7snapshots /peak1action |

Sequence:sample_frames -> successful invoke_model on resident-a4-vl4b-v1,
with7terminal input artifacts. Raw model text equals canonical answer/frozen
deterministic projection. No contact_sheet action or context-rejected inference.
Semantic-validation/phase-restriction observations remain in the original trace,
not automatically repaired or retried. Registered movement0 excludes prompt/RPC
traffic; initial placement is separate fixed setup. Inclusive model-action work
and backend service must not be double-counted.

The correct n1 output does not prove retained required evidence. Comparing this
cell to cell41(E/DeepSeek/Fast) cannot isolate a method effect:Planner, network
and method all differ. Full192strict-inactive private audit and matched,
quality-conditioned analysis remain pending; no causal method/winner claim.

42effective/42preserved/zero pending,150remaining; same007continues,
next43Video4/DeepSeek/Slow/B1. Snapshot039 creator47240 running, not completed;
feedback035 not invoked.038/034 retain41-settled scope. No source/prompt/model/
budget/scheduler change/private-body decoding/payload export/fresh full-test claim.

Checkpoint2026-10-07 14:13HKT: successful snapshot038/feedback034 independently
reproduced06:12:50Z:all41trace/708actual request hashes and population/journal/
control003 bindings.41effective41preserved0pending/151remaining; same007continues.
321Manager321Verifier66specialist;80profiles165ledgers82rules exactly match.
Snapshot SHAea8c08d8c4f10c737a9ee812c6b79d12e4b21c7af4458c6c548a5e246e2566cd;
feedback SHA1746a07531c4958ccce878214ffea1b5167498e70c63730ee02dccb29e0e390e.
No additional benchmark run/result replacement; full192private/adoption audits
pending. Feedback visibility does not establish causal effects or evidence retention.

## Cell41 settled: all actions succeeded, original quality score0

2026-10-07 14:05HKT. Video4/DeepSeek/Fast/E attempt1 completed with valid
terminal output and original evaluator score0. Admission valid, no retry.
Audit SHA `ee2ac6ead0c2c845020ecb50c8d605e52e5678339d98190614d9ba67e461055a`
independently binds all source/state/startup/terminal/tc/shutdown evidence and
6actual SDK contexts. No hidden semantic finalizer.

| Recorded component | Cell41 |
| --- | --- |
| Manager / Verifier / specialist turns |3 /3 /0; no specialists created |
| Physical calls / model requests / successful inference receipts |3 /1 /1 |
| Typed failures |none |
| E2E |54.749900806s |
| Initial materialization, separate from Agent movement |9320768bytes /0.838005692s |
| Complete registered Agent movement |0bytes /0s; not all HTTP/RPC/prompt traffic |
| Complete tool work |1.995775747s |
| Inclusive successful Worker model-action work |7.466222887s; includes backend service |
| Complete backend service / tokens / finish |7.453622537s /1368input,2output /stop |
| Frozen-list-price cloud API USD |0.16554395354708406967937389548093915677860; not invoice |
| Execution-grown graph |3action nodes /33artifact-flow edges /10snapshots /peak1action |

Sequence:sample_frames -> make_contact_sheet -> successful invoke_model on
resident-a4-vl4b-v1. Terminal consumes one artifact; raw model output equals
canonical answer/frozen deterministic projection. No context/tool failure.
Registered artifact movement0 does not mean all communication0; inclusive
model action and backend service are overlapping scopes, not additive work.
No evidence-loss/E-adherence/causal saving claim from compact wrong trajectory;
private semantic diagnosis waits all192and strict inactivity. The33recorded
artifact-flow edges must not be interpreted as33distinct action-DAG dependencies.

41effective/41preserved/zero pending,151remaining; same007continues,
next42Video4/Qwen/Slow/B0. Snapshot038 creator49490 running; feedback034
not yet invoked.037/033 retain40-settled scope. No prompt/model/budget/scheduler
change/new private body decoding/payload export/fresh full-test claim.

Checkpoint2026-10-07 13:58HKT: snapshot037/feedback033 now closed, independently
reproduced05:57:57Z:all40trace/702actual request hashes and population/journal/
control003 bindings.40effective40preserved0pending/152remaining; same007continues.
318Manager318Verifier66specialist;80profiles162ledgers79rules exactly match.
Snapshot SHA206064b2541a4ce172a5d2e8d78d8c7fd4a22b96afe689edadb45d4c61813a59;
feedback SHA2b0e17eebb2a796b09713a2216835f313a93bc1c98a632541c0109684f37bb45.
No additional benchmark run/result replacement; full192private/adoption audits
pending. Visibility does not establish causal method effect or retained evidence.

## Cell40 settled: valid completion, original score0 retained

2026-10-07 13:51HKT. LongBench3/DeepSeek/Fast/B0 attempt1: execution complete,
format valid, original evaluator score0, admission valid. No retry/replacement.
Audit SHA `46b5c5c2041ff53aab2390234e5154f784f8f4b947b1488a2016037b9094f37d`
independently reverified05:49:22Z; source/state/tc/shutdown/18SDK contexts pass.

| Recorded component | Cell40 |
| --- | --- |
| Manager / Verifier / specialist turns |9 /9 /0; no specialists created |
| Physical calls / model requests / successful inference receipts |16 /3 /1 |
| Typed failures |1oversized read;2context rejects before inference;3phase restrictions;1semantic validation |
| E2E |146.232869495s |
| Initial materialization, separate from Agent movement |967830bytes /0.106842131s |
| Registered Agent transfer |successful receipts0bytes/0s; complete failed-inclusive total unknown |
| Tool work |successful3.526244250s; complete failed-inclusive total unknown |
| Inclusive successful Worker model-action work |18.728596011s; includes backend service |
| Complete backend service / tokens / finish |18.660636758s /6468input,2output /stop |
| Frozen-list-price cloud API USD |0.189032943568211110963472807239001315457274; not invoice |
| Execution-grown graph |16nodes /12artifact-flow edges /49snapshots /peak4actions |

Sequence: oversized read; four BM25 actions; context-rejected model; four
further BM25 actions; second context-rejected model; four further BM25 actions;
successful terminal on resident-a4-vl4b-v1 with four artifact inputs. Raw model
answer equals canonical answer/frozen deterministic projection. Context rejects
are not inference and do not prove dynamic deployment unavailability. An
unmeasured failed read keeps complete transfer/tool totals unknown rather than0.
Inclusive model action must not be added to backend service as independent work.
Score0 establishes quality failure, not its evidence/reasoning cause; that needs
full192strict-inactive private audit. No claim of method superiority/causal savings.

40effective/40preserved/zero pending,152remaining; same007queue continues with
next41Video4/DeepSeek/Fast/E. Snapshot037 creator44480 running, not completed;
feedback033 not invoked.036/032 retain39-settled scope. No source/prompt/model/
budget/scheduler changes, private-body decoding/payload export or fresh full-test claim.

## Cell39 settled: valid original score1, not causal B1 evidence

Checkpoint2026-10-07 13:45HKT: successful snapshot036/feedback032 independently
reproduced all39trace/684provider-request hashes;309Manager309Verifier66specialist,
80profiles162ledgers79rules.39effective/39preserved/zero pending,153remaining;
same007queue continues. No new benchmark run or result replacement by the auditor.
Latest snapshot SHA8ce9396545553766995b169faba60eaa884e3b2e67c9db474fb78900639d4483;
feedback SHA038659a45522f77415ffdd33962185d9b5baedf7c2a254eabbe4ceb74c6fa001.
No adoption/coverage/causal savings conclusion; full192post-block audits pending.

2026-10-07 13:37HKT. LongBench3/Qwen/Slow/B1 attempt1 completed with valid
canonical terminal and original evaluator score1; original admission valid,
no retry/replacement. AuditSHA
`364421dd3d4fd9863e52f5960e8c183a19c73356b29799c490a8db2072e00ad0`
independently binds source/state/terminal and22actual SDK contexts. StartupSHA
`83f2d154a1344e663572ff0ae92fdc90a297941daeb1c141e1438ccf1ad7d517`.

| Recorded component | Cell39 |
| --- | --- |
| Manager / Verifier / specialist turns |7 /7 /8; one specialist created, peak1 |
| Physical calls / model requests / successful inference receipts |16 /3 /1 |
| Typed failures |2context rejects explicitly inference=false;1phase restriction |
| E2E |117.586936283s |
| Initial materialization, separate from Agent movement |967830bytes /2.811361854s |
| Complete registered Agent movement |0bytes /0s; not all HTTP/RPC/prompt traffic |
| Complete tool work |3.697231580s |
| Inclusive successful Worker model-action work |0.526592209s; includes backend service |
| Complete backend service / tokens / finish |0.522301237s /448input,2output /stop |
| Frozen-list-price cloud API USD |0.377172170770273322791958436864693923650330; not invoice |
| Execution-grown graph |16nodes /18artifact-flow edges /49snapshots /peak4actions |

Sequence: five BM25 actions; context-rejected model; aggregation; BM25/read;
BM25/read; three further BM25 actions; another context-rejected model;
successful terminal on resident-4090-gpu0-qwen35-27b-v1. Terminal has no artifact
inputs; raw model text equals canonical answer/frozen deterministic projection.
Prompt-only does not imply no evidence: inline prompt content was not privately
audited here. No hidden semantic finalizer. Context rejects are not inference
calls or proof of dynamic unavailability. Registered zero movement is not zero
HTTP/RPC/prompt traffic; inclusive model-action work must not be added again to
backend service. Persisted work receipts are not an additive E2E decomposition.

Original score1 is retained, but n1 trajectory success does not identify B1
adoption/causal benefit, specialist utility or evidence retention. These questions
wait for full192strict-inactive private audit. Same007continues;39effective/
39preserved/zero pending/153remaining. Next40LongBench3/DeepSeek/Fast/B0.
Snapshot036creator94698 running/not completed;feedback032 not invoked.035/031
retain38-settled scope. No aggregation/old-new pooling, ordinary retry, source/
prompt/model/budget/scheduler change, private-body decode or raw payload export;
documentation-only/no fresh full-test claim/no push.

## Cell39 running; snapshot035 still covers38settled

2026-10-07 13:33HKT. LongBench3/Qwen/Slow/B1 attempt1 atomic2825208 actually
owned/live; same007continued without restart.38effective settled/39preserved/
one pending/153unstarted. StartupSHA
`83f2d154a1344e663572ff0ae92fdc90a297941daeb1c141e1438ccf1ad7d517`
independently binds four empty stores/five resident instances and atomic004-only
source05:33:11Z; successful creator never repeat. No completed outcome/evaluator
score claimed. Snapshot035/feedback031 retain38-settled scope. Full192and final
strict-inactive private/manual/failure/recipient/adoption, quality-conditioned
Q1-Q10 unfinished. No retry/source/prompt/model/budget/scheduler change, new
private-body decode or raw payload export; docs-only/no fresh full-test claim.

## Snapshot035 and feedback031 completed: thirty-eight settled

2026-10-07 13:28HKT. Snapshot035 creator90061 completed exit0, captured
05:27:33Z; successful creator never repeat. SHA
`5e7369fd30505d1471818bdc126c74fe0265e1597cc7e4c96c976508ce6846f3`:
38effective/38preserved/zero pending/five original findings retained/zero effective
confounders/zero exclusions. JournalSHA
`51c1648d45db3b0a359693490f72e516bfd050568cfbfe78c7cc65885bb7b8b8`.
Source/control003/collector/schedule/execution004 unchanged; no score aggregation
or old/new pooling. Feedback031SHA
`92484fa51901315e83cbc4986e54c701ae50a594da8c072ca07d3d4f686e98b2`
verifies662actual SDK contexts:302Manager/302Verifier/58specialist, exact73B1
profiles/162A_Eledgers/79Efrozen rules. Fixed Verifier and non-Manager feedback
exclusion pass. Independent05:28:37Z rehashes all38traces and662actual requests,
population/journal/control bindings and unchanged PhaseI journal. Visibility
does not establish adoption, coverage or causal quality-preserving resource
benefit. No new auditor model calls, support/corpus/store-body decoding or raw
payload export. Successful035/031 creators must never repeat.

Same007supervisor2772570/controller2772571 owned/live05:28:38Z before39
LongBench3/Qwen/Slow/B1;154remaining. All192and final strict-inactive private/
manual/failure/recipient/adoption, quality-conditioned Q1-Q10/named reports remain
unfinished. No ordinary retry, source/prompt/model/budget/scheduler change or
fresh test-suite claim; documentation-only/no push.

## Cell38 settled: valid score0 after context recovery

2026-10-07 13:23HKT. LongBench3/DeepSeek/Slow/A attempt1 completed with valid
canonical terminal and original evaluator score0; original admission valid,
no retry/replacement. AuditSHA
`425e3be9803ac58e07df0a64feaafbb62c43d1b29c7a68baf121f5d77a313212`
independently binds source/state/terminal and24actual SDK contexts. StartupSHA
`83148a777f6110226d290d4c0ca6285c90205607cf3232d7ec02e61523ac74f7`.

| Recorded component | Cell38 |
| --- | --- |
| Manager / Verifier / specialist turns |12 /12 /0; no specialists |
| Physical calls / model requests / successful inference receipts |20 /4 /1 |
| Context rejects |3, explicitly inference=false |
| Other typed observations |1oversized read,3phase restrictions,1semantic validation |
| E2E |178.834073287s |
| Initial materialization, separate from Agent movement |967830bytes /2.810816925s |
| Successful registered Agent movement |0bytes /0s; complete failed-inclusive movement unknown |
| Successful tool work |3.848558175s; complete failed-inclusive work unknown |
| Inclusive successful Worker model-action work |13.915417022s; includes backend service |
| Complete backend service / tokens / finish |13.791579259s /4882input,2output /stop |
| Frozen-list-price cloud API USD |0.292623500179380539204613401719395686894581; not invoice |
| Execution-grown graph |20nodes /15artifact-flow edges /61snapshots /peak3actions |

Sequence: oversized read; four successive three-BM25 groups with context-rejected
model requests after each of the first three; three select_fields actions;
successful terminal model on resident-a4-vl4b-v1 consuming three artifacts. Raw
terminal equals canonical answer/frozen deterministic projection. No hidden
semantic finalizer. Preflight rejects are not backend inference or evidence of
dynamic unavailability. Registered successful zero movement is not all HTTP/RPC/
prompt traffic; failed-inclusive movement/tool work remains unknown. Inclusive
model-action work must not be added again to backend service. Persisted work
receipts, potentially overlapping, are not an additive E2E decomposition.

Score0 is a valid quality failure; observed context recovery does not establish
adequate evidence or ledger-driven improvement. Retrieval/reduction adequacy,
adoption and causal benefit wait for full192strict-inactive private audit.
Same007continues;38effective/38preserved/zero pending/154remaining. Next39
LongBench3/Qwen/Slow/B1. Snapshot035creator90061 running/not completed;
feedback031 not invoked. Snapshot034/feedback030 retain37-settled scope. No
aggregation/old-new pooling, ordinary retry, source/prompt/model/budget/scheduler
change, private-body decoding or raw payload export; no fresh full-test claim.

## Cell38 running; snapshot034 still covers37settled

2026-10-07 13:18HKT. LongBench3/DeepSeek/Slow/A attempt1 atomic2813364
actually owned/live; same007continued without restart.37effective settled/
38preserved/one pending/154unstarted. StartupSHA
`83148a777f6110226d290d4c0ca6285c90205607cf3232d7ec02e61523ac74f7`
independently binds four empty stores/five resident instances and atomic004-only
source05:17:51Z; successful creator never repeat. No completed outcome/evaluator
score is claimed. Snapshot034/feedback030 remain37-settled, not38. All192and
final strict-inactive private/manual/failure/recipient/adoption, quality-conditioned
Q1-Q10 remain. No ordinary retry, source/prompt/model/budget/scheduler change,
new private-body decode or raw payload export; no fresh full-test claim.

## Snapshot034 and feedback030 completed: thirty-seven settled

2026-10-07 13:14HKT. Snapshot034 creator66401 completed exit0, captured
05:13:07Z; successful creator never repeat. SHA
`c5f081166700de5519f0819f83322eba519ca575ece21a8509d7dfd3bd1cb60d`:
37effective/37preserved/zero pending/five original findings retained/zero effective
confounders/zero exclusions. JournalSHA
`a77610411d67eef9fa15deab35b81447fc67117b5eb92f4de62e2531e3607397`.
Source/control003/collector/schedule/execution004 unchanged; no score aggregation
or old/new pooling. Feedback030SHA
`54fbe4880cf6eaa4e830fdb8dc023442034e6ada5c5f0ca5bba73a298651fd59`
verifies638actual SDK contexts:290Manager/290Verifier/58specialist, exact73B1
profiles/150A_Eledgers/79Efrozen rules. Fixed Verifier and non-Manager feedback
exclusion pass. Independent05:14:39Z rehashes all37traces and638actual provider
requests, population/journal/control bindings and unchanged PhaseI journal.
Visibility does not identify adoption, coverage or causal quality-preserving
resource benefit. No new auditor model call, support/corpus/store-body decoding
or raw payload export. Successful034/030 creators must not repeat.

Same007supervisor2772570/controller2772571 owned/live05:14:41Z before38
LongBench3/DeepSeek/Slow/A;155remaining. All192and final strict-inactive private/
manual/failure/recipient/adoption, quality-conditioned Q1-Q10/named reports remain
unfinished. No ordinary retry, source/prompt/model/budget/scheduler change or
fresh test-suite claim; documentation-only/no push.

## Cell37 settled: valid score0; rule visibility is not causal evidence

2026-10-07 13:08HKT. LongBench3/Qwen/Fast/E attempt1 completed with valid
canonical terminal and original evaluator score0; original admission valid,
no retry/replacement. End-auditSHA
`5926c8f7a275c1a78082acc5739f7a292b04674df247584ce79f60adff7c6602`
independently reproduces all source/state/terminal bindings and12SDK contexts.
StartupSHA `949ba9d893f8d8c689a21871797069deade78c56cce1296191890c5a491538b7`.

| Recorded component | Cell37 |
| --- | --- |
| Manager / Verifier / specialist turns |6 /6 /0; no specialists |
| Physical calls / model requests / successful inference receipts |5 /2 /1 |
| Typed failures |1context reject explicitly inference=false;1semantic validation |
| E2E |89.419063866s |
| Initial materialization, separate from Agent movement |967830bytes /0.123360969s |
| Complete registered Agent movement |0bytes /0s; not all HTTP/RPC/prompt traffic |
| Complete tool work |0.517319935s |
| Inclusive successful Worker model-action work |16.775824944s; includes backend service |
| Complete backend service / tokens / finish |16.667139426s /5902input,2output /stop |
| Frozen-list-price cloud API USD |0.115794140235719315962210499740894776704452; not invoice |
| Execution-grown graph |5nodes /3artifact-flow edges /16snapshots /peak1action |

Sequence: BM25; context-rejected model; another BM25; select_fields; successful
terminal inference on resident-a4-vl4b-v1 with one input artifact. Raw terminal
text equals canonical answer and the frozen deterministic projection. No hidden
semantic finalizer. Context-rejected request is not backend inference; abstract
requirements matching does not prove the complete prompt/artifact envelope fits.
Successful registered movement zero does not measure all transport/prompt traffic.
Inclusive model-action work must not be added again to backend service; these
persisted work receipts are not an additive E2E decomposition.

Score0 is a valid quality failure; neither compact information flow nor a wrong
answer alone proves evidence loss or E-rule adoption/causality. Those questions
wait for all192strict-inactive private audit. Same007 continues;37effective/
37preserved/zero pending/155remaining. Next38LongBench3/DeepSeek/Slow/A.
Snapshot034 creator66401 running, not completed; feedback030 not invoked.
Snapshot033/feedback029 retain36-settled scope. No score aggregation, old/new
pooling, ordinary retry, prompt/model/budget/scheduler change or payload export.

## Cell37 running; snapshot033 still covers36settled

2026-10-07 13:05HKT. LongBench3/Qwen/Fast/E attempt1 atomic2802358 actually
owned/live; same007continued without restart.36effective settled/37preserved/
one pending/155unstarted. StartupSHA
`949ba9d893f8d8c689a21871797069deade78c56cce1296191890c5a491538b7`
independently binds four empty stores/five resident instances and atomic004-only
source05:05:15Z; successful creator never repeat. No completed outcome/evaluator
score is claimed. Snapshot033/feedback029 remain36-settled, not37. All192and
final strict-inactive private/manual/failure/recipient/adoption, quality-conditioned
Q1-Q10 remain. No ordinary retry, source/prompt/model/budget/scheduler change,
new private-body decode or raw payload export; no fresh full-test claim.

## Snapshot033 and feedback029 completed: thirty-six settled

2026-10-07 13:01HKT. Snapshot033 creator56740 completed exit0, captured
04:59:52Z; successful creator must never repeat. SHA
`3fa8ce7ca12b1179bac9fa2c990c281f7b0de61efc9577621fbc9082d94b3748`:
36effective/36preserved/zero pending/five raw findings retained/zero effective
confounders/zero exclusions. JournalSHA
`40d1d9231a85cdd7859d0bf5c033ba05f55ced2285654b05e0f6c7462fe8e259`.
Source/control003/collector/schedule/execution004 unchanged; no score aggregation
or old/new pooling. All192 and strict-inactive private/manual/failure/recipient/
adoption, quality-conditioned Q1-Q10/named reports remain incomplete.

Feedback029SHA
`9ff31599cab4d8a19ce960b51ca9dcdfcc83e026e091ef11d8239b136b465339`
verifies626actual SDK contexts:284Manager/284Verifier/58specialist. Exact73B1
profiles/144A_Eledgers/73Efrozen rules; fixed Verifier and non-Manager feedback
exclusion pass. Independent05:01:22Z readback reproduces all36trace hashes and
626actual request hashes, population/journal/control bindings and unchanged
PhaseI journal. Visibility does not prove adoption, coverage or causal savings.
No new auditor model call, support/corpus/store-body decoding or raw payload export.

Same007supervisor2772570/controller2772571 independently owned/live05:01:24Z;
next37LongBench3/Qwen/Fast/E remains unstarted;156remaining. No ordinary retry,
source/runtime/prompt/model/budget/scheduler change or new test-suite claim.

## Cell36 settled: Blind valid completion with wrong benchmark answer

2026-10-07 12:56HKT. LongBench4/Qwen/Fast/B0 attempt1: execution completed,
terminal format valid, original evaluator score0, original admission valid.
No retry/replacement. Independent auditSHA
`3825a7441d8c5e3f42372e34bc961ced038d2a85f4e27950a55b2e69f1954561`
binds source/store/residency/tc/shutdown/terminal and26actual SDK requests.
StartupSHA `0a69e931c8a5f85d7986d1e0917f00c6c55a2a4596fbb363aeb3fbbf6e72ad12`.

| Recorded component | Cell36 |
| --- | --- |
| Manager / Verifier / specialist turns |9 /9 /8; one specialist created, peak1 |
| Physical calls / model requests / successful inference receipts |16 /3 /1 |
| Context rejects |2, explicitly inference=false |
| Other typed observations |2oversized reads,1semantic validation,1phase restriction |
| E2E |121.426158824s |
| Initial materialization, separate from Agent movement |115726bytes /0.072326423s |
| Successful registered Agent movement |0bytes /0s; complete failed-inclusive movement unknown |
| Successful tool work |0.341129221s; complete failed-inclusive tool work unknown |
| Inclusive successful Worker model-action work |11.247883773s; includes backend service |
| Complete backend service / tokens / finish |11.059325921s /3913input,2output /stop |
| Frozen-list-price cloud API USD |0.219260006112225780305345540068297479371239; not invoice |
| Execution-grown graph |16nodes /16artifact-flow edges /49snapshots /peak3actions |

Sequence: oversized read; four BM25 calls; context-rejected model request;
aggregation; second context-rejected model request; oversized read; six further
BM25 calls; successful terminal model on resident-a4-vl4b-v1. Terminal consumes
one artifact; raw model text equals canonical answer and the existing frozen
deterministic projection. No hidden semantic finalizer. The two context failures
are not inference calls or proof of dynamic deployment unavailability. Successful
registered zero movement is not zero HTTP/RPC/prompt traffic. Inclusive model work
must not be added to backend service as independent work. Recorded overlapping
work is not an E2E decomposition.

Score0 is valid quality failure; retrieval/evidence adequacy, specialist utility,
semantic loss and method causality are not identified before the all192 strict-
inactive private audit. Same007 remains live;36effective/36preserved/zero pending,
156remaining. Snapshot033 creator56740 is running, not completed; feedback029
not invoked. Snapshot032/feedback028 retain35-cell scope. No aggregation/old-new
pooling, ordinary retry, prompt/model/budget/scheduler change or payload export.

## Cell36 running: no new completed result yet

2026-10-07 12:52HKT. The unchanged continuation gate reached the next cell.
Same007controller2772571/supervisor2772570 owned/live; cell36LongBench4/Qwen/
Fast/B0 attempt1 atomic2791465 actually running. Current35effective settled/
36preserved attempts/one pending/156unstarted. Startup receiptSHA
`0a69e931c8a5f85d7986d1e0917f00c6c55a2a4596fbb363aeb3fbbf6e72ad12`
independently binds source004-only execution, four empty Worker stores and five
resident instances04:52:17Z. Creator succeeded and must not be repeated.
No completed outcome/evaluator score is claimed. Snapshot032/feedback028 still
cover35settled cells, not36. No ordinary retry, source/prompt/model/budget/
scheduler change or new private-body decode/payload export. All192and final
strict-inactive private/manual/failure/recipient/adoption, quality-conditioned
Q1-Q10/named reports remain unfinished; goal active.

## Snapshot032 and feedback028 completed: thirty-five settled

2026-10-07 12:22HKT. Snapshot032 completed04:20:00Z, SHA
`e4e1499e3ab99b2eb53efe8cd2a2909769f46ec401594eaf2ad234a1791b6714`:
35effective/35preserved/zero pending/five original findings retained/zero
effective confounders/zero exclusions. Original journalSHA
`91e98fc45c025b9f5f0a88f84356e8e1eceee203b4bb78b6cf5189741720533e`.
New control003 binds all exact sidecars; execution004, schedule and collector
unchanged. Successful creator19362 must not be repeated; next snapshot033.

Feedback028SHA
`72eb400fe5898983c495e73c5925d2103a8403a6947c0828e697aac8a9ef4d8a`
verifies600actual SDK contexts:275Manager/275Verifier/50specialist,73B1profiles/
144A_Eledgers/73Efrozen-rule exact matches. Same population/journal/control
independently reverified04:21:08Z. Fixed Verifier, role-specific original scans
and non-Manager feedback exclusion pass. Visibility does not prove rule adoption,
evidence adequacy, specialist benefit or causal savings. Failed-call model/traffic
work in35 remains unknown. No score aggregation or old/new pooling.

Actual007supervisor2772570/controller2772571 independently owned/live; full
startup gate ongoing, no36reservation yet04:21:04Z. Launch69573 completed exit0
and must not be repeated. Original private guard negative probe003SHA
`4bf22c701e49377f3c5e360e47d6d8adeff796243d4942d9195aa6a83224093c`
proves live-controller rejection before any private body read. Guard source and
controller source independently unchanged04:22:21Z. Next36LongBench4/Qwen/Fast/
B0; remaining157. All192strict-inactive private/manual/failure/adoption, final
quality-conditioned Q1-Q10/named reports remain unfinished. No source/runtime/
prompt/model/budget/scheduler change, audit model calls or raw payload export.

## Cell35 exact admission review completed

2026-10-07 12:01HKT. Existing source-bound reviewer confirmed all three
post-backend JSON output failures; append-only sidecarSHA
`cd859f740c62e9f400289763c97ca8b688f50b4c48de68a947f9e0dfa6ad362f`
independently reproduced04:00:53Z. Effective disposition is valid; original
completed/format-valid/score1, raw confounder and journal are unchanged. Failed
JSON model-outcome inference=false flags do not establish no inference: actual
backend completion before parsing is proven. At least eight backend completions
exist, although only five returned successful telemetry receipts; complete work,
tokens and traffic remain unknown. No ordinary retry or hidden repair.
Full continuation-control003 validation is still running; latest completed
full-population snapshot remains031/34cells, not a35-cell snapshot. Older pending
review captures below retain historical scope. No new private-body decoding or
model calls by this audit; full192quality-conditioned final analysis remains.

Additional independently hash-bound metadata04:05:47Z: four specialists used
7/5/5/7reasoning turns, max7 below the shared eight-turn ceiling. Actions by
owner:19Manager plus6/4/3/13specialist actions, total45. A13action trajectory
is not thirteen reasoning turns. Final traceSHA
`b92ffbf4e4b7b1fe12ba0ed9f366c84f807289750c5745cc02de38f7c1e70189`.
No per-agent prompt or result text exported; no specialist utility claim.

## Cell35 terminal completion preserved; exact gate review pending

2026-10-07 11:50HKT. LongBench4/DeepSeek/Slow/E attempt1 completed and
received original evaluator score1 with valid output format. Original controller
006 stopped on three JSON materialization findings; this capture is not a claim
of35effective admission. Original trace/result/admission/journal remain immutable.
Independent auditSHA `af2c1ce4eb8f3cd7b4e0ec74cbb547a5f3fc19b894318072587eaa6cf6ce7fd0`
binds terminal provenance, Worker exit/store/residency/tc and fifty SDK contexts.

| Receipt-derived metric | Value / scope |
| --- | --- |
| Reasoning |13Manager /13Verifier /24total specialist turns |
| Specialists |4created /2peak-active; per-specialist ceiling unchanged |
| Physical actions |45;5successful inference telemetry receipts |
| Typed feedback |2context /3JSON /1oversized read /2semantic validation /1phase restriction |
| E2E |350.104s |
| Initial placement, separate |115,726B /0.387s |
| Successful registered Agent movement |0B /0s; complete failed-inclusive movement unknown |
| Successful tool work |2.896s; complete tool work unknown |
| Inclusive successful model-action work |42.233s; includes backend service |
| Complete model service/tokens |Unknown because failed-call telemetry is absent |
| Returned successful model tokens |3,914input /1,230output;5stop receipts |
| Frozen list-price API cost |USD0.785616062; not invoice |
| Graph |45nodes /39artifact-flow edges /136snapshots /peak4 |

Terminal is a successful prompt-only model output,69input/2output/stop/service
0.278s; raw text equals canonical evaluated answer. No extra semantic finalizer
or benchmark retry. Evidence sufficiency, specialist utility, E-rule adoption
and causal quality/cost benefit are not established by these metadata. Complete
failed-inclusive traffic/service work must not be replaced by the successful
subtotals. Same frozen execution and schedule; next unexecuted cell36 is
LongBench4/Qwen/Fast/B0. Full192strict-inactive private/manual/failure/adoption
and quality-conditioned Q1-Q10 remain; no pooled scores or payload via the PC.

## Snapshot031 and feedback027 completed: thirty-four settled

2026-10-07 11:38HKT. Snapshot031 completed03:37:02Z, SHA
`4905f3d5a7b5a8a393f5ee7726cbaa7f5fb5acc1296301f58a7895bb96625e8c`:
34effective/34preserved/zero pending/four original findings retained/zero
effective confounders/zero operational exclusions. JournalSHA
`560aed6b9dc3007873c152df85ddc81eb0e3dc0fc03243b245c1412f6dc1429b`;
control002 and frozen schedule/execution004/collector unchanged. Successful
creator80130 must not be repeated; next snapshot032.

Feedback027SHA
`7c12fa80f3e5c9d6be1c7f61e360c8bd46f87cbfb468d37d71e1e3ba2a54e33e`
verifies550actual contexts:262Manager/262Verifier/26specialist,73B1profiles/
131A_Eledgers/60Efrozen-rule exact matches. Both role-specific original scans
and fixed Verifier/non-Manager feedback separation pass. Snapshot/feedback/
population/journal/control independently reverified03:38:48Z. Visibility does
not establish rule adherence, specialist utility, evidence coverage or causal
Ledger savings. Same006owned/live03:38:49Z before35 LongBench4/DeepSeek/Slow/E;
158remaining. All192strict-inactive private/manual/failure/adoption and final
quality-conditioned Q1–Q10/named reports remain unfinished. No new model calls,
support/corpus/store-body decoding or raw payload export. Older captures retain
historical scopes; no cross-benchmark score aggregation or old/new pooling.

## Cell34 settled: bounded specialist and generic reduction, originalscore1

2026-10-07 11:34HKT. LongBench4/Qwen/Slow/A attempt1 completed valid,
format-valid, originalscore1. Independent original admission/source/store/
residency/tc/exit/terminal/thirty-sixSDKcontext auditSHA
`fed47320bc169797c32693d9942166755fe4f78e1e3390c09fa7a65279f21dea`;
startupSHA `31c3c858cb965b64fca364bf0c6fcbe75ff3825fd8a714aaa1a5a67e36b4f83e`.
OriginaljournalSHA `560aed6b9dc3007873c152df85ddc81eb0e3dc0fc03243b245c1412f6dc1429b`.
34effective/34preserved/four reviewed original findings/zero pending;158remain.
Next35 LongBench4/DeepSeek/Slow/E; same006 queue, no retry or measured
model/prompt/budget/scheduler changes.

Fourteen Manager/fourteen Verifier/eight specialist turns; one created/peak-active
specialist, twenty-five physical actions. Observable sequence comprises two
four-action BM25 waves, four aggregates, two four-action top_k_records waves,
and five model requests interleaved with those operations. Four model requests
are context-preflight rejected (one specialist-owned), not inference; all have
static requirement matching=true and selection/inference=false. Terminal
request succeeds on A4VL4B:3,138input/2output tokens,stop,service8.706s,
one materialized input artifact; raw output equals the evaluated canonical label.
Two separate semantic-validation and one phase-restriction feedback are retained.

| Receipt-derived metric | Value / scope |
| --- | --- |
| E2E |182.654s |
| Complete registered Agent artifact movement |0B /0s; not all HTTP/RPC/prompt traffic |
| Initial placement, separate setup |115,726B /0.362s |
| Complete tool execution work |1.905s |
| Inclusive Worker model-action execution |8.888s; includes backend service |
| Complete backend model service |8.706s; one reached inference |
| Frozen list-price API cost |USD0.494152961; not an invoice |
| Execution-grown graph |25nodes /36artifact-flow edges /76snapshots /peak4 |

This is natural bounded-agent/reduction continuation with correct completion,
not manual repair or an extra cell. It does not prove evidence coverage, optimal
top-k pruning, specialist necessity or Ledger-induced savings. Comparing this
cell with33 changes Planner/network/method, so their latency/model-call difference
is not a clean method effect. Full192strict-inactive private/manual audit remains;
no new support/corpus/store-body decoding, audit model calls or raw payload export.

## Snapshot030 and feedback026 completed: thirty-three settled

2026-10-07 11:25HKT. Snapshot030 completed03:24:10Z, SHA
`5cd8cc16474bd79bbd397b42c16d89f26a0fef3d2222169e354f76016c81f1e0`:
33effective/33preserved/zero pending/four original findings retained/zero
effective confounders/zero operational exclusions. OriginaljournalSHA
`2ce5805f057f129cfef9fb730052ae190aaa66d34e6815d457d66f2925c038bd`;
original control002/schedule/execution004/collector unchanged. Successful
creator47167 must not be repeated; next snapshot is031.

Feedback026SHA
`be94061707306bf7c6878559798eeea3d28057e1778b89bf7ba7cedb921a96ab`
verifies514actual SDKcontexts:248Manager/248Verifier/18specialist,
73B1profiles/117A_Eledgers/60Efrozen-rule exact matches. Fixed Verifier and
non-Manager feedback exclusion pass. Snapshot/feedback/population/journal/
control independently reverified03:25:32Z. Visibility does not prove profile
adoption, semantic coverage, repeated-verification necessity or causal benefit.
Unknown failed-read transfer/tool work in cell33 remains unknown. No new model
calls, support/corpus/store-body decoding or raw payload export. Same006owned
live03:25:33Z before34 LongBench4/Qwen/Slow/A;159remaining. Full192strict-
inactive private/manual/failure/adoption and final quality-conditioned Q1–Q10/
named reports remain. Earlier captures retain historical scope; no score pooling.

## Cell33 settled: LongBench natural continuation, originalscore1

2026-10-07 11:20HKT. LongBench4/DeepSeek/Fast/B1 attempt1 is valid,
completed, format-valid, originalscore1. Independent original admission/source/
store/residency/tc/exit/terminal/twenty-twoSDKcontext auditSHA
`3032aa91bc7b8031e52c4d02582f28904b0890ac092c6d54c762b9f9d880f593`;
startupSHA `53a5ffaaf030bf90c037d31ef97ee9063b0bbdeaa8e5721c604ffe2ca3ce7757`.
OriginaljournalSHA `2ce5805f057f129cfef9fb730052ae190aaa66d34e6815d457d66f2925c038bd`.
33effective/33preserved/four reviewed original findings/zero pending. Next
scheduled34 LongBench4/Qwen/Slow/A;159remaining. No ordinary retry, semantic
tuning, model/prompt/budget/scheduler change or extra semantic finalizer.

Eleven Manager/eleven Verifier turns, twenty physical actions, no specialists.
Initial oversized read is rejected; three waves of four BM25 actions interleave
with two context-preflight-rejected model requests. Then two successful model
actions, two successful reads, and a successful terminal model action. Exact
prepared sequence is preserved in trace. Three successful A4VL4B inferences:
4,477in/2out/12.368s;4,529in/599out/78.005s;1,154in/2out/3.191s;
all finish_reason=stop. Two context rejects are not inference. Terminal consumes
one materialized artifact and raw text equals the evaluated canonical choice.
One separate SDK phase-restriction feedback is preserved.

Independent model-outcome readback confirms both context failures have
`static_feasible=true`, `physical_selection_succeeded=false`,
`reached_model_inference=false`; all three successes have all three flags true.
Here static_feasible matches declared semantic requirements to an abstract
class; it does not certify the combined artifact/prompt context envelope. The
rejections therefore must not be relabeled as reached inference or evidence of
dynamic deployment unavailability. No new backend calls in this readback.

| Receipt-derived metric | Value / scope |
| --- | --- |
| E2E |228.804s |
| Successful registered Agent transfers |0B /0s; complete failed-action-inclusive movement unknown |
| Initial placement, separate setup |115,726B /0.039s |
| Successful tool execution work |0.979s; complete work unknown due failed read |
| Inclusive successful Worker model-action work |93.835s; includes backend service |
| Complete backend model service |93.565s across three successful inferences |
| Successful physical model tokens |10,160input /603output |
| Frozen list-price API cost |USD0.282574262; not an invoice |
| Execution-grown graph |20nodes /15artifact-flow edges /61snapshots /peak4 |

One failed read has no complete execution work/transfer receipt, so complete
Agent movement and tool work remain unknown, not zero. Registered movement
does not include all HTTP/RPC/control/prompt traffic. Correct completion proves
normal recovery from typed failures, not evidence retention, necessity of all
queries/repeated reasoning, actual profile adoption or causal cost benefit.
These await full192strict-inactive private/manual audit. No new audit model
calls, support/corpus/store-body decoding or raw payload export.

## Snapshot029 and feedback025 completed: thirty-two settled

2026-10-07 11:11HKT. Snapshot029 completed03:10:17Z, SHA
`7d65363ef2bc3c7885e80b70b39737252c4a8d175700960a95389425355786b6`:
32effective/32preserved attempts/zero pending/four original findings retained/
zero effective confounders/zero operational exclusions. OriginaljournalSHA
`6a17eb35de0238adfb7c1c11c23277bb7155be35ac812550fe31321e27ae396b`;
control002 and schedule/execution004/collector remain frozen. Successful
creator1474 must not be repeated; next snapshot is030.

Feedback025SHA
`a78f173b77bee73865bc1f21c930d50c9dfe0e9f0fe9299c8afa2e594cb6315b`
verifies492actual SDK contexts:237Manager/237Verifier/18specialist,
62B1profiles/117A_Eledgers/60Efrozen-rule exact matches. Fixed Verifier and
non-Manager feedback separation pass. Snapshot/feedback/population/journal/
control bindings independently reverified03:11:07Z. Cell32score0 remains a
valid original evaluator outcome, not missing evaluation or harness failure.
No new model calls, private support/corpus/store-body decoding or raw payload
export. Feedback visibility does not prove adoption, semantic coverage or causal
cost benefit. Same006controller/supervisor verified live03:11:09Z, before
scheduled33 LongBench4/DeepSeek/Fast/B1. Remaining160 and all192strict-inactive
private/manual/failure/adoption plus final quality-conditioned Q1–Q10/named
reports remain. Older live/startup/snapshot captures retain historical scope.

## Cell32 settled: compact visual workflow, valid execution but score0

2026-10-07 11:06HKT. Video3/DeepSeek/Fast/A attempt1 completed valid and
format-valid, with original evaluator score0. Independent original admission/
source/store/residency/tc/exit/terminal/sixSDKcontext auditSHA
`1b5b9b9fb54ff504d9ad53bae609fb1aec93ea4537833a21e90b4f8da9cf25d8`;
startupSHA `101233e06cc158a36067ed776703ec4e9bf31423def9479a411c859d17322628`.
JournalSHA `6a17eb35de0238adfb7c1c11c23277bb7155be35ac812550fe31321e27ae396b`.
32effective/32preserved attempts/four reviewed original findings/zero pending.
Next scheduled33 is LongBench4/DeepSeek/Fast/B1;160remaining. Same006queue,
no cell retry, prompt/model/budget/scheduler changes or extra semantic finalizer.

Three Manager/three Verifier turns, three physical actions, no specialists:
`sample_frames → make_contact_sheet → invoke_model`. Terminal A4VL4B consumes
one visual contact-sheet artifact; 1,416input/2output tokens, stop, service7.450s.
Raw terminal text already equals the declared canonical choice evaluated.
No context/preflight rejection or recorded SDK failure feedback.

| Receipt-derived metric | Value / scope |
| --- | --- |
| E2E |48.234s |
| Complete registered Agent artifact movement |0B /0s; not all HTTP/RPC/prompt traffic |
| Initial video placement, separate setup |15,239,623B /1.355s |
| Complete tool execution work |2.362s |
| Inclusive Worker model-action execution |7.563s; includes backend service |
| Complete backend model service |7.450s |
| Frozen list-price API cost |USD0.095980246; not an invoice |
| Execution-grown graph |3nodes /17artifact-flow edges /10snapshots /peak1 |

This is a valid quality failure, not unevaluated=0 or a runtime failure. Compact
information flow plus low resource work does not establish a quality-preserving
optimization. Contact-sheet evidence loss, semantic reasoning failure, stopping
adequacy and ledger adoption/causality remain unresolved until post-block
private/manual audit. Cell32 versus prior31 or30 changes more than one factor;
no isolated network/method causal conclusion. Preserve all raw evidence and
the score0; do not tune or replace the task. No new audit model calls or private
support/corpus/store-body decoding/raw payload export.

## Snapshot028 and feedback024 complete: thirty-one settled

2026-10-07 11:00HKT. Snapshot028 completed at02:59:43Z, SHA
`9c272b63fe737ce805ad7c073d7ecfb3e91332bb43c3378146f4df9f5b12ccf3`:
31effective/31preserved attempts/zero pending/four original findings retained/
zero effective confounders/zero operational exclusions. JournalSHA
`7ad0eba9dfc8f1a4723a18b0060798528b3002d316e5c65c13a353f2d013d43f`.
Original control002, frozen schedule/execution004 and collector remain unchanged.
The first028collector exited before writing on journal advance; successful
read-only recollection29198 must not be repeated. Next snapshot is029.

Feedback024SHA
`2788d349b7176a820cc47926c3be2bbcceeddf038cb401125cd0ff0e2db17a19`
verifies486 actual provider contexts:234Manager/234Verifier/18specialist,
62B1profile/114A_Eledger/60Efrozen-rule exact matches. Fixed Verifier and
non-Manager feedback exclusion pass. Snapshot/feedback hashes, population,
journal and control binding independently reverified at03:00:33Z. These audits
make no new model calls and read no new support/corpus/store bodies or gold;
raw requests remain owner-local. Visibility does not prove adoption, retention
or causal cost benefit. Next feedback is025, only after a new successful snapshot.
Same006controller/supervisor remains owned/live before32. Remaining161 and
all full192 strict-inactive private/manual/failure/recipient/adoption and final
quality-conditioned Q1–Q10/named reports remain unfinished. Old27/29 scopes
below remain historical; no old/new experimental population pooling.

## Cell31 settled: Qwen/Slow/E with natural context continuation

2026-10-07 10:56HKT. Video3/Qwen/Slow/E attempt1 is valid, completed,
format-valid, original evaluator score1. Independent admission/source/store/
residency/tc/exit/terminal/fourteenSDKcontext auditSHA
`3309b2371a7910292ea26217a475ad49537fcaff2b145e1ef1bba507ad46b6f5`;
startupSHA `09915d4bd718081d8ce57a55862ea4e15f341196593dce7408aca9f38375b04f`.
Original journalSHA `7ad0eba9dfc8f1a4723a18b0060798528b3002d316e5c65c13a353f2d013d43f`.
31effective/31preserved attempts/four original reviewed findings/zero pending.
Same006 queue continues to scheduled32 Video3/DeepSeek/Fast/A; 161 remain.

Seven Manager/seven Verifier turns, six physical actions, no specialists:
`sample_frames → context-rejected invoke_model → extract_clip → sample_frames
→ invoke_model → terminal invoke_model`. One context preflight rejection is
not inference; one separate SDK phase-restriction feedback is preserved. Two
successful A4VL4B inferences:4,503/4,498input tokens,2/2output tokens,
both finish_reason=stop, service25.069s/24.318s. Terminal consumes four image
artifacts and its raw text already equals the evaluated canonical choice.

| Receipt-derived metric | Value / scope |
| --- | --- |
| E2E |172.100s |
| Complete registered Agent artifact movement |0B /0s; not all HTTP/RPC/prompt traffic |
| Initial video placement, separate setup |15,239,623B /42.598s |
| Complete tool execution work |1.291s |
| Inclusive Worker model-action execution |49.635s; includes backend service |
| Complete backend model service |49.386s |
| Frozen list-price API cost |USD0.275954318; not an invoice |
| Execution-grown graph |6nodes /25artifact-flow edges /19snapshots /peak1 |

Natural continuation is not cell replacement or manual semantic repair. E-rule
visibility/adherence, sampling sufficiency, repeated-inference necessity and
method causality require the deferred post-block audits; correctness alone
does not prove these. Comparing cell31 with cell30 changes both Planner and
method; it is not a clean isolated method contrast. No new prompt/model/budget/
scheduler change, raw payload export or private support/corpus/store-body read.

## Cell30 settled: resource-blind Video under Slow

2026-10-07 10:49HKT. Cell30 Video3/DeepSeek/Slow/B0 attempt1 is valid,
completed, format-valid and original evaluator score1.0. Independent auditSHA
`c7bbbf52531e41e1542ab502a46243330e913de633be15eb7df67c4ae619bf97`;
startupSHA `92b6c1d1c91317ce2f53d19ddea996baae46be3b9d9494abb5f7495c3a79241c`.
Original journalSHA at readback:
`62de720864acbc9970c2bdef44e96ada31464270d369ae21b97638e6c55f980c`.
Thirty effective/thirty preserved attempts/four original reviewed findings/
zero pending at capture. Same006 queue continues; next scheduled cell31 is
Video3/Qwen/Slow/E. No ordinary retry or prompt/model/budget/scheduler change.

Three Manager/three Verifier turns, two physical actions, no specialists:
`sample_frames → invoke_model`. The A4 visual model consumes seven image
artifacts; 7,849 input/15 output tokens, finish_reason=stop, service45.900s.
Evaluated answer is exactly the frozen deterministic choice projection of the
successful terminal model text; raw text itself is not the canonical label.
No context rejection; one separate SDK phase-restriction feedback remains.
Resource-blind trace records zero dynamic-profile feedback events. Six actual
SDK contexts pass the original recipient scan.

| Receipt-derived metric | Value / scope |
| --- | --- |
| E2E |131.161s |
| Complete registered Agent artifact movement |0B /0s; not all HTTP/RPC/prompt traffic |
| Initial video placement, separate setup |15,239,623B /42.603s |
| Complete tool execution work |2.242s |
| Inclusive Worker model-action execution |46.070s; includes backend service, not extra work |
| Backend model service |45.900s |
| Frozen list-price API cost |USD0.112917901; not a billing invoice |
| Execution-grown graph |2nodes /7artifact-flow edges /7snapshots /peak1 |

Seven graph edges are artifact information flows, not seven separate branches.
Score1 does not establish temporal sampling sufficiency. This cell and previous
Fast/Qwen/B1 cell29 vary both Planner and method as well as network: their E2E
difference is not a matched network/method causal effect. Full192 strict-inactive
private/manual evidence and quality-conditioned analysis remain outstanding.

## Snapshot027 and feedback023 completed:29settled

2026-10-07 10:39HKT. Snapshot027 completed at02:38:19Z, SHA256
`30439eb3c0608653aabaf1e3b2faf972772f7edfd501c4b65928d7a983cfe112`:
29effective/29preserved attempts/0pending/4original findings retained/
0effective confounders/0operational exclusions. Original journal remains
`17d101d215625cba64398a6130d31ac0c2381124e99d40aa9d48a8d613e4ed10`.
Control002 and frozen schedule/execution004/collector source remain unchanged.
Successful creator40264 must not be repeated; next snapshot is028.

Feedback023SHA
`7785cc4c849efc33c08d4f7ddf4a8579b068e7d0159c196d7465398606ed3c16`
matches466actual contexts:224Manager/224Verifier/18specialist,62B1profile/
107A_Eledger/53Efrozen-rule inputs. Snapshot/cell29audit/feedback hashes and
same-population/journal bindings independently reverified. Fixed Verifier and
non-Manager feedback exclusion remain valid; visibility does not prove semantic
coverage, retention, rule adherence or causal cost benefit. At02:39:35Z same006
supervisor/controller remain owned/live, before cell30 Video3/DeepSeek/Slow/B0.
Remaining163and all full192strict-inactive private/manual/failure/adoption,
quality-conditioned Q1–Q10/named final reports remain unfinished. No new model
calls, support/corpus/store-body decoding or raw payload export. Older pending
projection captures below retain historical scope.

## Cell29 settled: original Video evaluator reached

2026-10-07 10:35HKT. Video3/Qwen/Fast/B1 attempt1 is formally valid,
completed, format-valid and original evaluator score1.0. Independent original
admission/source/store/residency/tc/exit/direct-terminal/sixSDKcontext auditSHA
`2d5ee6b0786a7a2140c2cb3a06c636b1da963935a2d6cc4e07ff37eadc7a2278`;
startupSHA `36831faf695da9fc05016a20d7d320bd2eff4780ab9df6aa2df1cd0540d0ea2b`.
Raw journalSHA
`17d101d215625cba64398a6130d31ac0c2381124e99d40aa9d48a8d613e4ed10`;
29effective/29preserved attempts/4original reviewed findings/0pending at capture.
No ordinary retry or measured model/prompt/budget/scheduler/contract alteration.

Three Manager/three Verifier turns, two physical actions, no specialists:
`sample_frames → invoke_model`. A4VL4B terminal inference consumes siximage
artifacts,6,699actual input/2output tokens,finish_reason=stop,service37.683s.
The raw terminal text already equals the canonical choice answer. No context
rejection; one separate SDK phase-restriction feedback is preserved. Neither
score1 nor the small workflow proves full temporal evidence sufficiency or a
causal benefit of the threepredecision profiles; that audit remains deferred.

| Receipt-derived metric | Value / scope |
| --- | --- |
| E2E |73.223s |
| Complete registered Agent artifact movement |0B /0s; not zero HTTP/RPC/prompt traffic |
| Initial video materialization, separately |15,239,623B /1.364s |
| Tool execution work |2.133s |
| Inclusive Worker model-action work |37.776s; includes backend service |
| Frozen list-price API cost |USD0.119300; not an invoice |
| Graph |2nodes /6artifact-flow edges /7snapshots /peak concurrency1 |

Same006continues before cell30 Video3/DeepSeek/Slow/B0;163outcomes remain.
Snapshot027creator40264 is in progress, not yet a completed projection;
snapshot026/feedback022 retain their28settled scope. No new model calls,
support/corpus/store-body decoding or raw payload export in metadata audits.
Full192and strict-inactive private/manual/failure/adoption/Q1–Q10 remain.
Earlier live-cell29/no-result captures are historical.

## Snapshot026 and feedback022 completed:28settled

2026-10-07 10:29HKT. Snapshot026 completed at02:28:15Z, SHA256
`7ae450a920ec407b346160943527f3566842cf8422ac903c6d871d09ff26c667`:
28effective/28preserved attempts/0pending/4original findings retained/
0effective confounders/0operational exclusions. Original journal remains
`cbc590248d229f1c787c4f31f7a694b71fd2b46fa53f02190fdff046813926e9`.
Control002 and the frozen schedule/atomic004/collector source are unchanged.
Successful snapshot creator42339 must not be repeated; next snapshot is027.

Feedback022SHA
`f0d26562cf6539be1fd8cb1205c8ebdd459bb3631d77b0654e92d9f7fbebae19`
verifies460actual contexts:221Manager/221Verifier/18specialist,59B1profile/
107A_Eledger/53Efrozen-rule matches. Snapshot/cell28audit hashes and feedback's
same-population/same-journal bindings were independently reverified. Fixed
Verifier and non-Manager feedback exclusion remain valid; visible feedback is
not proof of causal adoption, semantic coverage or quality-preserving savings.
At02:29:32Z same006supervisor/controller are owned/live, before next cell29
Video3/Qwen/Fast/B1. Remaining164and all full192post-block audits/Q1–Q10 remain.
No new model calls, support/corpus/store-body decoding or raw payload export.
Older snapshot-in-progress captures below retain their historical scope.

## Cell28 settled: valid completion, original score1

2026-10-07 10:26HKT. MultiHop3/DeepSeek/Fast/A attempt1 is formally valid,
completed and format-valid with original evaluator score1.0. Independent
admission/source/empty-store/residency/tc/Worker-exit/direct-terminal/14actual
SDKcontext auditSHA
`b6f7285848ee9d44e0450a3c08128d2005ac4305504908d0b7f90e096751dc2c`.
Raw journalSHA
`cbc590248d229f1c787c4f31f7a694b71fd2b46fa53f02190fdff046813926e9`;
28effective/28preserved attempts/4original exact-reviewed findings/0pending
at this capture. No ordinary retry or measured behavior change.

Seven Manager/seven Verifier turns,13physical calls, no specialists. Sequence:
three BM25 → context-rejected model → six BM25 → two reads → successful terminal
model. Terminal selection is4090GPU0/qwen35, with225actual input/6output tokens,
finish_reason=stop and0.463sbackend service. Its logical action has0direct artifact
inputs; this does not prove absence of inline evidence or adequate retention.
One context rejection is not an inference; separate SDK feedback records one
semantic-validation and three phase-restriction failures. Semantic sufficiency
and causal ledger contribution await the full strict-inactive private audit.

| Receipt-derived metric | Value / scope |
| --- | --- |
| E2E |83.284s |
| Complete registered Agent artifact movement |0B /0s; not zero HTTP/RPC/control/prompt traffic |
| Initial materialization, separately |7,696,522B /0.815s |
| Tool execution work |4.139s |
| Inclusive Worker model-action work |0.465s, not additional backend service work |
| Frozen list-price API cost |USD0.165243; not an invoice |
| Graph |13nodes /5edges /40snapshots /peak concurrency6 |

Same006continuation remains; next cell29 Video3/Qwen/Fast/B1,164outcomes remain.
Snapshot026creator42339 is in progress, not yet a completed projection. Latest
finished snapshot025/feedback021 still cover27settled outcomes; they are not
silently extended. No support/corpus/store-body decode, new audit model call or
payload export. All192and final private/manual/failure/adoption/Q1–Q10 remain.
Earlier live-cell28 and snapshot025 captures retain historical populations.

## Cell28 live; settled population remains27

2026-10-07 10:23HKT. MultiHop3/DeepSeek/Fast/A attempt1 atomic2622426 is
owned/live under the same006controller. Startup receiptSHA
`03428e20c4b6905f2266177bcdf0886369bf33943f1a407d09a4507cdc46694f`
independently proves four empty Worker stores, five resident instances and
source004-only atomic imports. No terminal result/score is yet available.
Twenty-seven valid settled outcomes plus one pending attempt do not establish
28completions. Snapshot025/feedback021 retain their27settled scope, and165
unresolved outcomes include this active cell. No retry, model/prompt/budget/
scheduler change, private corpus/store-body decode or raw payload export.

## Snapshot025 and actual feedback021 completed:27settled

2026-10-07 10:19HKT. Snapshot025 completed at02:18:20Z, SHA256
`4e0940f88387f8152124141be16df8b88f8e3d5848a2c72e3318507e332d4d93`:
27effective/27preserved attempts/0pending/4original findings preserved/
0effective confounders/0operational exclusions. Original journal remains
`67dd1d59ec084c3032f59f69bdd46badb425e9ca3dd34458e1919f63b802807f`.
Control002, original schedule/execution and collector source remain unchanged.
Successful creator37776 must not be repeated; next snapshot is026.

Feedback021SHA
`3b162765e0cb3216f0d29c7b1bf5cb63f4ffb28f03f88b73d517424b1fed658a`
matches446actual provider contexts:214Manager/214Verifier/18specialist,
59B1profiles/100A_Eledgers/53Efrozen-rule inputs. All three new receipt hashes
(snapshot, feedback and cell27audit) were independently read back at02:19:04Z.
Feedback exclusion for non-Manager recipients and fixed Verifier remain valid;
visibility does not prove adoption, semantic retention or causal cost benefit.
No new model calls, private support/corpus/store-body decoding or payload export.
Full192and strict-inactive audits/Q1–Q10 remain incomplete. The earlier
snapshot025-in-progress and live-cell27 captures retain historical scope.

## Cell27 settled: valid completion after natural context recovery

2026-10-07 10:16HKT. MultiHop3/Qwen/Slow/E attempt1 is formally settled valid,
completed, format-valid and original evaluator score1.0. Independent original
admission/source/store/residency/tc/Worker-exit/direct-terminal/recipient audit
SHA `559fb33e9b08c4e01898afaa74895e5c4c44da6b6d1cb18e18a79fa477789606`.
Original journalSHA
`67dd1d59ec084c3032f59f69bdd46badb425e9ca3dd34458e1919f63b802807f`;
27preserved attempts,27effective outcomes,4original exact-reviewed findings,
0pending at this capture. No repeated attempt or semantic tuning.

Seven Manager/seven Verifier turns, eight physical actions, no specialists.
Sequence: three cross-shard BM25 actions → one context-preflight rejection →
three further BM25 actions → successful A28 terminal model consuming three
artifacts. Actual model usage4,747input/6output tokens, finish_reason=stop,
service82.838s. The rejected request is not an actual inference. Separate SDK
feedback contains one semantic-validation and one phase-restriction failure.
Natural continuation is observed; semantic coverage/retention and rule-specific
causal contribution remain unknown pending the strict-inactive post-block audit.

| Receipt-derived metric | Value / scope |
| --- | --- |
| E2E |169.330s |
| Complete Agent artifact movement |11,978B /0.724s |
| Initial materialization, separately |7,696,522B /22.033s |
| Tool execution work |2.482s |
| Inclusive Worker model-action work |82.927s; includes backend service, do not double-count |
| Frozen list-price API cost |USD0.135557; not an invoice |
| Graph |8nodes /6edges /25snapshots /peak concurrency3 |
| Actual SDK contexts covered by original admission |14 |

Continuation006 remains active before next frozen cell28 MultiHop3/DeepSeek/
Fast/A;165outcomes remain. Snapshot025creation is in progress, not yet claimed
completed; successful snapshot024/feedback020 remain their original26-cell
population. No new support/corpus/store-body decoding or payload export.
All192and private/manual/failure/recipient/adoption/Q1–Q10 remain unfinished.
Earlier live-cell27/no-result captures below are historical.

## Live cell27; completed population still26

2026-10-07 10:13HKT. Same006 supervisor2562900/controller2562901 and atomic
2599888 are owned/live for MultiHop3/Qwen/Slow/E attempt1. Startup receiptSHA
`21169d125de0ef08a2d9d7a29b607f566e17cd9b17feea73522ec1fa459574d0`
proves four initially empty Worker stores, five resident instances and source004
only in atomic PYTHONPATH. No repeated completed cell or model/prompt/budget/
scheduler change. At02:13:44Z six BM25 actions and one context-rejected model
request are prepared; Manager has naturally continued. No final result or
score is available, so do not add this reservation to the26settled outcomes.
Snapshot024/feedback020 below retain their settled26 scope. Remaining166
includes this active cell; full192 and post-block audits are still required.
No private support/corpus/store-body decoding or raw payload export occurred.

## Snapshot024:26effective; actual006 is running

2026-10-07 09:58HKT. Immutable snapshot024 at01:56:56Z has26admitted/
26attempts/0pending/4original raw findings preserved/0effective confounders.
SnapshotSHA `fa41a7adae9a8f7d7bc3149cbdb042c9beb6000585e9c6b6abaa95cd89a7f13c`;
journalSHA `2be72457913f15e36c79d64dcefcc6092713c626a72d9d61219296ca0eadfb33`.
Its source is the completed disjoint exact-review control002; old answer/score/
admissions and unknown failed telemetry remain unchanged. No result pooling or
score aggregation is performed.

Feedback020 independently matches432 actual provider contexts:207Manager/
207Verifier/18specialist,59B1profiles/93A_Eledgers/46Efixed-rule inputs.
SHA `0003f4a6cc4f5101ebd9d340d450a6adf588e1cf8eb8250c1c84fb0b3fcd4e9c`.
Non-Manager feedback exclusion/fixed Verifier/original recipient scans pass;
visibility does not establish semantic adequacy or causal adoption. No new model
calls, support/corpus/store-body decoding or raw payload export.

At01:58:07Z supervisor2562900/controller2562901 remain owned/live, no exit or
new reservation; first unstarted27=MultiHop3/Qwen/Slow/E. Remaining166and all
full192strict-inactive private/manual/failure/adoption/Q1–Q10 audits remain.
Successful snapshot024/feedback020 creators must not be repeated. Earlier
pending-projection or stopped005captures below are historical.

## Actual continuation restored;26effective outcomes

2026-10-07 09:56HKT. Exact cell26review and full original gate/control002
verification finished successfully. ControlSHA
`349db3f5aa57983630a34d7a17e68f353cbf5084f75c8f7c79b41a63d8e5276a`;
validationSHA `be59a1b4eb6248b5407a6103f3fc0f20aece5a39338dc87d959f4e87a46e94c1`.
Twenty-six effective/26preserved/4original findings/0pending at this capture,
no original journal, answer, score or failed telemetry modification. Model JSON
case26 is retained as natural recovered noncompliance, not rerun.

New006supervisor2562900/controller2562901 owned/live at01:56:32Z, no exit or
next reservation. Actual launchreceiptSHA
`55fb5aec077c40d17838a69f21ed685a631542b612ed4f55c2f3758118409a58`.
First unstarted27=MultiHop3/Qwen/Slow/E; remaining166. Original global private
guard demonstrably rejects this live controller (receipt3e35f886...), no body
read. Snapshot024 is being collected under002control, not claimed finished yet.
No duplicate launch, ordinary retry, new method or measured behavior change.
All192and post-block audit requirements remain. Older stopped captures below
are historical; the table's earlier scoped snapshots remain unchanged.

## Latest:26 original outcomes,25effective pending exact JSON review

2026-10-07 09:35HKT. Controller005 exited1 after cell26; no27reservation.
The cell completed/formatvalid/originalscore1, but its sole original admission
gate is one source-proven post-backend model JSON failure. Durable exact review
and combined control002 are still being created. Do not count26effective or
infer a queue restart from passing repair tests. The earlier25-cell snapshot
and its population remain immutable. Original journalSHA
`2be72457913f15e36c79d64dcefcc6092713c626a72d9d61219296ca0eadfb33`:
26rawattempts/4original findings/0pending;25effective under existing reviews.

Cell26 MultiHop3/DeepSeek/Slow/B0:10Manager/10Verifier,8specialist turns,
1created specialist,25physical requests. Six preflight context rejects and
one invalid JSON after backend completion precede the final successful model;
terminal consumes2artifacts,6,563input/6output tokens,stop. E2E446.769s,
successful Agent movement59,044B/1.210s; complete failed traffic and complete
model-service work unknown. Initial7,696,522B/22.651s remains separate.
Returned successful model-action work113.546s is not added to backend service.
Graph25nodes/32edges/76snapshots, peak actual concurrency6. API frozen-list-price
USD0.495492, not an invoice. Natural recovery is not benchmark retry or proof
of sufficient evidence retention; no quality/cost causal claim.

Independent original admission/source/residency/stores/tc/Workerexit/direct
terminal and28SDKcontexts auditSHA
`1aaf2990c59e6a5020a2628c2608ad307f57497f97934b5bbe2e5a6fa81de5e9`.
The [external ancestor compatibility repair](large-scale-resident-phase2-field-review-v1.md)
changes no Agent/model/prompt/budget/runtime/scheduler behavior or old evidence.
Full1821pytest/7skips, Ruff/strictPyright and47actual Linux tests pass. Actual
durable control freeze remains in progress; continue only27–192 once verified.
All192and strict-inactive full-block audits/Q1–Q10 remain incomplete.

## Snapshot023:25 settled outcomes (2026-10-07 09:18 HKT)

Immutable owner-local snapshot023 at01:18:19Z has25admitted/25attempts,
0pending/0effective confounders/3original rejections preserved. SHA
`b054749dabdecfac32d4856112899825cb63ec33a0deb2519c71f7b73923de95`;
journalSHA `5fd11863ef4da7861d6b3eb39808348eb42766fb976c7847ed524d7621b95c3e`.
Controller005/supervisor2434640/2434639 are independently owned/live at01:18:38Z.
The next frozen cell is MultiHop3/DeepSeek/Slow/B0; no reservation yet at
that capture.167outcomes and all post-block private/manual audits remain.

Cell25 MultiHop3/Qwen/Fast/B1 completes with valid format/originalscore1:
six Manager/six Verifier turns, no specialists, eight physical requests.
Three parallel per-shard BM25 actions, one context-rejected model request,
three further BM25 actions and one successful model request form the observed
trajectory. Terminal model consumes three artifacts on A28/resident27.3B:
7,074input/6output tokens, stop,123.202s service. One additional semantic
validation and one phase restriction SDK receipt are separate. No manual
recovery, prompt tuning or repeated benchmark run.

E2E179.709s; complete registered Agent transfer18,036B/.605s, separately
initial7,696,522B/.951s. Successful tool work2.446s; inclusive Worker model
work123.291s is not added to backend service. API frozen-list-price cost
USD0.101177 is not an invoice. Graph8nodes/6edges/25snapshots, peak actual
concurrency3. Natural reduction/context recovery is observed; quality1 and
profile visibility do not establish evidence retention or causal optimization.

Independent original-admission reproduction, journal binding, empty stores,
five resident identities, restored tc, Worker exits, direct model terminal and
12SDKcontexts pass: cell25auditSHA
`947e215c621a74cbe7bda73743e18b0b60eafe496d73fdb7d20ee62b38276660`.
Cell24 independent original-admission audit also passes, preserving score0,
SHA `c8e621ac8a35cf1d54c0e6f0ac3567eea49814396b2d1c7ab3b0e27f76fef781`.
Feedback019 audits404contexts=197Manager/197Verifier/10specialist,
59profile/93ledger/46rule matches; SHA
`b5aa844b48b994a276db6d6c3a70b7fc11917a436ae915b299ccb89a599c773d`.
No new model calls, private-body scans or payload export; older captures below
retain their original populations and liveness scopes.

## Current snapshot022:24 settled; next cell live (2026-10-07 09:12 HKT)

Owner-local immutable snapshot022 at01:10:43Z records24admitted/24attempts,
0pending/0effective confounders/3preserved raw rejections. SHA256
`eadec1fc6d34c06e14f4a78ee3446e8029d416f810123056719cf8c13464baf2`;
journalSHA `4e01dec8b63e8cea2203a1edd4cad11037bde495a4cb97333e5be897102e6a87`.
Controller005 is running under the newly frozen disjoint review control;
01:12:42Z monitor confirms owned supervisor2434639/controller2434640 and
pending cell25atomic2480233. A subsequent reservation is not part of this
snapshot's settled count. Remaining168 outcomes include this active cell.

| Additional settled cell | Completion / format / original score | Manager / Verifier | Physical / returned inference | E2E, s | Initial bytes / seconds | Agent transfer bytes / seconds |
| --- | --- | --- | --- | --- | --- | --- |
|23 MultiHop6 / DeepSeek / Slow / E |true / valid /1 |10 /10 |13 /1 |155.267 |7,696,522 /22.117 |Successful0 /0; complete failed traffic unknown |
|24 MultiHop6 / Qwen / Fast / B0 |true / valid /0 |7 /7 |5 /1 |120.261 |7,696,522 /.771 |5,204,596 /.909 |

Cell24 follows aggregate_artifacts, BM25, context-rejected model request,
BM25, then successful model inference on A28:4,137input/4output tokens,
stop,72.534s backend service. One separate semantic-validation and one
phase-restricted SDK feedback are recorded. Graph5nodes/4edges/16snapshots;
no specialists, maximum actual concurrency1. Original admission is valid,
with no operational or recipient findings. Quality0 remains a valid negative
sample; no replacement or prompt tuning. Frozen-list-price API cost is
USD0.085285, not an invoice. Inclusive Worker model-action work is not added
to backend service work. Specific semantic failure remains for post-block audit.

Feedback018 verifies392 actual contexts:191Manager/191Verifier/10specialist,
53profile/93ledger/46rule matches; SHA
`4bbbf57909c155421918076d1a2f39bb3be64e201d088eaab44e9e99c7b1d2ff`.
All192 and inactive private/manual failure/adoption audits remain incomplete.
Older captures and the historical22-row table below retain their own scope.

Latest durable review:23effective/23preserved attempts/3raw confounders/
0effective confounders/0pending. Cell23's original score1/completion/format are
unchanged; its exact field sidecarSHA is
`e7f503553c51012ee2a9918b27535bb5f758fdb82f3e327fcb0b738b4c6f4e82`,
validationSHA `3f6cf22237f288dd260ff43b67731b9efa4e43146cb4e94a44782dc484445aed`.
JournalSHA `354cbe03899c906aae7b5de6050ee1311dde61becbd6fca4ae084d869c13de4e`.
Queue remains stopped; only the new combined continuation/control projection
is being frozen, not a new Agent/method/experiment configuration. Snapshot022
and feedback018 have not yet been created. Full192 and post-block audits remain
incomplete; the historical table below remains the prior22-cell snapshot scope.

Current at2026-10-07T00:29Z: queue004 exited after cell23, not live.
Cell23 completed/format-valid/original score1 but its raw field-validation gate
awaits durable source-bound review. Effective membership is still22; do not
append an unreviewed cell to the admitted table or run cell24 yet. The new exact
[field review](large-scale-resident-phase2-field-review-v1.md) documents original
telemetry, actual schema-wire proof, hash-identical historical shape reuse and
passing tests. No benchmark retry, Agent/model/prompt/budget/scheduler change or
new corpus/store-body scan. The following snapshot021 is a historical22-cell
capture, not an assertion that controller004 remains live.

Latest reviewed snapshot021 at2026-10-06T23:56:38Z:
22effective valid/22attempts/0pending/2preserved raw confounders/0exclusions.
SHA256 `6dec958ee318ab44d38377a262c1918f52c906a5352a1bc82b92ee1f89741883`;
journal `20a35ba16e047302c0d803ce65b62045424fd1d25414ddfd0163289e95d9df2d`.
The table now includes22 settled original outcomes. Old captures below are
historical, not current counts. No score pooling, retry or semantic tuning.

Cell22 MultiHop6/Qwen/Slow/A completed, format valid, original score1.0.
Original admission/journal, empty stores, resident identities, Worker exits,
tc restoration/direct terminal model and18SDKcontexts independently pass;
auditSHA `a03a5385ac2d4580b65a3b620f40a277a8e060820d246bcf018a9abd5390e788`.
Nine Manager/Verifier turns, no specialist, eight physical requests: three BM25,
one context-rejected model request, three filter_records and a successful model
request. One semantic-validation and two phase-restricted SDKcalls are separate.
Terminal model consumes one artifact on A4/resident-a4-vl4b-v1:
7,417input/4output tokens, stop,21.811s backend service. No retry/manual recovery.
Complete registered Agent artifact transfer0B/0s excludes HTTP/control/prompt
traffic; initial7,696,522B/22.033s is separate. Successful tool work1.546s,
inclusive model-action Worker work21.911s must not be added to backend service.
Graph8nodes/7edges/25snapshots/peak2, E2E98.339s, API listpriceUSD.124987.
Terminal one-artifact consumption and weak score1 do not establish full evidence
coverage or retention. Cell21 differs in Planner, method, network and selected
physical model weights (A28Qwen3.5 vs A4Qwen3-VL); its latency difference cannot
be credited to network or ledger alone. No pool or scheduler modification.

Feedback017 audits358actual contexts=174Manager/174Verifier/10specialist,
53B1profiles/83A_Eledgers/36frozenrules exactly matching provider requests.
SHA `04affebf388e4663fa837b37f266afe4fed63855101bd986a6347dc6fcb550c7`.
At23:58:00Z samecontroller0042229557/supervisor2229556 remain owned/live,
no pending reservation; original full gate before cell23 MultiHop6/DeepSeek/Slow/E.
Remaining170, full192/inactive private/manual/failure/adoption/Q1–Q10 unfinished.
No source/model/prompt/budget/scheduler change, private body audit or PCpayload.

Historical snapshot020 at23:49:27Z had21effective outcomes,
SHA256 `a3c41f513f7beb73b70a3b58734866bcf31dbff403033075730bff96ad4f3992`,
journal `b023a7b86e4fb66c29b8f8c50be4afb9e52aec14ee4cf946064cfc8344c51004`.

Cell21 MultiHop6/DeepSeek/Fast/B1 completed, format valid, original score1.0.
Original admission/journal, empty stores, resident identities, Worker exits,
tc restoration/direct terminal model and16SDKcontexts independently pass;
auditSHA `166e16c18bf68b0dd5f5b6683211fd1ca5aba9aabe663f9105fa21c0030b4eb1`.
Eight Manager/Verifier turns, no specialist,12physical requests: three-shard
BM25 rounds with top_k20 →5 →3, each followed by a model request. The first
two were context-rejected before inference; the third consumed three artifacts
on A28/resident-a28-qwen35-27b-v1:7,466input/4output tokens, stop,
129.421s backend service. One semantic-validation and one phase-restricted
SDKcall are separate. No automatic retry, hidden reduction or manual recovery.
Source-bound shape-only receiptSHA
`c2818fcc53431a6b1446fe858b2e676396f6309f688d0e976708b29ff087ea94`
binds actual top_k values without exporting query, prompt or evidence bodies.
Complete Agent movement17,878B/.507s; separate initial7,696,522B/1.203s.
Successful tool work3.178s, inclusive model-action Worker work129.639s;
do not double-count the backend service. Graph12nodes/9edges/37snapshots/peak3,
E2E220.323s, API frozen listpriceUSD.148450. Weak original score1 is not an
evidence-retention oracle. Fresh B1 exposure, reduction and low recorded bytes
do not establish causal profile adoption or a quality-preserving method benefit.

Feedback016 audits340actual contexts=165Manager/165Verifier/10specialist,
53B1profiles/74A_Eledgers/36frozenrules exactly matching provider requests.
SHA `a50fe0364388d323f6562044b51a92d49ede04ca6a5fa8f61256f4a2b06b670f`.
At23:50:29Z the same controller004 remains owned/live, no pending reservation,
performing the original full gate before cell22 MultiHop6/Qwen/Slow/A.
Remaining171, full192/inactive private/manual/failure/adoption/Q1–Q10 unfinished.
No source/model/prompt/budget/scheduler change or payload through development PC.

Historical snapshot019 at23:39:54Z had20effective outcomes,
SHA256 `7995295a22d1a890b4c7faa335cc328924885d068525990504c170c7bdcaa47e`,
journal `266d4bd9bd8f4bed9dbff4e3d7df3e81e96c2bc15df4b712e6c539cb33444000`.

Cell20 MultiHop4/Qwen/Fast/A completed, format valid, original score0.0.
Original admission/journal, four empty stores, five resident identities, Worker
exits/tc restoration/direct terminal model and12actual SDKcontexts pass;
auditSHA `342dda96cb7be83677d09f25085139c5c7eacbbf254045be0ae99c1280b2c7ca`.
Six Manager/Verifier turns, no specialist; six physical actions in sequence:
aggregate_artifacts → bm25_retrieve → read_artifact → bm25_retrieve →
read_artifact → invoke_model. The successful terminal model consumed two
artifacts on A28/resident-a28-qwen35-27b-v1:7,562input/162output tokens, stop,
187.421s backend service. No context or other typed failure occurred.
Complete Agent movement5,204,596B/1.627s; separate initial7,696,522B/1.278s.
Successful tool work2.272s; inclusive model-action Worker work187.567s must not
be added to backend service again. Graph6nodes/6edges/19snapshots/peak1,
E2E234.878s, API frozen listpriceUSD.136943. Wrong quality is retained, not
retried or repaired. Retrieval/evidence versus terminal reasoning cause remains
unknown until full-block private audit; physical success alone does not isolate
semantic failure subtype. No matched causal claim against17–19 is made.

Feedback015 audits324actual contexts=157Manager/157Verifier/10specialist;
45B1profiles/74A_Eledgers/36frozenrules exactly match provider requests.
SHA `ecdeaf31bc2ce0179c9692f273aef314afa2a208329de8654c33e0a8517c3101`.
At23:40:50Z controller0042229557/supervisor2229556 remain owned/live with no
pending reservation, validating the original full gate before cell21.
Remaining172 preserve the original schedule. Full192/inactive private/manual/
failure/adoption/Q1–Q10 are outstanding; no execution source or tuning changes.

Historical snapshot018 at23:30:46Z had19effective outcomes,
SHA256 `7c33b755c07450dc8eb279ab49ca730d2e0f03242e7069dd7797737e794a8712`,
journal `dfe3a28cd22c3a8248a8f9105beb0e92440fbd1ed9b15b811588026fb9913e00`.

Cell19 MultiHop4/DeepSeek/Slow/B1 completed, format valid, original score1.0.
Original admission/journal, empty stores, five resident identities, Worker exits,
tc restoration/direct terminal model and26SDKcontexts independently pass;
auditSHA `48aa06c96cb65eecb35f021f476372ad2f26b34817538ad941528dad6382e459`.
Twelve Manager/Verifier turns, two specialist turns/one created/peakactive1,
15physical requests: six BM25, six read_artifact and three model requests.
Two model requests were context-rejected before inference; a later request
reached strong-4090/resident-4090-gpu0-qwen35-27b-v1:432input/143output,
stop,2.218s backend service. Typed observations also include two unavailable
artifact references and eight phase restrictions; original admission is valid,
not a Worker-store collision. No action was replaced or manually repaired.
Complete Agent artifact transfer0B/0s is distinct from initial7,696,522B/22.032s
and is not a zero-network-traffic claim. Successful tool work3.802s,
inclusive model-action Worker work2.220s; these overlapping receipt work values
are not an E2E decomposition. Graph15nodes/14edges/46snapshots/peak6;
successful terminal physical model has no artifact inputs. This alone neither
proves evidence loss nor establishes semantic sufficiency; private audit deferred.
E2E196.997s/API frozen listpriceUSD.566055. No causal comparison with18,
because Planner and method differ; weak evaluator score is separate from audit.

Feedback014 audits312actual contexts=151Manager/151Verifier/10specialist;
45B1profiles/68A_Eledgers/36frozenrules exactly match provider requests.
SHA `cfb570d0651975d218022b18a9b3cf4ec0f8c63715f56a35e1a354ccb78e73c3`.
At23:31:53Z the same controller004 remains owned/live, no pending reservation,
validating the original full gate before the next cell. Remaining173 are not
completed; no restart/tuning/private body audit or payload export. Full192,
inactive private/manual/failure/adoption andQ1–Q10 remain outstanding.

Historical snapshot017 at23:24:09Z had18effective outcomes,
SHA256 `04b06062b3fc5f48019881a6e254a5e06f3f61e3cb45dacc685e4a8c87a09397`,
journal `6637ed398d120c961ff3e95b21dea5431481d59b243abff9ae1e4160396bfc4f`.

Cell18 MultiHop4/Qwen/Slow/B0 completed, format valid, original score1.0.
Independent original admission/journal, four empty stores, five resident
identities, Worker exits/tc restoration, direct successful terminal-model answer
and22actual SDKcontexts pass; audit SHA256
`3b13b2225137558c6cd82e0384a9f8cbcf49763e077ecc86c358b84001d4fe22`.
Eleven Manager/Verifier turns, nine physical actions: one aggregate, two BM25,
four filter and two model requests. One model request was context-rejected
before inference; one later request reached A28/resident-a28-qwen35-27b-v1,
reporting1,711input/2output tokens, stop and32.244s backend service work.
The Manager continued after typed context and semantic-validation feedback,
without manual recovery or retry. One phase-restricted SDKcall is separate.
Successful tool work2.692s; inclusive model-action Worker work32.451s is not
additional backend work. Agent movement5,204,596B/14.838s is complete; initial
7,696,522B/22.434s is separate. Graph9nodes/10edges/28snapshots/peak1;
terminal model consumes two artifacts. Weak original score1 is not independent
semantic/evidence-retention verification. Do not causally compare this cell
against17: Planner, network and method all differ.

Feedback013 audits286actual SDKcontexts=139Manager/139Verifier/8specialist,
33profiles/68ledgers/36rules exactly matching archived requests;
SHA256 `1c5e51175890488752f61a4a82af9a72271ce293522550ce4bb8464318bb5cb6`.
At23:27:44Z the same controller0042229557/supervisor2229556 are owned/live;
cell19 MultiHop4/DeepSeek/Slow/B1 attempt1, atomic2265023, is owned/live.
The journal then has38records/18effective settled/one pending. Pending is not
completion. Remaining174 preserve the frozen schedule; no controller restart,
model/prompt/budget/scheduler change or payload transfer through the development PC.
Full192 and inactive private/manual/failure/adoption/Q1–Q10 remain outstanding.

Historical snapshot016 at23:07:31Z had17effective outcomes,
SHA256 `ef36035b6960d0ca502b48e0eb9a47a008c7a78eb5ad5fa144b1b10805de18d9`.

Cell17 MultiHop4/DeepSeek/Fast/E completed, format valid, original score0.
Its exact2post-backend model-JSON failures are source-bound reviewed under
sidecarSHA `7509ddddc81e2fb04bbde3df76175176ead5b362b3048b8809f70999cf461c66`.
Raw journal/admission and score0 remain unchanged; replacement forbidden.
Full original admission/settlement, four empty stores, resident identities,
Worker exit/tc cleanup/direct terminal model and12actual SDKcontexts independently
pass (audit22f2fe0b1d72b5b956d9fd20047d767633fe1fcfc5167fa6673c5542ab20cd2a).
Four successful model receipts report22,619input/1,060output/4stop and189.851s
backend service work. Two additional backend completions are source-proven;
their tokens/finish/service work and full movement remain unknown. Successful
movement subtotal0 is not a full zero-traffic claim. Six BM25 requests/sevenmodel
requests/one context reject/three logical phase restrictions,6Manager/6Verifier,
no specialist;13nodes/6edges/40snapshots/peak3. Semantic/evidence cause remains
unknown pending the completed inactive private block; terminal0artifact inputs
does not by itself prove evidence loss.

Controller003 ended before any next cell. After external bookkeeping-only
reservation validation correction, reviewed control002 and adapterfreeze003
were source-bound and controller0042229557/supervisor2229556 are owned/live
at23:08:43Z, validating the original full gate. No atomic18 is asserted yet.
Remaining175 preserve the schedule; nextMultiHop4/Qwen/Slow/B0.
Actual original private guard still rejects this controller before body reads
(receipt7a49714ec6485ff1c1b1f7e47e6a6a2b8b032c30731477655705e713766650b7).
Feedback012 audits264contexts=128Manager/128Verifier/8specialist;
33profiles/68ledgers/36frozenrule exposures match actual requests. Visibility
still does not establish adoption/causal optimization; final audits remain open.

Historical live continuation at2026-10-06T22:47Z: cell17,
`phase2-multihop_rag-4-fffab28c23fbdeaf-p1-fast-E`, attempt1,
atomic2188408 is owned/live. This is a pending reservation, not another result:
the settled population at that capture remained16. Its initial four Worker stores were empty,
five resident instances were attested before execution, and the atomic process
uses only archived execution004src/scripts with revision
`0ff0e9b6d0799bd62e725a76b157e64cd9df5ccd`. External controller/private-audit
namespaces are absent from the atomic PYTHONPATH. Start receipt SHA256:
`dd29530e68dcc36230b3f07ad6ea2875f60d2b012aa1fa604efc3c0c7028d669`.
Completion, quality, final residency, tc cleanup and recipient audits for this
cell are not yet claimed. No completed sample was repeated.

Checkpoint: 2026-10-06T22:20:09Z / 2026-10-07 06:20 HKT. Sixteen of 192 nominal
held-out cells are effective valid samples; no reservation was pending at this
snapshot. Cell16's raw JSON audit rejection is preserved and source-bound reviewed,
not silently rewritten or rerun. These are
actual original evaluator results, not final
method estimates. Same frozen 18-task manifest, execution004, resident diversified
pool, B0/B1/A/E methods, deterministic schedule and n1 discipline. Old42 and
Phase I results are not pooled into this held-out table.

The first four cells are the same frozen LongBench-v2 position6 task hash
`612be14c898ffdda`, attempt1. Canonical choice came from successful terminal model
output; evaluator ran without a semantic finalizer. Original admissions were
independently reproduced exactly and matched journal settlements. Empty initial
stores, Worker exit, five-instance residency and tc restoration passed. Existing
actual SDK recipient scans found no issues; complete post-block semantic/adoption
audits remain pending. Cells five through eight are frozen Video-MME position5
task hash `332db0bfa03dd109`, also attempt1, with valid completion and original
scores 0, 0, 1 and 1 respectively. Neither wrong-answer cell was retried.

| Task | Planner / network / method | Completion / format / score | Manager / Verifier | Physical / returned inference | Context rejects | E2E s | Initial bytes / s | Artifact movement bytes | API list-price USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LongBench6 | DeepSeek / Fast / E | true / valid / 1 | 6 / 6 | 4 / 1 | 1 | 61.338 | 2,032,683 / 0.215 | 0 | 0.076829 |
| LongBench6 | Qwen / Slow / B0 | true / valid / 1 | 6 / 6 | 4 / 1 | 1 | 57.405 | 2,032,683 / 5.737 | 0 | 0.066510 |
| LongBench6 | DeepSeek / Slow / B1 | true / valid / 1 | 17 / 17 | 24 / 11 | 2 | 392.753 | 2,032,683 / 5.739 | 0 | 0.468597 |
| LongBench6 | Qwen / Fast / A | true / valid / 1 | 6 / 6 | 4 / 1 | 1 | 53.779 | 2,032,683 / 0.204 | 0 | 0.065860 |
| Video5 | Qwen / Fast / E | true / valid / 0 | 8 / 8 | 7 / 1 | 1 | 136.761 | 2,076,341 / 0.209 | 0 | 0.486185 |
| Video5 | DeepSeek / Slow / A | true / valid / 0 | 7 / 7 | 4 / 1 | 1 | 140.020 | 2,076,341 / 5.906 | 0 | 0.180513 |
| Video5 | Qwen / Slow / B1 | true / valid / 1 | 3 / 3 | 2 / 1 | 0 | 101.103 | 2,076,341 / 5.863 | 0 | 0.120313 |
| Video5 | DeepSeek / Fast / B0 | true / valid / 1 | 3 / 3 | 2 / 1 | 0 | 91.785 | 2,076,341 / 0.211 | 0 | 0.108085 |
| Video6 | DeepSeek / Fast / B1 | true / valid / 1 | 3 / 3 | 2 / 1 | 0 | 121.284 | 233,097,342 / 20.753 | 0 | 0.071510 |
| Video6 | Qwen / Slow / A | true / valid / 1 | 5 / 5 | 3 / 1 | 1 | 753.030 | 233,097,342 / 650.833 | 0 | 0.220815 |
| Video6 | DeepSeek / Slow / E | true / valid / 1 | 6 / 6 | 5 / 3 | 1 | 802.365 | 233,097,342 / 650.722 | 0 | 0.285777 |
| Video6 | Qwen / Fast / B0 | true / valid / 1 | 5 / 5 | 3 / 1 | 1 | 101.233 | 233,097,342 / 20.537 | 0 | 0.184910 |
| MultiHop5 | Qwen / Fast / E | true / valid / 0 | 10 / 10 | 13 / 1 | 2 | 318.009 | 7,696,522 / 1.339 | 5,204,596 | 0.234685 |
| MultiHop5 | DeepSeek / Slow / A | true / valid / 1 | 14 / 14 | 22 / 10 | 3 | 682.445 | 7,696,522 / 22.219 | 0 | 0.394572 |
| MultiHop5 | Qwen / Slow / B1 | true / valid / 1 | 10 / 10 | 13 / 2 | 1 | 1034.529 | 7,696,522 / 22.042 | 5,204,596 | 0.202958 |
| MultiHop5 | DeepSeek / Fast / B0 | true / valid / 0 | 13 / 13 | 48 / 5 | 3 | 1884.311 | 7,696,522 / 1.511 | unknown; returned subtotal 43,046 | 0.838502 |
| MultiHop4 | DeepSeek / Fast / E | true / valid / 0 | 6 / 6 | 13 / 4 | 1 | 352.579 | 7,696,522 / 1.108 | unknown; returned subtotal 0 | 0.150308 |
| MultiHop4 | Qwen / Slow / B0 | true / valid / 1 | 11 / 11 | 9 / 1 | 1 | 149.584 | 7,696,522 / 22.434 | 5,204,596 | 0.175846 |
| MultiHop4 | DeepSeek / Slow / B1 | true / valid / 1 | 12 / 12 | 15 / 1 | 2 | 196.997 | 7,696,522 / 22.032 | 0 | 0.566055 |
| MultiHop4 | Qwen / Fast / A | true / valid / 0 | 6 / 6 | 6 / 1 | 0 | 234.878 | 7,696,522 / 1.278 | 5,204,596 | 0.136943 |
| MultiHop6 | DeepSeek / Fast / B1 | true / valid / 1 | 8 / 8 | 12 / 1 | 2 | 220.323 | 7,696,522 / 1.203 | 17,878 | 0.148450 |
| MultiHop6 | Qwen / Slow / A | true / valid / 1 | 9 / 9 | 8 / 1 | 1 | 98.339 | 7,696,522 / 22.033 | 0 | 0.124987 |

Cell16 completed with original score0,13Manager/13Verifier,8specialist turns,
1created specialist,48physical actions,5successful inference telemetry receipts.
It also has one source-proven backend completion followed by invalid JSON
materialization; five returned receipts are not asserted to be all backend calls.
Three context and three read-size rejects returned to the Agents, which continued.
The48-node/37-edge graph has145snapshots and peak concurrency6. Terminal answer
comes directly from a separate successful prompt-only physical model action;
the original evaluator ran, without a new semantic finalizer.

Five returned model receipts record18,102input/3,468output tokens, all stop, and
1283.773s service work. Complete model work/tokens/finish distribution remain
unknown because the JSON-failed action has no returned telemetry. Successful tool
work9.055s and inclusive model-action Worker work1284.028s are not an E2E
decomposition and must not be added again to backend work. Successful registered
transfers total43,046B/.881s; full transfer totals are unknown because four
execution-stage failures lack complete execution receipts. Initial7,696,522B/
1.511s remains separate. Do not rank observed subtotals as complete costs.

Raw original admission is confounder only for the exact known post-backend JSON
error. Its full admission/journal, stores/exit/residency/tc/direct terminal and
34SDKcontexts independently reproduce; audit SHA256
`d8500a885a00584c46ce9a63f36a0a13b040610edcbf5248cadab6cb54d11ba4`.
Exact offline sidecar SHA256
`916192e8cc7aaf97ad5e789acf6ce8a684ce29a14e11e675855f1180b2338015`
supplies effective valid disposition, preserves score0 and explicitly forbids
replacement. Original journal/admission/trace/result remain unchanged.

Snapshot015 SHA256
`1c62622eab48ad7354d0de9529feba052c3206a66c34a7f2fda1af28ed727ea9`,
journal `4e5d6d964a7a8fa8001a9d8da7760de7130b16d88319efedca8a0817e5d4672c`:
16effective valid/16attempts/0pending/0effective confounders/1preserved original
confounder/0operational exclusions. Exact reviewer and read-once projection
adapter source/freeze are explicitly bound. No score pooling, retry or tuning.
Feedback011 audits252actual contexts,122Manager/122Verifier/8specialist; the
fixed Verifier and bounded specialist remain Blind. Visibility/evidence path is
not a semantic sufficiency or causal adoption oracle.

The first resumed external controller was self-rejected at startup before any
new reservation/Worker/tc/model call. Its exit/console are preserved as a setup
diagnostic, not a benchmark replacement. Narrow controller identity repair is
documented in [preparation](large-scale-resident-phase2-json-review-preparation-v1.md).
Actual continued queue execution must be verified separately. Remaining176cells
and complete post-block semantic/failure/adoption/Q1–Q10 audits are outstanding.
Historical checkpoint descriptions below retain their captured populations.

The fifteenth cell completed with valid direct terminal-model output and original
MultiHop score1. Ten Manager/Verifier turns and13physical actions: one aggregate,
six BM25, three select_fields and three model requests. One model request failed
context preflight; two A28Qwen3.5-27B requests returned actual inference. Separate
phase_restricted and semantic_validation_failed observations returned to the
Manager and did not become physical executions or hidden fixes. No specialists.

The first returned model receipt was6,767input/2,048output tokens, finish_reason
length, service796.637s. This explicit output-limit receipt is retained, not
called a normal stop or silent input truncation. The Manager then submitted a
distinct model action against the three evidence artifacts; its6,723input/2output
tokens, finish_reason stop and116.151s service produced the terminal answer.
This is recorded agent continuation, not an automatic backend retry. Combined
model service work912.788s, tool work9.323s and inclusive model-action Worker
work913.191s must not be double-counted. E2E1034.529s includes initial7,696,522B/
22.042s; registered Agent artifact movement is5,204,596B/14.944s. The graph has
13nodes/18edges/40snapshots, peak concurrency3. Score1 remains the original weak
evaluator result, not proof of evidence sufficiency or optimal cost reasoning.

Original admission independently reproduced exactly and matched the journal.
Four empty initial stores, Worker exit, five unchanged resident identities, tc
restoration, direct terminal-model text and20actual SDK contexts passed. Audit:
`e250fcf465f295562da2bf199badbeb14c23cda5916eea92459aafbec9b34b0f`.
Ten actual B1 feedback deliveries match their corresponding anonymous profile
payloads; visibility does not establish causal adoption or system benefit. No
retry, model reload, prompt tuning or private supporting-body audit occurred.

Snapshot014 SHA256 `1d11e7e3611572ce7c8f4c5876c28aa124d1945025739548d4ac733d335180de`,
journal at capture `658bda5ebee5c52d901334dbd3b959a2fb038effdab67c16c69587391dd80eaf`:
15admitted/15attempts/0pending/0confounded/0operational-excluded. The controller
continues the remaining177frozen cells. Full held-out private/manual semantic,
adoption, failure and Q1–Q10 analysis remain outstanding. Historical checkpoint
descriptions below retain their own capture times and populations.

The fourteenth cell completed with valid direct terminal-model output and original
MultiHop score1. Fourteen Manager/Verifier turns,22physical actions: nine BM25
actions and thirteen model requests, of which three were pre-inference context
rejects and ten returned successful inference telemetry. Actual successful model
selections span A4VL4B, A5VL8B and A28Qwen3.5-27B, three receipts each, followed
by one explicit prompt-only terminal model on4090GPU0. This is real execution on
fourWorkers, not forced routing or an assumption that every resident instance was
selected. GPU1 was not selected in this cell. No specialists were created.

The ten returned receipts record68,285input/446output tokens, all normal stop;
backend service work634.638s. Tool work6.304s and model-action Worker work635.955s
are exclusive receipt categories, not quantities to add again to backend work.
E2E682.445s includes initial7,696,522B/22.219s; registered action artifact movement
is complete0B. Zero movement does not imply no prompts/control traffic. The action
graph has22nodes/21edges/67snapshots and peak concurrency6; overlap/work sums are
not an E2E decomposition. Privacy and semantic evidence sufficiency are distinct.

Original admission reproduced exactly and matched journal settlement. Four empty
stores, five stable resident identities, tc restoration, Worker exit, direct
terminal-model text and28actual SDK contexts independently passed. The recorded
phase/readiness/semantic failures were returned to the Manager, which continued;
none is silently repaired or counted as inference. Independent audit SHA256
`27544644886bfed56e57ec227609319c66ad7b1f6453cde23e3cf274676945a0`.
Fourteen actual Ledger deliveries match trace payloads; visibility does not prove
useful cost reasoning. Repeated inference work is retained, not tuned away.
This is not a matched comparison with cell13: Planner, network and method differ.
Original score1 is not a private semantic-retention oracle or optimizer success.

Snapshot013 SHA256 `68059249e5a3372f48ba101768f2d7c60ce74bb3d482a2590058b3af7c75818e`,
journal at capture `965de01f812c802e262133738926b4de3f58e1f102929f4cc2eb509a6ce55bbf`:
14admitted/14attempts/0pending/0confounders/0exclusions; full block incomplete.
Earlier live proof SHA256
`71047fa18526c7dca344c7ede032cb2c58e93dff6200c02518157a30b0841cac`
verified original atomic1914655/source004/fresh stores/stable residency. One ad-hoc
read-only poll preceded trace creation and raised FileNotFoundError; the next poll
correctly reported an absent trace during preparation. No experiment was restarted
or modified, and this diagnostic race is not a cell failure.

The thirteenth cell, frozen MultiHop-RAG position5 task hash `a60f56ec789bf3ae`,
completed normally with valid direct terminal-model text and original evaluator
score0. It is a valid quality failure, not a system confounder or a retry target.
Actual sequence: aggregate_artifacts; three BM25 actions; a context-rejected
model request; three select_fields actions; another rejected model request;
three further BM25 actions; then successful A28 model inference consuming three
artifacts. Ten Manager/Verifier turns, thirteen physical actions, thirteen nodes,
eighteen edges, forty snapshots, max actual concurrency three, no specialists.
The two context rejects did not reach inference. The sole returned model receipt
records5,145input/461output tokens, finish stop,228.881s backend service work.
Tool work9.669s and model-action Worker work228.959s are separate exclusive kinds;
backend service is included in the latter, not additional E2E time.

Initial three-shard materialization7,696,522B/1.339s is separate from subsequent
registered artifact movement5,204,596B/1.526s. Terminal text equals the successful
model output directly, without hidden finalization. Original admission and journal
settlement, four empty initial stores, five resident identities, tc restoration,
Worker exit and twenty actual SDK recipient contexts independently passed.
Audit SHA256 `74967cfc330b24e9f1a5e4b03e7cd16040d02c8ecd45c4bc377378ecdea33a1e`.
E's ten exact rule deliveries do not demonstrate rule adoption or benefit.
Required-evidence retention and retrieval-versus-synthesis primary cause remain
unknown until the unchanged post-block private audit guard permits investigation.
No supporting/gold/corpus/store-body reads or exported raw API/model output.

Snapshot012 SHA256 `4576c7eae7d368dcc7ab53d68b266a2f4ab3624ade891d5feaa6be4c1b4c9425`,
journal at capture `e074fd3e180a24aa5c750945919e5ea11ff27c395568cef471ea6b5bdc645dae`:
13admitted/13attempts/0pending/0confounders/0exclusions, block still incomplete.
Its earlier live proof, SHA256
`8bbfa4ade78f94f2ad70f4f6a577e1e89ef18103007bbc1e9dfdd0803c965ac3`,
verified actual atomic1894444, execution004-only imports, four empty stores and
stable five-instance identities before completion. Read-only /state at20:23:40Z
confirmed A28in_flight1 and all fourWorkers available; no failover/restart was used.

The twelfth cell used sample_frames, one context-rejected model request, then
successful A4 visual inference consuming three already materialized artifacts.
The returned receipt records 3,450 input tokens, two output tokens, finish stop
and 19.031s backend service work. Five Manager and five Verifier turns, three
graph nodes, eleven edges, ten snapshots, no specialists and max concurrency one.
Original admission was independently reproduced and matched settlement; four
empty stores, five resident identities, Worker exit, tc restoration, successful
terminal model provenance and ten actual SDK recipient contexts passed. No retry
or semantic tuning. A context reject followed by smaller-input continuation is
observable recovery, not proof of an infrastructure-guided optimization.

Append-only snapshot011 SHA256:
`d83b7fe0bec6b78cf4297feb0fb5e78900535064ffeaefef1a8fb9635b6ac2e5`;
journal SHA256 at capture:
`870e698752088f0a70428598a1f6e86808ae900f05c91117b457bc05f6e700c0`.
Twelve admitted attempts, no pending reservation or confounder at this capture;
the live controller remains active, so this is not completion of the block.
Independent twelfth-cell audit SHA256:
`90b2703c7869bf63c8ab144e335802e7b1af057fde80f3b36ee1f671c22a549a`.
All receipts remain owner-local under the existing analysis root. Historical
snapshots below retain their original populations and timestamps.

Fast100Mbps/configured5ms and Slow3Mbps/configured50ms retain the existing
Jetson HTB/no-netem caveat: configured delay is not measured symmetric RTT.
Initial materialization is separate from Agent-controlled registered artifact
transfers. Zero artifact movement does not mean zero HTTP prompt/control traffic.
The price estimate is based on frozen usage/pricing, not the provider invoice.
Worker operator receipts include invoke_model and must not be added again to
backend service work as an E2E decomposition.

Observed paths:

- E, B0 and A: two BM25 attempts, two model requests, one context preflight rejection
  followed by successful smaller-input inference. Six Manager/Verifier turns,
  four graph nodes. No specialists; single-agent completion is valid.
- B1: ten BM25 actions, one aggregate_artifacts action and thirteen model requests,
  with eleven returned inference telemetry receipts and two context rejections.
  24 graph nodes/14 edges, 73 snapshots, zero specialists. Physical model input/
  output totals42,324/729; all eleven finish reasons stop. Backend service work
 260.379s. Most successful model selections were A4; the terminal prompt-only
  choice synthesis selected the4090GPU0Qwen3.5-27B instance,290input/2output tokens.
 34actual SDK contexts (17Manager/17Verifier) scanned without findings.
- Video5/E: sample_frames, an infeasible model request, four make_contact_sheet
  actions, then successful visual model invocation consuming all four sheets.
  A4VL4B returned4,620input/2output tokens, finish stop; service25.118s. Seven
  graph nodes/64 artifact-flow edges/22snapshots; max actual concurrency1,
  no specialists. The terminal model choice was format-valid but wrong under
  the original evaluator. Actual original admission/settlement, four empty stores,
  unchanged five resident identities, tc restoration, Worker exit and16SDK
  recipient contexts passed. This is retained without retry/tuning; visual
  reasoning versus evidence selection/coverage remains unidentified pending
  post-block private audit. Source-bound first-video audit SHA256
  `07edea55b8d8a80ae3e5927d943c95c5197bf6a656b755b0f9cb2e924c2d322b`.
- Video5/A: sample_frames, a context-rejected model request, another sample_frames
  action with fewer frames, then successful A4 visual inference on seven artifacts.
  Model input/output7,819/2, finish stop, backend service44.262s; four graph
  nodes/23 edges/13 snapshots, no specialists and max action concurrency1.
  The resulting canonical choice was wrong, not a runtime/format failure.
  Exact original admission reproduction and journal receipt, four empty stores,
  unchanged five runner/server identities, tc restoration, Worker exit and14
  actual SDK contexts passed. Source-bound audit SHA256
  `ebe5f45c93bda035cc9df9d97458657e2600b2c5ea82765588a2f81bbc04824f`.
- Video5/B1: sample_frames then successful A4 visual model inference on seven
  artifacts, with no context rejection. Model input/output7,760/2, finish stop,
  service44.144s; two graph nodes/seven edges/seven snapshots, no specialists
  and max action concurrency1. Exact original admission/journal, empty stores,
  unchanged five resident identities, cleanup, Worker exit and six actual SDK
  contexts passed. Source-bound audit SHA256
  `4ddbed36cdcfd0ee4ed3796748c786e348ffb4aa459f4ec8edfc98521230e377`.
- Video5/B0: sample_frames then successful A4 visual inference on seven artifacts,
  no context rejection,7,905input/2output tokens, finish stop, service44.610s.
  Two nodes/seven edges/seven snapshots, no specialists, max concurrency1.
  Original admission/journal, four empty stores, five stable resident identities,
  tc restoration, Worker exit and six actual SDK contexts passed. Source-bound
  audit SHA256 `6c40c24de1d5b4b2935fa4d11b31498048240d00065f07048e6d710f424e2100`.
- Video6/B1, task hasha530f885312b82f6: sample_frames then successful A4 visual
  model inference on six artifacts, no context rejection,6,707input/2output tokens,
  stop, service37.782s. Sampling operator work25.903s; two nodes/six edges/seven
  snapshots, no specialists and max concurrency1. The larger fixed video payload
  took20.753s to materialize, separate from zero Agent artifact movement. Original
  admission/journal, empty stores, five stable resident identities, Worker exit,
  cleanup, terminal provenance and six SDK contexts passed. Audit SHA256
  `639b8718d11b114f7a98980d717c1cbad7a2b7218164d6de8c6266c22c2499a3`.
- Video6/A: sample_frames, a context-rejected model request, then a successful
  A4 visual model invocation using three already materialized artifacts. Model
  input/output3,411/2, stop, service19.035s; three nodes/35 edges/ten snapshots,
  no specialists and max concurrency1. Manager continued after typed preflight
  and schema/phase observations without hidden repair or retry. The initial
 233,097,342B video materialization took650.833s of753.030s E2E, separate from
  zero Agent artifact movement. This setup-dominated result is not an Agent
  communication-saving claim or a causal comparison with the different Planner/
  method/network ninth cell. Original admission/journal, four empty stores,
  five stable resident identities, cleanup, Worker exit, terminal provenance and
  ten actual SDK contexts passed. Audit SHA256
  `26e77b78caa1b341ebfeb82e29135e1a70dde2cfdad0d470c8de48d5e229b4f9`.
- Video6/E: sample_frames and four model requests: one context rejection,
  two successful A4 visual inferences, then an explicitly selected prompt-only
  terminal synthesis on4090GPU0Qwen3.5-27B. Three returned inference receipts,
 9,253input/6output tokens, all finish stop, total backend work49.627s. The
  successful terminal model supplies the canonical choice; it is not an extra
  hidden finalizer. Five nodes/24 edges/16 snapshots, no specialists and max
  concurrency1. Initial materialization650.722s remains separate from zero
  registered Agent artifact movement and802.365s E2E. Extra visual/model work is
  retained, not tuned away or called a cost saving because quality passed.
  Exact original admission/journal, empty stores, stable resident identities,
  cleanup, Worker exit, terminal provenance and12actual SDK contexts passed.
  Audit SHA256 `536848a75cc0dc5693ad9a5355d2cc5098a6b637d840bb204bfd7aba48ac6c1e`.

Actual feedback-wire review of all eleven settled cells matched persisted provider
requests, not just trace declarations: 70 Manager plus70 Verifier contexts,
23 exact B1 pre-decision profiles,38 exact A/E ledgers and20 exact E rule payloads.
All Verifier requests used the fixed frozen model and contained none of the
profile/ledger/rules message prefixes. B0 had none of these feedback messages.
The existing full recipient scans had no findings. Advisory rules were the same
canonical payload throughout; visibility is not internal adoption or causal
optimization. Owner-local feedback audit006 SHA256:
`f2f75e4ba4f8f21d26e7ae061e570c1b7b7788a693061b4cead709e70639efd7`.
The ten-cell audit005 is preserved with SHA256:
`2cca663e95ea0c5964308fd7c434cc79f74cf0dea11df28788ca443b986aca3b`.
The nine-cell audit004 is preserved with SHA256:
`0223640e8c48c4a67d7a01015b0bcf72ff9bdce37a0a73d908e5a92931c82a60`.
The eight-cell audit003 is preserved with SHA256:
`16a68ee56c944055ff0f2278086403e9b96db6f6abb1a3850e8d066acd552dbf`.
The seven-cell audit002 is preserved with SHA256:
`7d1ee33a2d8846f0914de6f36fe38add6637c21ca7a937625fa8de04ad7733de`.
The six-cell audit001 is preserved with SHA256
`a35c518dda67f761937608cf87661d44c12f3d85536b9c6d4c1253ea2aa2f7e8`.
No support/corpus/store-body or gold scans were performed while the queue was live.

These unmatched Planner/method/network cells cannot establish an E or B1 causal
effect, a matched speedup, stable infrastructure adaptation or statistical
significance. B1's longer successful trajectory is retained unchanged, not
treated as a bug to tune away. Evidence coverage/semantic sufficiency and causal
profile adoption remain separate questions for the full audit.

Authoritative owner-local snapshot010 SHA256:
`6a50144c235831e74cf6380c81fbe03e504c2bfb689e76e512285e8324e9b552`,
under `/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.
Journal SHA256 at that checkpoint:
`abe096a80f48c11c5ca9c77edfa1e8cea7d947638f76733ec3576d3af3243fd8`.
Eleven admitted cells, eleven preserved attempts, zero pending; no confounded or
operational-excluded attempts. Earlier snapshot009 SHA256:
`cee444fe3a3cd800f16bf0f334e8071cb829c07224ff3030a23fbff847881ac9`,
under `/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.
Journal SHA256 at that checkpoint:
`154a1768f12316ddf6650fc89ea3e0de564f28a320a7f158ed16fc118ec0e7d3`.
Ten admitted cells, ten preserved attempts, zero pending; no confounded or
operational-excluded attempts. Earlier snapshot008 SHA256:
`7f63d2ab27420269f8db1005e01905c0b87c78e3c3202a9d8f0a8c0bf896433b`,
under `/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.
Journal SHA256 at that checkpoint:
`7089a591c244a1a01bb8d085c7446e6a9786e3a109c915b9c4a577e9d9e582c6`.
Nine admitted cells, nine preserved attempts, zero pending; no confounded or
operational-excluded attempts. Earlier snapshot007 SHA256:
`48dfed8298f46726df7534e3656428b0f5ff522d8940b390f4788ef7e01e2f98`,
under `/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.
Journal SHA256 at that checkpoint:
`6c0da78fc0ed3ab39924638a5adef52fc925a89bbcfc4ce268d165e0f82f787f`.
Eight admitted cells, eight preserved attempts, zero pending; no confounded or
operational-excluded attempts in this held-out block. Earlier snapshot006 SHA256:
`b18abcb244ce89cd6f6d40254667b809cb1b1080673a2db4a21f6408b662fb76`,
under `/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.
Journal SHA256 at the seven-cell checkpoint:
`c95be495615079c6eddda3ffc8ee376a6d636c32a42ba220a0bf535f40fd20c5`.
Its eighth reservation was pending, not completion. Earlier snapshot005 (six
settled cells) remains preserved:
`3df2cca139d9fae2e99c7eb1f7ef6f7b9ddfd4464881de62ef4729101beb6555`.
Earlier snapshot004 SHA256:
`cbfc4ee0a97a7d1c8cb11c172140e14cb2b01d7816a17362fef4daf68adde2e5`,
under `/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.
Journal SHA256 at that checkpoint:
`4cfc30a5cb72954293d5670ceb1cc5677d6e56adabe3a237972095bc959cd8e7`.
Earlier snapshot002, covering the first three cells, remains preserved:
`0cb9a56a44ed0707482c237958a8ef9a760d2c27e85ab06a42ad01b54230bc9c`.
At snapshot003, the fifth cell was pending; its reservation is not completion.
Snapshot003 SHA256 remains preserved:
`7b9bdfa4d7d3f0b969cea7eec7a0324be366a513e605386123aa54366e82db8e`.
No complete-table aggregation, private-body scan, new method, retry, prompt
tuning or replacement was performed. The remaining frozen schedule continues.
See [first-cell audit](large-scale-resident-phase2-first-cell-v1.md) and
[collector validation](large-scale-resident-phase2-projection-v1.md).
