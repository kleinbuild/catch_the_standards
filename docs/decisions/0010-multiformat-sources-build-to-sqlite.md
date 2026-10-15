0010 Keep PDFs, images, and extracted text as files in git; the build packages them into SQLite

Status: proposed, 2026-10-14

Extend 0007 to sources that are not CSVs. Coherence maps and standards progressions documents come as PDFs with long text and embedded images. Keep them as files, and let `src/load.py` package them into the same `standards.db` the app ships.

Layout:
- `data/raw/`: original PDFs and CSVs, as downloaded.
- `data/extracted/<doc>/`: each PDF converted to markdown, with its images in a folder beside it. The owner's earlier PDF extraction tool already writes images to their own folder; not yet tried on these documents.
- `data/raw/sources.csv`: one row per document with title, original URL, download date, and file hash. The hash shows when a file has changed and catches the same document added twice. The URL lets any text or image in the app link back to its original.

The build writes text chunks (document, page, section, text) and image paths into `standards.db`. Images stay as files and ship in a folder next to the database, not inside it.

MongoDB as the master store was considered and not chosen. It runs as a server and stores data in a form git cannot diff, which loses what 0007 keeps: readable history of the owner's reviewed work, and repair by fixing inputs and rebuilding. A vector database as master was not chosen either, because embeddings are produced by a script from the text and are build output, not source.

`load.py` runs on the owner's machine when sources change, not when the app opens. The shipped app only reads `standards.db`. Each build deletes and recreates the database, so it contains exactly what the source files contain; updating in place is how leftover and duplicate rows accumulate. At this size the rebuild takes seconds. Embeddings would be the slowest step and could be reused for chunks whose text is unchanged.

Each build should write its date and a version into a metadata table in `standards.db`, so any installed copy shows which build it is.

Not decided:
- Markdown or JSON for chunk data. Markdown for extracted prose; JSON or CSV likely for the chunk table.
- Whether large PDFs and images go in git, in Git LFS, or stay out of git with only URL and hash recorded.
- Whether a server (e.g. FastAPI) is needed. Depends on how teachers open the app; SQLite alone needs none.
- Whether coherence maps and progressions documents may be redistributed inside the package (licensing open question in CLAUDE.md). Linking to the original is the fallback.

CLAUDE.md Layout needs `data/extracted/` added if this is accepted.
