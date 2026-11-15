-- schema.sql - tables for data/build/standards.db
--
-- The database is build output (decision 0007). src/load.py deletes it and
-- recreates it from data/raw/ every time, so nothing here is ever edited by hand.
--
-- STRICT makes SQLite enforce the column types below. Without it SQLite will
-- store text in an INTEGER column without complaint.

-- One row per fact about the build, so any copy of the database can say what it is.
CREATE TABLE build_info (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
) STRICT;

-- The files this build was made from. sha256 is a fingerprint of the file's
-- bytes: if two builds list the same fingerprint, they read the same file.
CREATE TABLE source_files (
    subject       TEXT NOT NULL,
    file_name     TEXT NOT NULL,
    sha256        TEXT NOT NULL,
    record_count  INTEGER NOT NULL,
    PRIMARY KEY (subject, file_name)
) STRICT;

-- CDE's filter codes for the three loaded subjects, from docs/reference/codes.csv.
-- Codes belong to one subject page and are not shared across subjects (0002).
CREATE TABLE filter_codes (
    subject  TEXT NOT NULL,
    param    TEXT NOT NULL,      -- c0, c1, c2, c3
    level    TEXT NOT NULL,      -- the field label this level filters, e.g. Cluster
    code     INTEGER NOT NULL,
    label    TEXT NOT NULL,
    PRIMARY KEY (subject, param, code)
) STRICT;

-- A code that should be read as another code (0003).
CREATE TABLE cluster_alias (
    subject     TEXT NOT NULL,
    code        INTEGER NOT NULL,
    alias_code  INTEGER NOT NULL,
    reason      TEXT NOT NULL,
    PRIMARY KEY (subject, code)
) STRICT;

-- One row per CDE record (0011). record_id is the number in /cacs/id/web/<n>
-- and is the only key other tables use. identifier is NOT unique: A-CED.1 is
-- five records (one per course) and Calculus.16.0 is two different standards.
CREATE TABLE standards (
    record_id            INTEGER PRIMARY KEY,
    url                  TEXT NOT NULL,
    subject              TEXT NOT NULL CHECK (subject IN ('math', 'ela', 'eld')),

    identifier           TEXT NOT NULL,   -- exactly as CDE writes it
    identifier_norm      TEXT NOT NULL,   -- en dashes as hyphens, nothing else changed (0012)
    -- Filled only for the few identifiers CDE got wrong, from
    -- data/curated/identifier_corrections.csv. The id_ parts below are then
    -- read from this instead of identifier_norm.
    identifier_corrected TEXT,

    grade_label          TEXT NOT NULL,   -- as written: K, 5, 9–10
    grade_min            INTEGER NOT NULL CHECK (grade_min BETWEEN 0 AND 12),   -- 0 = TK & K (0004)
    grade_max            INTEGER NOT NULL CHECK (grade_max BETWEEN grade_min AND 12),

    -- Field labels as shown on the record. Which ones are filled depends on the subject.
    subject_area         TEXT,            -- ELA
    domain               TEXT,            -- ELA, math
    cluster              TEXT,            -- ELA, ELD: a short label. Math's cluster is text_cluster.
    cluster_code         INTEGER,         -- CDE's code for that label
    cluster_code_merged  INTEGER,         -- the same after cluster_alias; use this one for grouping
    discipline           TEXT,            -- high school math course
    conceptual_category  TEXT,            -- high school math
    critical_principle   TEXT,            -- ELD
    proficiency_level    TEXT,            -- ELD: Emerging, Expanding, Bridging
    content_strand       TEXT,            -- ELD

    -- Text sections, as written.
    text_cluster         TEXT,            -- math only
    text_standard        TEXT NOT NULL,
    text_footnote        TEXT,
    -- All sections joined, with the minus sign and en dash as hyphens, so a
    -- search typed on a keyboard finds both ways CDE writes subtraction (0012).
    text_search          TEXT NOT NULL,

    -- Parts read from the identifier (0005). All NULL when id_parsed = 0.
    id_parsed            INTEGER NOT NULL CHECK (id_parsed IN (0, 1)),
    id_strand            TEXT,            -- ELA strand (L), math domain (NF, A-CED, Calculus), ELD part (PI)
    id_grade             TEXT,            -- K, 5, 9-10. NULL for high school math, which has no grade in it.
    id_number            TEXT,            -- 1, 12, 3.1, 16.0
    id_letter            TEXT,            -- a in 5.NF.3.a or ELD 12a
    id_level             TEXT,            -- ELD only: Em, Ex, Br
    parent_identifier_norm TEXT,          -- math sub-item records: 5.NF.3.a -> 5.NF.3. The parent may have no record.

    -- Facts about the text, not interpretations.
    ca_marker            INTEGER NOT NULL CHECK (ca_marker IN (0, 1)),      -- the word "CA" appears in text_standard
    has_asterisk         INTEGER NOT NULL CHECK (has_asterisk IN (0, 1)),   -- "*" appears in text_standard
    -- The whole text is a bracketed note such as "(Begins in grade 2)": CDE
    -- lists the identifier but there is no standard at this grade.
    is_placeholder       INTEGER NOT NULL CHECK (is_placeholder IN (0, 1)),

    source_file          TEXT NOT NULL,
    source_page          INTEGER NOT NULL  -- results page the scraper read the record from
) STRICT;

CREATE INDEX idx_standards_identifier_norm ON standards (identifier_norm);
CREATE INDEX idx_standards_progression ON standards (subject, id_strand, id_number, grade_min);

-- Lettered parts inside one record's text (a., b., c.). In ELA these are not
-- CDE records, so they have no record ID of their own: the key is the
-- record plus the letter.
CREATE TABLE sub_items (
    record_id     INTEGER NOT NULL REFERENCES standards (record_id),
    letter        TEXT NOT NULL,
    text          TEXT NOT NULL,
    ca_marker     INTEGER NOT NULL CHECK (ca_marker IN (0, 1)),
    has_asterisk  INTEGER NOT NULL CHECK (has_asterisk IN (0, 1)),
    PRIMARY KEY (record_id, letter)
) STRICT;

-- Corrections to identifiers CDE published wrongly, with the evidence for each.
CREATE TABLE identifier_corrections (
    record_id             INTEGER PRIMARY KEY REFERENCES standards (record_id),
    identifier            TEXT NOT NULL,   -- as CDE writes it
    corrected_identifier  TEXT NOT NULL,
    evidence              TEXT NOT NULL,
    source                TEXT NOT NULL,
    reviewed              INTEGER NOT NULL CHECK (reviewed IN (0, 1))
) STRICT;

-- Directed links between records (0006). from_record_id comes earlier: it is
-- the lower grade, the lower proficiency level, or the standard that builds
-- towards the other.
--   type            source             made by
--   next_grade      structural         the loader: same strand and number, next grade (ELA, ELD)
--   next_level      structural         the loader: ELD Emerging -> Expanding -> Bridging
--   builds_towards  learning_commons   data/derived/learning_commons_edges.csv
-- reviewed is 1 only where the owner has confirmed the link.
CREATE TABLE edges (
    from_record_id  INTEGER NOT NULL REFERENCES standards (record_id),
    to_record_id    INTEGER NOT NULL REFERENCES standards (record_id),
    type            TEXT NOT NULL,
    source          TEXT NOT NULL,
    note            TEXT,
    reviewed        INTEGER NOT NULL CHECK (reviewed IN (0, 1)),
    PRIMARY KEY (from_record_id, to_record_id, type, source),
    CHECK (from_record_id <> to_record_id)
) STRICT;

CREATE INDEX idx_edges_to ON edges (to_record_id);
