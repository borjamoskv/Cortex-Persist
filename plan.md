1. **Refactor `LineageVerifier.get_lineage` in `cortex/core/lineage.py`**
   - Use `replace_with_git_merge_diff` to replace sequential asynchronous calls (`for pid in parent_ids: ... await ...`) with concurrent execution using `asyncio.gather`.
   - Update `_cache` handling to allow concurrent lookups without race conditions or cyclic recursion loops.

2. **Verify changes to `cortex/core/lineage.py`**
   - Run `cat cortex/core/lineage.py` to confirm changes are correctly applied.

3. **Refactor `MemoryArchaeologist._build_clusters` in `cortex/memory/memory_archaeology.py`**
   - Use `replace_with_git_merge_diff` to replace the nested python loop iterating over the O(N^2) similarity matrix to find clusters.
   - Use `np.where` or boolean indexing to find neighbors and construct clusters without nested loops.

4. **Verify changes to `cortex/memory/memory_archaeology.py`**
   - Run `cat cortex/memory/memory_archaeology.py` to confirm changes are correctly applied.

5. **Write tests for `lineage` and `archaeology` modifications**
   - Create a new file `tests/test_refactored_logic.py` using `write_file` or bash.
   - The test will construct dummy `engine` objects and call `LineageVerifier.get_lineage` directly to ensure correct concurrent execution and caching logic.
   - The test will also call `_build_clusters` with a mocked similarity matrix to ensure proper cluster building logic without N^2 nested loops.

6. **Run tests**
   - Run `python -m pytest tests/test_refactored_logic.py` to verify the modified logic is sound.

7. **Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.**
   - Call `pre_commit_instructions` and follow them (e.g. running `ruff check`, `ruff format`).

8. **Submit the change.**
   - Commit with a descriptive message and submit.
