Review sheets

These sheets list the links and pairings that most need a teacher's judgment, most doubtful first (priority 1, then 2). They do not list everything. A link that is not on a sheet stays in the database as it is, unreviewed.

To mark a row, fill in two cells:

- `decision`: `keep` or `reject`.
- `reviewed`: change `0` to `1`. A decision counts only when `reviewed` is `1`, so a row can be left half-thought with a decision written and `reviewed` still `0`.

`owner_note` is free text, for anything worth remembering about the decision.

Do not change, delete, or reorder the other cells or the rows. The record IDs at the right of each row are how the decision finds its link.

What a decision does when the database is rebuilt (`python src/load.py`):

| Sheet | keep | reject |
|---|---|---|
| `ela_links.csv`, `eld_links.csv`, `math_links.csv` | the link is marked reviewed | the link is left out of the database |
| `math_link_candidates.csv` | the pair is added as a link, source `owner`, reviewed | nothing; the pair was never loaded |
| `pairings.csv`, `eld_ela_notes.csv` | recorded only | recorded only |

The last two are recorded but not yet acted on. Rejecting a pairing, or an ELD note, means the join with Learning Commons needs changing, which is done in `scripts/join_learning_commons.py` and not by the loader.

Opening the sheets: they are UTF-8 CSV files. LibreOffice asks for the character set on opening; choose Unicode (UTF-8) and comma as the separator. Save in the same format (Keep Current Format).

`scripts/make_review_sheets.py` wrote these sheets. Run again, it adds new rows to the end of a sheet and leaves every existing row alone.
