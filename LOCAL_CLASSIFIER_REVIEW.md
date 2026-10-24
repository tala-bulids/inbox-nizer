# inbox-nizer local classifier review

From the project folder, run:

```powershell
.\env\Scripts\python.exe -m quality.local_classifier_review
```

Open the private `http://127.0.0.1:8765/#...` URL printed in the terminal. Enter your reviewer name once. Click a label to save and advance; Ambiguous saves `ambiguous=yes` with an empty label. Skip does not label the email. Previous lets you inspect or correct earlier choices. At the end, Review remaining returns to unfinished items. Stop with Ctrl+C; run the same command to resume.

Place your authorized development export at the default path below, or pass `--csv` with another development.csv path. The screen updates that file directly:

`private_review/development.csv`

The tool selects up to 50 development emails from your local export. Selection interleaves Finance/Business, Business/Job Application, Newsletter/Promotion, high-confidence category-boundary cues and mixed Arabic/English. Heuristics identify useful review candidates, not proven errors. Existing prediction labels and scores remain hidden. This diagnostic queue is not a representative accuracy benchmark.

Each label/Ambiguous click writes `gold_label`, `ambiguous`, `reviewer`, `label_source=human_reviewed`, and `reviewed_at` (UTC `YYYY-MM-DD`). Missing review columns are added on the first human save. All original email fields, IDs, notes and other rows are retained. Writes use a temporary file followed by atomic replacement; the first save also creates `development.before-local-review.csv.backup` beside the CSV. Close Excel or other editors before reviewing. An external change is rejected rather than silently overwritten; reload the screen to read it.

Queue order, position and skips persist in Git-ignored `private_review/classifier-ui/`. Reviewer name is remembered only in this local browser when browser storage is available; otherwise it stays in the current tab and can be re-entered after reload. Blocked storage never prevents reviewing. Email contents and answers are not put in browser storage. The completed counter comes from the saved CSV. Save confirmation appears only after the server finishes writing. On an error, reload to verify saved progress before continuing.

The standalone Python standard-library server binds only to `127.0.0.1`, requires a per-run access token, and makes no outbound requests. Email bodies are displayed as plain text; remote images and HTML are not loaded. It has no database/model imports, does not modify production predictions, and never opens or writes `holdout.csv`. The manifest is used only to select metadata for development IDs. Nothing is uploaded, staged, committed or pushed.

Focused synthetic verification:

```powershell
.\env\Scripts\python.exe -m unittest quality.test_local_classifier_review -v
```
