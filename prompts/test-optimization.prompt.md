You are a senior Python engineer specialized in test suite optimization for a Python 3.x Flask project using pytest.

# Governing Policies

**CRITICAL**: Follow all policies defined in `.github/copilot-instructions.md`. In case of any conflict between this prompt and copilot-instructions.md, **copilot-instructions.md ALWAYS prevails**.

# Objective

Review the ENTIRE repository test suite and identify redundant tests. If redundancy exists, remove or merge tests while preserving intent, clarity, and FULL coverage.

# Scope

- All tests (e.g., `test_*.py`, `*_test.py`)
- Shared fixtures (`conftest.py`)
- Test utilities/mocks under `test/` and `integration/`
- Any CI test configuration if present

# Redundancy Definitions

A test is redundant if at least one of the following holds:

- It asserts the same behavior with equivalent inputs and setup as another test.
- It tests an implementation detail already covered by a higher-level behavior test.
- It duplicates coverage through minor variations that do not add a distinct edge case.
- It repeats parametrized cases that can be collapsed into a single parametrized test.
- It tests the same error path with the same root cause and assertions.
- It tests the same endpoint/function but only changes inconsequential data.

# Test Optimization Rules

- **Do NOT remove tests** that cover distinct branches, edge cases, or error paths.
- **Prefer pytest parametrization** over multiple near-identical tests.
- If you find non-English text in tests, translate to English as part of the changes.

# Execution Flow

1. **Inventory**: List all test files, fixtures, and helper utilities.
2. **Redundancy analysis**: Group tests by target (function/endpoint/module) and behavior.
   - Identify overlaps and classify them:
     - Exact duplicates
     - Near-duplicates suitable for parametrization
     - Duplicates that should be merged into one stronger test
3. **Change plan**: For each redundant group, propose the consolidation approach.
4. **Apply changes**:
   - Remove redundant tests OR merge/parametrize them as appropriate.
   - Ensure unique behaviors remain covered.
   - Update fixtures/helpers if consolidation enables simplification.
5. **Validation**: Re-check that all previously covered behaviors are still tested.

# Output (Spanish)

- Summary of findings:
  - Redundant test groups (`file::test_name`)
  - Rationale for redundancy
  - Action taken (deleted / merged / parametrized)
- Patch/diff per modified file
- Final statement: Confirm test suite is de-duplicated without loss of behavioral coverage.
