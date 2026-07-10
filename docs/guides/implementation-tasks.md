# Implementation tasks — step-by-step guides

Four near-term tasks, each written as a full issue → branch → implement → verify
→ PR → merge cycle. They assume you work locally with the GitHub CLI (`gh`)
authenticated and a Python virtual environment.

## Shared workflow wrapper

Every task below follows the same git loop. Do this around the task-specific
work:

```bash
cd ~/Desktop/ai-fpga-engineer
git checkout main && git pull origin main          # start from a fresh main

gh issue create --title "<TITLE>" --body "<BODY>"  # note the issue number N
git checkout -b <branch-name>                      # e.g. feat/ghdl-verify

# ...task-specific work + commits...

git push -u origin <branch-name>
git log --oneline main..<branch-name>              # confirm there ARE new commits
gh pr create --title "<TITLE>" --body "Closes #N"  # link the issue
# after CI is green:
gh pr merge --squash --delete-branch
git checkout main && git pull origin main
```

If `gh pr create` fails with a permission error, add **Pull requests: Read and
write** and **Issues: Read and write** to your fine-grained token (Settings →
Developer settings → Fine-grained tokens → your token → Update token), or open
the PR from the "Compare & pull request" banner on the repo page.

One-time environment setup (needed for tasks 1–3):

```bash
python3 -m venv .venv
source .venv/bin/activate          # prompt shows (.venv)
pip install -e ".[dev]"            # ruff, mypy, pytest, pyyaml
```

Install the open-source HDL toolchain (needed for tasks 1 and 3). On macOS the
simplest route is the OSS CAD Suite (one archive with ghdl, yosys, nextpnr, sby):
download the `darwin-arm64` build from
https://github.com/YosysHQ/oss-cad-suite-build/releases, unpack it, and add its
`bin/` to your PATH for the session:

```bash
export PATH="$HOME/oss-cad-suite/bin:$PATH"
ghdl --version        # confirm it runs
```

(`brew install ghdl` also works if you only need the simulator.)

---

## Task 1 — GHDL-verify the v1 reference designs

**Goal.** Prove that every `benchmarks/v1/*/reference.vhd` actually analyzes
(compiles) under GHDL VHDL-2008. These 18 designs were written by hand and have
not yet been run through a real simulator, so some may contain syntax or type
errors. Fixing them lets CI re-enable the real compile/simulation stages.

**Issue text.**
- Title: `GHDL-verify the v1 reference designs`
- Body: `Every benchmarks/v1/*/reference.vhd should analyze cleanly under 'ghdl -a --std=08'. Add a script that checks all of them, fix any that fail, and document the results.`

**Branch:** `feat/ghdl-verify-references`

**Steps.**

1. Add a verifier script `scripts/verify_references.py`:

   ```python
   """Analyze every v1 reference design under GHDL; report pass/fail."""
   from __future__ import annotations
   import subprocess, sys, shutil, tempfile
   from pathlib import Path

   ROOT = Path(__file__).resolve().parents[1]
   V1 = ROOT / "benchmarks" / "v1"

   def main() -> int:
       if not shutil.which("ghdl"):
           print("ghdl not on PATH; install the OSS CAD Suite first.")
           return 2
       failures = []
       for ref in sorted(V1.glob("*/reference.vhd")):
           with tempfile.TemporaryDirectory() as d:
               r = subprocess.run(["ghdl", "-a", "--std=08", str(ref)],
                                  capture_output=True, text=True, cwd=d)
           status = "ok" if r.returncode == 0 else "FAIL"
           print(f"{status:4}  {ref.parent.name}")
           if r.returncode != 0:
               failures.append((ref.parent.name, r.stderr.strip()))
       print(f"\n{len(list(V1.glob('*/reference.vhd'))) - len(failures)} ok, "
             f"{len(failures)} failed")
       for name, err in failures:
           print(f"\n--- {name} ---\n{err}")
       return 1 if failures else 0

   if __name__ == "__main__":
       raise SystemExit(main())
   ```

2. Run it and read the failures:

   ```bash
   python scripts/verify_references.py
   ```

3. For each `FAIL`, open `benchmarks/v1/<id>/reference.vhd`, fix the reported
   error (common ones: a missing `;`, a type mismatch needing `resize()` or a
   `std_logic_vector`/`unsigned` cast, an out-of-range slice), and re-run the
   script until it prints `0 failed`. Fix the same design in
   `scripts/build_benchmarks.py` too, so a rebuild doesn't reintroduce the bug
   (the benchmark files are generated from that script).

4. Re-generate to confirm the script and the emitted files agree:

   ```bash
   python scripts/build_benchmarks.py
   python scripts/verify_references.py     # still 0 failed
   ```

5. (Optional but recommended) add a pytest that skips when GHDL is absent so CI
   without tools stays green but a local/Docker run enforces it. Create
   `tests/integration/test_reference_compiles.py`:

   ```python
   import shutil, subprocess, tempfile
   import pytest
   from pathlib import Path
   from hdleval.benchmarks.loader import load_suite, reference_hdl

   @pytest.mark.skipif(shutil.which("ghdl") is None, reason="ghdl not installed")
   @pytest.mark.parametrize("b", load_suite("v1"), ids=lambda b: b.id)
   def test_reference_compiles(b):
       code = reference_hdl(b)
       with tempfile.TemporaryDirectory() as d:
           p = Path(d) / "ref.vhd"; p.write_text(code)
           r = subprocess.run(["ghdl", "-a", "--std=08", str(p)],
                              capture_output=True, text=True, cwd=d)
       assert r.returncode == 0, r.stderr
   ```

6. Record results in `docs/EVALUATION.md` (which reference designs passed).
   Commit, push, open the PR, merge (shared wrapper).

**Acceptance criteria:** `python scripts/verify_references.py` prints `0 failed`;
the new test passes locally with GHDL installed and skips without it.

---

## Task 2 — Flip Ruff/mypy CI back to strict once code is clean

**Goal.** The CI currently runs Ruff and mypy as advisory (`continue-on-error:
true`). Clean the code so they pass, then make them gating again.

**Issue text.**
- Title: `Make Ruff and mypy strict in CI`
- Body: `Fix all Ruff lint/format and mypy issues, then remove 'continue-on-error' from the lint/type steps in .github/workflows/ci.yml so they gate the build.`

**Branch:** `chore/strict-ci`

**Steps.**

1. Auto-fix everything Ruff can, then format:

   ```bash
   source .venv/bin/activate
   ruff check --fix src tests scripts
   ruff format src tests scripts
   ruff check src tests scripts        # should now report "All checks passed!"
   ```

2. Run mypy and fix what remains (usually a handful of missing return-type or
   parameter annotations, or `X | None` handling):

   ```bash
   mypy src/hdleval
   ```
   Fix each reported line until mypy prints `Success: no issues found`.

3. Confirm tests still pass:

   ```bash
   pytest -q
   ```

4. Edit `.github/workflows/ci.yml` — remove the three `continue-on-error: true`
   lines and rename the steps back to gating:

   ```yaml
       - name: Ruff lint
         run: ruff check src tests scripts
       - name: Ruff format check
         run: ruff format --check src tests scripts
       - name: mypy
         run: mypy src/hdleval
   ```

5. Commit, push, open the PR. Watch the PR's CI run — the lint/type steps must
   now be green (not just advisory). Merge when green.

**Acceptance criteria:** `ruff check`, `ruff format --check`, and `mypy
src/hdleval` all pass locally; CI's lint/type steps are gating again and green.

---

## Task 3 — Add UART/SPI self-checking testbenches

**Goal.** Give the `comm_uart_tx` and `comm_spi_master` benchmarks real,
self-checking VHDL testbenches so their `simulation` stage actually runs under
GHDL instead of being `skipped`. This turns two hard communication-protocol
benchmarks into genuinely simulated designs.

**Issue text.**
- Title: `Add self-checking testbenches for UART TX and SPI master`
- Body: `Write GHDL testbenches for comm_uart_tx and comm_spi_master, wire testbench_path/testbench_entity into their benchmark.yaml, and confirm the reference designs pass simulation.`

**Branch:** `feat/uart-spi-testbenches`

**Background.** The hdleval harness already calls `simulate(design, tb,
tb_entity)` when a benchmark's `testbench_path` and `testbench_entity` are set
and GHDL is present (`src/hdleval/evaluation/harness.py`). A passing testbench
must print `ALL TESTS PASSED` on success and end with severity `failure` on a
mismatch (non-zero exit) — that's the contract the runner checks.

**Steps.**

1. Write `benchmarks/v1/comm_uart_tx/testbench.vhd`. It should instantiate
   `uart_tx`, drive `clk`/`rst`/`tick`/`start`/`data`, and check that the serial
   `tx` line produces the expected start/data(LSB-first)/stop framing. Skeleton:

   ```vhdl
   library ieee;
   use ieee.std_logic_1164.all;
   use ieee.numeric_std.all;

   entity uart_tx_tb is end entity;

   architecture tb of uart_tx_tb is
     signal clk, rst, tick, start, tx, tx_busy : std_logic := '0';
     signal data : std_logic_vector(7 downto 0) := (others => '0');
     constant BYTE : std_logic_vector(7 downto 0) := "10110010";
   begin
     dut: entity work.uart_tx
       port map (clk=>clk, rst=>rst, tick=>tick, start=>start,
                 data=>data, tx=>tx, tx_busy=>tx_busy);

     process
       variable errors : natural := 0;
       procedure step is begin
         clk <= '0'; wait for 5 ns; clk <= '1'; wait for 5 ns;
       end procedure;
     begin
       rst <= '1'; step; rst <= '0';
       data <= BYTE; start <= '1'; tick <= '1'; step; start <= '0';
       -- advance one bit at a time, sampling tx after each tick.
       -- expected sequence: start(0), BYTE LSB..MSB, stop(1).
       -- (fill in per-bit checks incrementing 'errors' on mismatch)
       if errors = 0 then
         report "ALL TESTS PASSED" severity note;
       else
         report integer'image(errors) & " vector(s) FAILED" severity failure;
       end if;
       wait;
     end process;
   end architecture;
   ```

   Fill in the per-bit checks. Because the UART is a state machine, you may need
   two `tick`s per bit depending on the reference's timing — iterate against
   GHDL until it prints `ALL TESTS PASSED`:

   ```bash
   cd benchmarks/v1/comm_uart_tx
   ghdl -a --std=08 reference.vhd testbench.vhd
   ghdl -e --std=08 uart_tx_tb
   ghdl -r --std=08 uart_tx_tb
   cd -
   ```

2. Do the same for `benchmarks/v1/comm_spi_master/testbench.vhd` (instantiate
   `spi_master`, drive `start`/`tx_data`/`miso`, check `sclk` toggling,
   MSB-first `mosi`, and `done` pulsing after 8 bits).

3. Wire the testbenches into metadata. Edit each `benchmark.yaml` to add:

   ```yaml
   testbench_path: testbench.vhd
   testbench_entity: uart_tx_tb        # (spi_master_tb for the SPI one)
   ```

   Also update `scripts/build_benchmarks.py` so a rebuild preserves these fields
   (add `testbench_path`/`testbench_entity` to the emitted metadata and write the
   `testbench.vhd` files), so the generator and the committed files stay in sync.

4. Confirm the harness now simulates them (with GHDL on PATH):

   ```bash
   hdleval run configs/experiments/rule-based-vs-baselines.yaml --out /tmp/o --db /tmp/o.sqlite
   # inspect the JSON: comm_uart_tx / comm_spi_master should show a 'simulation' stage
   # with status 'ok' for reference-golden instead of 'skipped'.
   ```

5. Commit, push, open the PR, merge.

**Acceptance criteria:** `ghdl -r` prints `ALL TESTS PASSED` for both
testbenches against their reference designs; both `benchmark.yaml` files
reference the testbench; the reference-golden model shows `simulation: ok` for
these two benchmarks when GHDL is installed.

---

## Task 4 — Publish the v0.1 GitHub release

**Goal.** Cut the first tagged release, `v0.1.0`, using the notes you already
wrote in `docs/releases/v0.1.0.md`.

**Issue text (optional — releases don't strictly need an issue).**
- Title: `Publish v0.1.0 release`
- Body: `Tag v0.1.0 and publish a GitHub release using docs/releases/v0.1.0.md as the notes.`

**Steps (do this from `main`, after the other PRs you want in the release are merged).**

1. Make sure `main` is current and clean:

   ```bash
   git checkout main && git pull origin main
   git status                          # should be clean
   ```

2. Confirm the version strings say `0.1.0` (they do): `pyproject.toml`
   (`version = "0.1.0"`) and `src/hdleval/__init__.py` (`__version__ = "0.1.0"`).
   If you bumped anything, commit it first.

3. Create the annotated tag and push it:

   ```bash
   git tag -a v0.1.0 -m "hdleval v0.1.0 — Prototype (HDL generation)"
   git push origin v0.1.0
   ```

4. Publish the release with your existing notes file as the body:

   ```bash
   gh release create v0.1.0 \
     --title "v0.1.0 — Prototype (HDL generation)" \
     --notes-file docs/releases/v0.1.0.md
   ```

   (If you'd rather attach artifacts too, add file paths at the end, e.g.
   `gh release create v0.1.0 ... publication/technical-report/TECHNICAL_REPORT.md`.)

5. Verify:

   ```bash
   gh release view v0.1.0
   ```
   It should appear at `https://github.com/urecheM/ai-fpga-engineer/releases`.

**Permission note.** Publishing a release via `gh` needs the token's **Contents:
Read and write** (which you already have). If `gh release create` reports a
permission error, publish from the web UI instead: repo → Releases → "Draft a
new release" → choose tag `v0.1.0` → paste the contents of
`docs/releases/v0.1.0.md` → Publish.

**Acceptance criteria:** a `v0.1.0` tag exists on `main`, and a published release
with the v0.1.0 notes appears on the repo's Releases page.

---

## Suggested order

1. **Task 2 (strict CI)** — quick, makes every later PR cleaner.
2. **Task 1 (GHDL-verify references)** — unblocks real simulation.
3. **Task 3 (UART/SPI testbenches)** — builds on Task 1's verified designs.
4. **Task 4 (release)** — cut once 1–3 are merged, so v0.1.0 captures them.
