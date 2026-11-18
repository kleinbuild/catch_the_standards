Review sheets

These sheets list the links and pairings that most need a teacher's judgment, most doubtful first (priority 1, then 2). They do not list everything. A link that is not on a sheet stays in the database as it is, unreviewed.

To mark a row, fill in two cells:

- `decision`: `keep` or `reject`.
- `reviewed`: change `0` to `1`. A decision counts only when `reviewed` is `1`, so a row can be left half-thought with a decision written and `reviewed` still `0`.

`confidence` is optional: `low`, `medium` or `high`, for how sure you are of a link you keep. Leave it blank when you have no view. It is stored on the link when the row has `reviewed` set to `1` and is shown beside the link in the interface. On `pairings.csv` and `eld_ela_notes.csv` it is recorded only, like the decision.

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

Search terms, in `data/curated/search_terms.csv` (one folder up, not a review sheet): pairs of a word teachers use and the word the standards use for the same thing, such as `regroup` and `decompose`. The prototype's search uses them to find more standards, and says so beside each result found that way. They are never links between standards. The rows Claude suggested have `source` `claude`, `reviewed` `0`, and the evidence for each pair. To accept one, change `reviewed` to `1`. To add your own, add a row at the end with `source` `owner`. `subject` is `math`, `ela` or `eld` when the pair holds only in that subject (`compose` means regrouping in math, not in writing), or blank. Rebuild afterwards with `python src/load.py` and `python scripts/make_prototype_data.py`.
