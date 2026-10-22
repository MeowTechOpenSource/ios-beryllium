# Working on ios-beryllium

- Read `NOTES.md` before starting; it contains the project goal, hardware facts,
  current blocker, local artifact locations and the next concrete action.
- The user switches agents frequently. Update the active handoff in `NOTES.md`
  after each milestone and before stopping. Record commits, CI run IDs, exact
  build/boot results and unfinished work. Distinguish observations from guesses.
- Commit completed changes. Use `gh` for GitHub Actions kernel builds and logs.
  Local single-file cross-compiles are useful before spending a CI run.
- Device bring-up uses temporary `fastboot boot` images. This user explicitly
  authorized formatting/writing `userdata` for iOS on 2026-10-22. Preserve GPT,
  bootloaders, recovery, modem, persist and private partition backups. Do not
  extend that authorization to other partitions. The phone is currently away;
  continue offline work without device operations until it returns.
- Keep device dumps, serial numbers and downloaded Apple artifacts out of git.
