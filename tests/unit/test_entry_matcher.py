"""Unit tests for EntryMatcher helpers and matching logic."""

from __future__ import annotations

from aegis_keepass_lib import AegisEntry, EntryMatcher, KeePassEntry
from app.secure import SecureBytes
from tests.fixtures.builders import AWS_AEGIS_UUID, GITHUB_AEGIS_UUID


def _aegis(uuid: str, name: str, issuer: str, secret: str = "JBSWY3DPEHPK3PXP") -> AegisEntry:
    return AegisEntry(
        uuid=uuid,
        name=name,
        issuer=issuer,
        secret=SecureBytes(secret),
        algo="HMAC-SHA-1",
        digits=6,
        period=30,
    )


def _keepass(
    uuid: str,
    title: str,
    username: str | None = None,
    url: str | None = None,
    notes: str | None = None,
) -> KeePassEntry:
    return KeePassEntry(
        uuid=uuid,
        title=title,
        username=username,
        url=url,
        notes=notes,
    )


class TestNormalizeAndHelpers:
    def test_normalize_strips_and_lowers(self):
        assert EntryMatcher.normalize("  GitHub!  ") == "github"

    def test_normalize_empty(self):
        assert EntryMatcher.normalize("") == ""
        assert EntryMatcher.normalize(None) == ""  # type: ignore[arg-type]

    def test_extract_base_domain_from_url(self):
        assert EntryMatcher.extract_base_domain("https://www.github.com/login") == "github"

    def test_extract_base_domain_rejects_email(self):
        assert EntryMatcher.extract_base_domain("user@example.com") is None

    def test_clean_username_strips_issuer_prefix(self):
        assert EntryMatcher.clean_username("GitHub: alice", "GitHub") == "alice"

    def test_extract_numbers(self):
        assert EntryMatcher.extract_numbers("acct-12345678-x") == {"12345678"}
        assert EntryMatcher.extract_numbers("short12") == set()

    def test_share_distinct_word(self):
        matcher = EntryMatcher()
        assert matcher.share_distinct_word("GitHub Corp", "My GitHub Login") is True
        assert matcher.share_distinct_word("login app", "account portal") is False

    def test_similarity_identical(self):
        matcher = EntryMatcher()
        assert matcher.similarity("GitHub", "github") == 1.0


class TestFindMatches:
    def test_uuid_rematch(self):
        aegis = _aegis(AWS_AEGIS_UUID, "root", "Amazon Web Services")
        kp = _keepass(
            "kp-aws",
            "Something Else",
            notes=f"AegisUUID: {AWS_AEGIS_UUID}",
        )
        matcher = EntryMatcher()
        matches, unmatched = matcher.find_matches([aegis], [kp])
        assert len(matches) == 1
        assert unmatched == []
        assert matches[0].confidence == 10.0
        assert "UUID" in matches[0].match_reason

    def test_fuzzy_github_match(self):
        aegis = _aegis(GITHUB_AEGIS_UUID, "alice", "GitHub")
        kp = _keepass("kp-gh", "GitHub", username="alice", url="https://github.com")
        distractor = _keepass("kp-other", "Unrelated Bank", username="bob")
        matcher = EntryMatcher()
        matches, unmatched = matcher.find_matches([aegis], [kp, distractor])
        assert len(matches) == 1
        assert matches[0].keepass_entry.uuid == "kp-gh"
        assert unmatched == []

    def test_unmatched_orphan(self):
        aegis = _aegis("orphan-uuid", "nobody", "UnmatchedServiceXYZ")
        kp = _keepass("kp-gh", "GitHub", username="alice")
        matcher = EntryMatcher()
        matches, unmatched = matcher.find_matches([aegis], [kp])
        assert matches == []
        assert len(unmatched) == 1

    def test_conflict_prefers_username_match(self):
        a1 = _aegis("a1", "alice", "GitHub")
        a2 = _aegis("a2", "bob", "GitHub")
        kp = _keepass("kp-gh", "GitHub", username="alice", url="https://github.com")
        matcher = EntryMatcher()
        matches, unmatched = matcher.find_matches([a1, a2], [kp])
        assert len(matches) == 1
        assert matches[0].aegis_entry.uuid == "a1"
        assert len(unmatched) == 1
        assert unmatched[0].uuid == "a2"

    def test_suggest_match_ignores_uuid(self):
        aegis = _aegis(GITHUB_AEGIS_UUID, "alice", "GitHub")
        # KeePass has a different Aegis UUID marker but still fuzzy-matches
        kp = _keepass(
            "kp-gh",
            "GitHub",
            username="alice",
            url="https://github.com",
            notes="AegisUUID: 99999999-9999-4999-8999-999999999999",
        )
        matcher = EntryMatcher()
        suggestion = matcher.suggest_match(aegis, [kp])
        assert suggestion is not None
        assert suggestion.keepass_entry.uuid == "kp-gh"
        assert suggestion.confidence != 10.0
