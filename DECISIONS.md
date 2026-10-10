# Merge test log: `seoyeon/merge-test`

Written for any teammate or agent picking up the merges. It records what was merged, in which
order, what conflicted, what was decided and by whom, and what is still open.

## What this branch is

`seoyeon/merge-test` is a **rehearsal**. It merges every open PR onto `main` in the planned order
to find conflicts and breakage before the real merges happen.

- **Do not merge this branch into `main`** and do not open a PR from it. The real PRs get merged one
  by one (squash) on GitHub. This branch only tells us what to expect.
- Built from `origin/main` at `33020a0` (Sat Oct 10 2026, after PRs #36 and #39 merged).
- If a PR branch changes after this log was written, this rehearsal is stale for that step. The
  branch heads tested are listed below; compare with `git rev-parse --short origin/<branch>`.

## Result

All five open PRs merge onto `main` in this order, and the final state builds and passes
**200 tests, 0 failures**. Two text conflicts, both in step 5, both resolved by keeping both sides.
One problem the merge does not show on its own: see "Open issues", item 1.

| Step | PR | Branch (head tested) | Merge commit here | Conflicts | Tests after the step |
|---|---|---|---|---|---|
| 0 | | `main` (`33020a0`) | | | **6 audio tests fail** (the ones #40 fixes) |
| 1 | #40 | `seoyeon/audio-tests` (`4429939`) | `f0889cb` | none | 154 pass |
| 2 | #37 | `qimin/settings-view` (`453f163`) | `e583533` | none | 154 pass |
| 3 | #41 | `seoyeon/elevenlabs` (`9671647`) | `843928d` | none | 181 pass |
| 4 | #34 | `tisya/object-memory` (`d3e07fc`) | `d943e22` | none | 196 pass |
| 5 | #35 | `tisya/ar-recovery` (`048ee64`) | `b88edfe` | **2**, see below | 200 pass |
| 3b | #41 | `seoyeon/elevenlabs` again (`916c6b5`) | `34d8d46` | none | 200 pass |

Steps 1 to 5 were each checked with `xcodegen generate`, then the full
`xcodebuild -scheme Echora ... test` run on an iPhone 16 simulator. Step 0 is from running the two
audio test classes on `main`. Simulator only. Nothing in this branch has been run on a phone.

Step 3b: after the rehearsal, #41 gained one commit (the 15 voice clips regenerated with a female
voice, plus the script default and a doc line). It was merged again on top so this branch matches
the PR's current head. Audio files and two text files only; no code changed.

## Why this order

1. **#40 first.** `main` is red: six audio tests fail since #36 replaced the primary cue. Every other
   PR inherits those failures until #40 is in.
2. **#37** touches only `UI/` and conflicts with nothing.
3. **#41** adds the voice listener, the voice clips and `VoicePromptPlayer`. It edits
   `App/AppEnvironment.swift`, which #34 also edits; they merge cleanly in either order.
4. **#34** then **#35**: both are Tisya's and both edit `EchoraCoordinator.swift` and the changelog
   in `docs/CONTRACT.md`, so whichever goes second conflicts. #34 goes first because the voice work
   in #41 depends on its flow.

**#33 (`seoyeon/voice-to-text`) is not in the plan.** #41 contains every commit of #33 with its
`OperatorView.swift` conflict already resolved, so #33 should be closed, not merged. Merging #33 and
then #41 would conflict in several voice files and leave `AnnouncingLocator` defined twice.

## Conflicts and decisions

Both conflicts happened in step 5, merging `tisya/ar-recovery` after `tisya/object-memory`.
In both, the two PRs added different, unrelated lines at the same place.

### Conflict 1: `ios/Echora/App/EchoraCoordinator.swift` (stored properties)

- **Object memory (#34) added:** `objectMemory`, `offeredSighting`, `memoryOfferExpiryTask`
  (the memory store, the pending "want to navigate?" offer, its expiry timer).
- **AR recovery (#35) added:** `worldResetObserver` (hears when the AR session restarted with a fresh world).
- **Options offered:** keep both / only #34's / only #35's.
- **Decision: keep both.** Decided by Seoyeon. Order: #34's block first, then #35's.
- **Why:** the rest of the file uses all four properties, so dropping either side does not compile.

### Conflict 2: `docs/CONTRACT.md` (changelog, last lines)

- **Object memory (#34) added:** the "v2.3 build (no Contracts/ change)" line.
- **AR recovery (#35) added:** the "AR auto-recovery (no Contracts/ change)" line.
- **Options offered:** keep both / only #34's / only #35's.
- **Decision: keep both.** Decided by Seoyeon. Order: #34's line first (it merges first), then #35's.
- **Why:** each line documents its own PR.

### Doing it for real

Both files belong to Tisya (CONTRACT 6.1), so the real resolution is hers: after #34 is merged,
merge `main` into `tisya/ar-recovery` and keep both sides in the two places above. The resolved
versions on this branch can be used as the reference:

```bash
git show seoyeon/merge-test:ios/Echora/App/EchoraCoordinator.swift
git show seoyeon/merge-test:docs/CONTRACT.md
```

## Open issues (not fixed on this branch)

1. **A reset AR world does not clear the object memory.** Found by reading the merged code; no test
   covers it. CONTRACT 4.11 says remembered positions are valid for one AR session and are "cleared
   when the AR session resets". After steps 4 and 5:
   - #35's `handleWorldReset()` in `EchoraCoordinator.swift` ends the round but never calls
     `forgetRememberedObjects()`.
   - #34's `forgetRememberedObjects()` has no caller at all.

   So after an AR recovery with a fresh world, Echora can still say "previously found N minutes ago"
   and guide to a position from the old world, which is a wrong spot. Neither PR can fix this alone,
   since each lacks the other's half. Suggested fix, in whichever of the two merges second: call
   `forgetRememberedObjects()` at the top of `handleWorldReset()`, before the `guard`. Owner: Tisya.

2. **The coordinator's voice lines are silent after step 4.** `AppEnvironment.voicePrompts` defaults to
   `MockVoicePromptPlayer`, and `make(flags:)` never passes the real player from #41. Follow-up once
   #41 and #34 are both merged, in `AppEnvironment.make(flags:)`:
   ```swift
   let voicePrompts: VoicePromptPlaying = VoicePromptPlayer.make(audio: audio) ?? MockVoicePromptPlayer()
   ```
   and pass it to the initializer. Owner of the file: Tisya. The player is Seoyeon's.

3. **Remove the `AnnouncingLocator` stopgap in the same follow-up.** It plays "Item found, navigating."
   and "Item not found, please turn." around the locator, and the coordinator flow from #34 plays the
   same lines. It is off unless `announcements` is in `ECHORA_REAL_SERVICES`, so nothing speaks twice
   by default, but with both on every line would be said twice. Delete the
   `AnnouncingLocator.wrapIfEnabled` line in `AppEnvironment`, `Voice/AnnouncingLocator.swift` and
   `EchoraTests/AnnouncingLocatorTests.swift`.

4. **#41 edits files Seoyeon does not own** (`App/AppEnvironment.swift`, one comment in
   `ios/Config/Local.xcconfig.example`). It needs Tisya's review before merging.

5. **The new primary cue has weak left/right level difference.** With the old cue the near ear got
   more than 2x the energy of the far ear; with the cue from #36 it is about 1.3x at 90 degrees.
   #40 makes the tests independent of the shipped cue, so they pass, but the sound itself deserves
   one blindfolded check. Owner: Qimin.

6. **Not verified on a device:** `VoicePromptPlayer` and the voice clips (#41), the object memory flow
   (#34), AR recovery (#35) as combined here.

## How to redo or extend this rehearsal

```bash
git fetch origin
git checkout -B seoyeon/merge-test origin/main        # start over from fresh main
git merge --no-ff origin/<branch>                     # one PR at a time, in the order above
xcodegen generate
xcodebuild -scheme Echora -destination 'platform=iOS Simulator,name=<any installed iPhone>' test
```

When a step conflicts, stop, describe both sides in plain words, let the human choose, then add a
"Conflict" entry above with the files, both sides, the options, the decision, who decided and why.
