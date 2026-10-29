# DATA_NOTES.md: Step 1 inventory

All counts below come from Python (pandas 2.3.3) reads of the raw files, run 2026-10-24. No file was edited.

**The codebook PDF is not in this directory.** I searched again on 2026-10-24, after being told it had been added, and still found nothing. Originally I searched the whole directory with `find` for `*.pdf` and `*codebook*` and found nothing. (`lockdowns/` holds an unrelated Stata project.) The state-file variable meanings below are inferred from their names and values. They need checking against the codebook.

---

## 1. `CELHouse93to118-REVISED-06.26.2025.xlsx` (U.S. House)

- **Sheet:** `Sheet1`. **Rows:** 11,606 member-Congress rows. **Columns:** 88.
- **Headers:** row 1 holds long descriptive labels, not short variable names (for example `"1 = Democrat"`, `"Seniority, number of terms served counting current"`). Some labels repeat, and pandas adds a `.1` suffix to the second copy.
- **Years:** Congresses 93–118 (26 Congresses). `Year at start of Congress` runs 1973–2023. Each Congress has 442–454 rows, including delegates and mid-term replacements.
- **Member ID:** `ICPSR number, according to Poole and Rosenthal`. It has 2,222 unique values and 127 missing. The missing rows are the non-voting delegates (Fauntroy/DC, Won Pat/Guam, de Lugo/USVI, Benitez/PR, and others). All 101 apparent duplicate ID-by-Congress pairs come from those missing IDs. With missing IDs dropped, there are 0 duplicates. Other ID-like fields: `Name in bioguide`, `Legislator name, as given in THOMAS`, and a row counter.
- **LES columns:**
  - `LES 1.0`: filled for all 11,606 rows, Congresses 93–118. Mean 1.000. Var(LES) = σ² = 2.226. Range 0–18.686.
  - `LES 2.0`: **filled for only 902 rows, Congresses 117–118.** Mean 1.000. σ² = 1.012. Range 0–7.142.
  - The LES 2.0 inputs (the 15 "inc in other leg vehicles" / `.1` bill-stage counts) are also limited to Congresses 117–118. I cannot rebuild LES 2.0 for earlier Congresses from this file.
  - Related columns: `Lagged LES 1.0` (Congresses 94–118, n = 9,320), `Lagged LES 2.0` (Congress 118 only, n = 365), `LES 2.0 Benchmarks`, `LES2.0/Benchmark2.0`, the classic benchmark and ratio, and rank-within-party columns.
- **Covariates for X_it:** `Seniority, number of terms served counting current`; `1 = Democrat` and the party code (`100=Dem, 200=Rep, Other`); `1 = majority party member`; `1 = committee chair, according to Almanac of American Politics`; subcommittee chair; power committee; majority and minority leadership; Speaker; vote percentage; DW-NOMINATE scores and their distances from the floor and party medians.
- **Background variables:** `1 = female`, `1 = African American`, `1 = Latino/a`, `Year born`, `1 = served in state legislature`, `state_leg * state legislature professionalism`, `Year first elected to House`, and the size of the state delegation.

## 2. `CELSenate93to118.xls` (U.S. Senate)

- **Sheet:** `Sheet1`. **Rows:** 2,635. **Columns:** 88. Row 1 holds descriptive labels, as in the House file.
- **Years:** Congresses 93–118 (26). `year elected for congress` runs 1972–2022. This year appears to be the election year, one year before the Congress starts, which is a different convention from the House file. Each Congress has 100–106 rows.
- **Member ID:** `icpsr number`. It has 420 unique values, 0 missing, and 0 duplicate ID-by-Congress pairs. `Name in bioguide` is also present.
- **LES columns:**
  - `LES Classic, not including incorporation in other legislative vehicles` (= LES 1.0): filled for all 2,635 rows, Congresses 93–118. Mean 1.000. σ² = 1.022. Range 0–10.823.
  - `LES 2.0`: **filled for only 202 rows, Congresses 117–118.** Mean 1.000. σ² = 1.205. Range 0.018–10.648. Its inputs are also limited to 117–118.
  - Oddity: `LES 2.0 Rank within Party` is filled for all 2,635 rows (93–118), but `LES 2.0` exists only for 117–118. Before 117 this column is probably the rank on LES Classic. This needs checking.
  - `Lagged LES 1.0` covers Congresses 94–118 (n = 2,214). `Lagged LES 2.0` covers Congress 118 only (n = 92).
- **Covariates for X_it:** `seniority`, `seniority squared`, `1 if senator is democrat`, the party code, `1 if senator is in majority party`, `1 if senator is a committee chair`, subcommittee chair, power committee, leadership, freshman, vote share, and DW-NOMINATE scores.
- **Background variables:** female, African American, Latino, `Year born`, `1 if senator ever served in state legislature`, `state_leg X squire index`, and `year first elected to the senate`.

## 3. `sles_all_50_states_202609.csv` (State Legislative Effectiveness Scores)

- **Rows:** 102,285 legislator-term-chamber rows. **Columns:** 37, with short names.
- **Coverage:** all 50 states, both chambers (`upper` and `lower`). Nebraska is unicameral, and its `party` = `N` (476 rows) is probably the nonpartisan code. Terms run from 1987_1988 (ME) to 2024_2025 (NJ, VA). The `term` variable has 49 distinct strings, and they are uneven: odd-year sessions (NJ, VA, LA, MS) and 4-year spans (`1995_1998`, `2019_2022`, and others). Coverage varies a lot by state. Kansas has 3 terms (2019–2024). Maine has 19.
- **Member ID:** `sles_id`. It has 27,583 unique values and is never in more than one state. 2,571 IDs appear in both chambers, and 314 ID-by-term pairs appear in both chambers in the same term (a member who switched chambers mid-term). ID-by-term-by-chamber is unique. Terms per ID: median 3, mean 3.7, max 18.
- **LES column:** only one, `SLES`. **The state file has no LES 1.0 / LES 2.0 split.** Mean 1.0 within each state-chamber-term. Overall σ² = 1.238. Related columns: `SLES_rank`, `SLES_rank_in_party`, `bm` (benchmark), `SLES_ratio`, `SLES_ratio_level`.
- **Bill-stage counts:** `all_*`, `ss_*` (substantive and significant), `s_*` (substantive), and `c_*` (commemorative), each × bills / aic / abc / pass / law. These are probably action in committee, action beyond committee, passed chamber, and became law. The codebook should confirm this.
- **Covariates for X_it:** `party` (D / R / I / 3rd / N), `in_majority` (1 missing), `comm_chair` (stored as text: `0` / `1` / `.`, with 1,629 rows `.` and 28 NaN), `seniority`, `chamber`.
- **Background variables:** none. The file has no gender, race, birth year, or prior-office fields.

---

## Degree or occupation variable?

**No. None of the three files has a variable for education, law degree, or prior occupation.** I checked every column name above. Step 4 (skill source) and Claim C therefore need an outside merge. Possible keys:
- Congress: ICPSR number or bioguide name → Bioguide biographies or a Congress-member education dataset.
- States: `sles_id` has no crosswalk in the file. A merge would have to match on name + state + term (for example, to Ballotpedia or Open States data). Expect error from that matching.

## Issues to settle before modeling

1. **LES version.** *User decision, 2026-10-24: LES 1.0 for House and Senate, `SLES` for states.* LES 2.0 covers only 2 Congresses (117–118). That leaves at most 2 terms per member. This gives a very weak basis for separating α_i from ε_it, and it cannot support the out-of-sample "terms before t" check. LES 1.0 covers all 26 Congresses. The state file has a single SLES.
2. Senate year variable is the election year. Use Congress number as t.
3. Drop House delegates (missing ICPSR) or give them a placeholder ID.
4. State `comm_chair = "."` needs a rule (set to missing or to 0). The codebook should say.
5. State members who served in both chambers: is α_i one effect per person, or one per person-chamber?
6. LES is scaled to mean 1 within each Congress or state-chamber-term. So the levels are relative within a session, and pooled variance mixes chambers with different σ².

## ABA "Enrollment and Degrees Awarded 1963 - 2010" (`data/raw/stats_1.authcheckdam.pdf`)
- Placed by the user on 2026-10-29. The macOS download attribute says it came from https://claude.ai/ (Brave), so it is not confirmed as the americanbar.org original. PDF metadata: Author "aba", made with Acrobat PDFMaker 8.1 for Excel on 2011-08-26. It has a text layer and is not a scan; both pages are rotated 90°.
- `code/aba_extract.py` writes `data/derived/aba_jd_awarded.csv`: 47 academic years, from "1963 - 1964" to "2009 - 2010", with labels kept as printed. Parsing checks: male + female = total for first-year and J.D. enrollment in every row; no gaps; no duplicates.
- PDF note: J.D./LL.B. degrees are "those awarded by approved schools for the academic year ending in the first year stated". So the row "2009 - 2010" counts degrees for the year ending in 2009. No year has been shifted.
- Column header: "J.D. or LL.B Awarded". The early years may include LL.B. degrees.
