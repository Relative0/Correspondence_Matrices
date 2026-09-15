# Maintained Windows pytest profile

The `windows-supported` profile gives routine Windows development a green-or-actionable test signal without editing or concealing historical evidence. It is bound to the exact September 14 nonpassing baseline and the September 15 isolated-module readiness audit.

Run the complete supported profile from the repository root with a new temporary directory name:

```powershell
& '.venv/Scripts/python.exe' -B -m pytest tests -q -p no:cacheprovider --cm-profile=windows-supported --basetemp=tmp/windows-supported-001
```

Validate or inspect the inventory without running the suite:

```powershell
& '.venv/Scripts/python.exe' -B scripts/cm_windows_pytest_profile.py verify
& '.venv/Scripts/python.exe' -B scripts/cm_windows_pytest_profile.py show
```

## Categories

- **Active supported tests** are every collected test under `tests/` after the other two categories are removed. Any new failure, error or collection problem fails the profile normally.
- **Optional dependency or platform refusals** are nine whole modules established by the isolated Windows audit: seven require optional PyTorch, one imports the Unix-only `resource` module and one fully skips without the optional CUDD binding. They are ignored before import so their absence cannot abort supported collection. The command-line inventory keeps every reason visible.
- **Immutable historical replay gates** are the exact 76 nonpassing test IDs and expected outcome kinds in the September 14 baseline. They remain available to ordinary unprofiled pytest and their evidence is untouched. The supported profile deselects those exact IDs after collection while continuing to run passing tests from the same modules.

The profile fails closed if an audit hash changes, an expected module disappears, a historical selector no longer collects, the category counts change or the two categories overlap. The September 14 JSON uses a newline-canonical SHA-256 because it predates the repository's exact-byte `.gitattributes` rules and can be checked out as LF or CRLF; all other bytes must match. The September 15 JSON uses its raw SHA-256. Validation only reads these files. A test rename or repaired historical gate therefore requires a successor audit and an intentional profile update; do not update hashes merely to make the profile green.

## CI scope

The repository's `research-checks.yml` workflow is a focused cross-platform evidence gate with a 15-minute job limit and a deliberately smaller dependency set. It validates this profile's bindings and helper logic on both operating systems. The complete `windows-supported` command remains the local maintained suite because the existing CI environment does not install the full optional research stack and its prior broad Windows runtime was about twelve minutes before setup.

Running `pytest` without `--cm-profile` retains the repository's original behavior. That unprofiled run includes historical gates and may collect optional modules; use it for deliberate full replay investigations rather than routine change validation.
