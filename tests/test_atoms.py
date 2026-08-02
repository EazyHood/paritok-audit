# SPDX-License-Identifier: Apache-2.0
"""The measurement has to be trustworthy before the numbers mean anything."""

from paritok_audit.atoms import (
    COMMAND,
    ERROR,
    IDENTIFIER,
    NUMBER,
    PATH,
    URL,
    extract,
    measure,
)

TRACEBACK = '''$ pytest tests/test_db.py -k commit
Traceback (most recent call last):
  File "app/db/session.py", line 214, in commit
    self._flush_pending(conn)
sqlalchemy.exc.IntegrityError: duplicate key 0x1f4 violates constraint
Retrying against https://api.internal/v2/orders -- HTTP 409
'''


def _texts(atoms, category=None):
    return {a.text for a in atoms if category is None or a.category == category}


def test_extracts_the_facts_an_agent_needs():
    atoms = extract(TRACEBACK)
    assert "app/db/session.py" in _texts(atoms, PATH)
    assert "IntegrityError" in _texts(atoms, ERROR)
    assert "0x1f4" in _texts(atoms, NUMBER)
    assert "214" in _texts(atoms, NUMBER)
    assert "https://api.internal/v2/orders" in _texts(atoms, URL)
    assert any("pytest" in t for t in _texts(atoms, COMMAND))


def test_path_swallows_its_own_tail():
    """`session.py` must not be counted again once the full path is an atom.

    Double-counting would inflate the denominator and flatter any compressor
    that keeps the full path.
    """
    atoms = extract(TRACEBACK)
    assert "session.py" not in _texts(atoms)
    assert "app/db/session.py" in _texts(atoms)


def test_atoms_are_literal_substrings():
    """Retention must stay decidable by exact search -- no paraphrase, ever."""
    for atom in extract(TRACEBACK):
        assert atom.text in TRACEBACK, atom


def test_prose_summary_scores_zero():
    """The failure mode the compression ratio hides."""
    summary = "A database commit failed due to a unique constraint violation."
    result = measure(TRACEBACK, summary)
    assert result.rate == 0.0
    assert result.total > 5


def test_identity_scores_one():
    result = measure(TRACEBACK, TRACEBACK)
    assert result.rate == 1.0
    assert not result.lost


def test_matching_is_case_sensitive():
    """An agent that reads `getUserId` cannot call `getuserid`."""
    src = "call getUserId(payload) in api/user_service.js"
    result = measure(src, src.lower())
    assert "getUserId" in {a.text for a in result.lost}


def test_empty_input_is_not_a_crash():
    assert extract("") == []
    assert measure("", "").rate == 1.0


def test_partial_loss_is_reported_per_category():
    kept_paths_lost_numbers = 'File "app/db/session.py" in commit, IntegrityError'
    result = measure(TRACEBACK, kept_paths_lost_numbers)
    by_cat = result.by_category()
    assert by_cat[PATH][0] >= 1
    assert by_cat[NUMBER][0] < by_cat[NUMBER][1]
    assert 0.0 < result.rate < 1.0
