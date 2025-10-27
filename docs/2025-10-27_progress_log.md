# Project Log: ComplianceRAG

**Date:** 2025-10-27

## Subject: CPU-First Refactoring and Dependency Cleanup

### Summary

This log entry details the refactoring efforts to make the ComplianceRAG project CPU-first and to clean up heavy GPU/CUDA and `transformers`/`accelerate` dependencies. The goal was to reduce the project's footprint for runtime and CI while preserving existing functionality and test stability.

### Key Changes

1.  **`requirements.txt` Update:**
    *   Removed `transformers` and `accelerate` from the dependency list.
    *   Ensured `torch` is explicitly pinned to the CPU wheel (`torch --index-url https://download.pytorch.org/whl/cpu`).
    *   The updated `requirements.txt` now reflects a minimal, CPU-first dependency set.

2.  **Codebase Review for `transformers`/`accelerate`:**
    *   A thorough search of the `src/` directory and root Python files (`ingestion_service.py`, `main.py`) was conducted for direct imports or uses of `transformers` or `accelerate`.
    *   No direct uses were found, indicating that `sentence-transformers` was already handling embedding generation as intended. Therefore, no code modifications were required for conditional imports or fallbacks.

3.  **`README.md` Update:**
    *   The `README.md` file was updated to include an explicit "CPU-First Installation (Torch)" section under "Notes for Future Developers (Human or AI)".
    *   This section provides the official PyTorch stable find-links CPU install command and guidance on how to re-enable GPU support if needed.

4.  **CI/Install Scripts:**
    *   No other CI or install scripts attempting to fetch CUDA-specific wheels or NVIDIA runtime packages were identified in the project structure beyond `requirements.txt`. The changes to `requirements.txt` address this aspect.

### Verification

The full test suite (`pytest`) was executed within the virtual environment after all changes were applied.
*   **Result:** All 7 tests passed successfully.
*   **Impact:** No test failures occurred due to the removal of `transformers` or `accelerate`, and no mocking or stubbing was required to maintain test stability. This confirms that the project's core functionality was not dependent on these heavy libraries for its current implementation.

### Status

The CPU-first refactoring and dependency cleanup are complete. The project now has a lighter dependency footprint, is optimized for CPU environments by default, and maintains full functional and test stability.
