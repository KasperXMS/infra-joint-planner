# Held-out case notes (working; not aggregate conclusions)

These notes use the original official verifier and private trajectory screens. They do not change task scoring. One trial per model/condition means case-level observations cannot establish a treatment effect.

## Qwen3.5-4B: `spring-boot-jakarta-migration`

Both frozen S0 and native S1 cells ended in the original Agent time limit and received official binary resolution 0 and fractional reward 0. The original verifier ran normally in both cells. Its 10 checks had the same pattern: RestClient use, Maven compile, and Maven test passed; seven Jakarta namespace, Spring Security, and dependency checks failed. Original CTRF SHA256: S0 `1d55db8b2b9e992b8070f585ff8ac1b02247cad8953690773433e934811dd701`; S1 `39ef4ef6f00bf7b9511ae8614242e5d947e034318c180634612888bdaed8f0de`. Original result JSON SHA256: S0 `72c2e93ce8365e83b041471da30cddc1e77f3efda85a0b26028cd083fe0a5368`; S1 `60e091979cf0b5ebb2579204260215e66b9e58e37adad4a001d6d7bfa7c02b09`.

S0 made 84 chat requests, 74 tool calls, and consumed 1,617,285 API prompt tokens plus 6,635 completion tokens over 1,010.4 seconds. S1 made 84 chat requests, 75 tool calls, and consumed 1,681,098 API prompt tokens plus 6,836 completion tokens over 1,133.6 seconds. Neither cell had an API transport error. The S1 first system message contained all five official Skill names: `hibernate-upgrade`, `jakarta-namespace`, `restclient-migration`, `spring-boot-migration`, `spring-security-6`. Its ACP trace screen found no Skill file read, reference read, script execution, or harness-recorded invocation; one thought mentioned a Skill path. The timeout leaves a nonterminal ACP trace and five pending tool-call records, so the absence of observed reads cannot establish that no Skill content influenced the model. Both private cell archives are SHA-verified in the local backup.

This case is a paired both-fail outcome. It supplies evidence of delivered Skill metadata and absent observed native Skill access, not evidence that an applied Skill failed to help.
