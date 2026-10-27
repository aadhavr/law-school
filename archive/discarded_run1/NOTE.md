# Discarded first run of Step 3 (2026-10-24). Do not cite these files.

The first version of `code/step3_test_A.py` wrote these files on 2026-10-24. That version did not follow PREREG.md:

1. **States model.** X_it included a chamber term (lower/upper). It came from the original task text, but PREREG.md lists no chamber term.
2. **Three extra models** that PREREG.md does not list, saved in `step3_sensitivity.csv`:
   - seniority + seniority² (House, Senate, States)
   - outcome log(1 + LES) (House, Senate, States)
   - States without a chamber term

The script was rewritten to use the PREREG X_it exactly. The current results are in `output/step3_*`. In these files, House and Senate κ match the current run, because only the States model changed. None of these numbers are reported in the post. The version of the code that produced them was overwritten and is not kept.

The files were moved here unchanged from a scratch folder.
