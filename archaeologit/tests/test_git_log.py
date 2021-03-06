from collections import namedtuple
import itertools
import os

from impermagit import fleeting_repo
from nose.tools import ok_, eq_

from archaeologit import git_log
from archaeologit.tutil import read_test_fname
from archaeologit import util


TEST_PARSE_NAME_AND_EMAIL_DATA = [
    ("Bob Jones <bob@example.com>",
     ("Bob Jones", "bob@example.com")),
    ("Bob Middle Name Jones <bob weird@example.com>",
     ("Bob Middle Name Jones", "bob weird@example.com")),
    ("Bob <bob@example.com>",
     ("Bob", "bob@example.com")),
    ("Bob > Greater Than <bob<>@example.com>",
     ("Bob > Greater Than", "bob<>@example.com")),
    # just to note how we would handle this insane case...
    ("Bob < Less Than <bob<>@example.com>",
     ("Bob", " Less Than <bob<>@example.com")),
    ("", None),
    ("Bob", None),
    ("bob@example.com", None)]


def test_parse_name_and_email():
    for (author, expected) in TEST_PARSE_NAME_AND_EMAIL_DATA:
        yield _check_parse_name_and_email, author, expected


def _check_parse_name_and_email(author, expected):
    eq_(expected, git_log.parse_name_and_email(author))


# named tuple containing information to commit to a test repo for
# purposes of testing log retrieval / parsing
TestCommitInfo = namedtuple('TestCommitInfo',
                            'file_body commit_msg author_name author_email')


TEST_COMMIT_ONE = TestCommitInfo(file_body="test file body\n",
                                 commit_msg="test commit msg",
                                 author_name="Testy McTesterson",
                                 author_email="testy@example.com")


TEST_COMMIT_TWO = TestCommitInfo(file_body="test second file body\n",
                                 commit_msg="test second commit msg",
                                 author_name="Testy Second McTesterson",
                                 author_email="testysecond@example.com")


TEST_COMMIT_UNICODE_BODY = TestCommitInfo(
    file_body=util.utf8(u"frosty the \u2603 was a kind soul\n"),
    commit_msg="test commit msg",
    author_name="Testy McTesterson",
    author_email="testy@example.com")


TEST_COMMIT_UNICODE_MSG = TestCommitInfo(
    file_body="hi unicode msg\n",
    commit_msg=util.utf8(u"test commit \u2603 msg"),
    author_name="Testy McTesterson",
    author_email="testy@example.com")


TEST_COMMIT_UNICODE_AUTHOR = TestCommitInfo(
    file_body="hi unicode author\n",
    commit_msg="test commit",
    author_name=util.utf8(u"Testy \u2603 McTesterson"),
    author_email="testy2@example.com")


# sorted for use in itertools.permutations
TEST_COMMIT_INFOS = sorted([TEST_COMMIT_ONE,
                            TEST_COMMIT_TWO,
                            TEST_COMMIT_UNICODE_BODY,
                            TEST_COMMIT_UNICODE_MSG,
                            TEST_COMMIT_UNICODE_AUTHOR])


def _commit_to_test_txt(test_repo, file_body, commit_msg,
                        author_name, author_email):
    test_repo.commit([('test.txt', file_body)],
                     commit_msg=commit_msg,
                     author="%s <%s>" % (author_name,
                                         author_email))


def test_parse_log_stream():
    # do from 1 to 3 commits
    for num_commits in range(1, 3):
        for commit_infos in itertools.permutations(TEST_COMMIT_INFOS,
                                                   num_commits):
            with fleeting_repo() as test_repo:
                for commit_info in commit_infos:
                    _commit_to_test_txt(test_repo, **commit_info._asdict())
                test_txt = os.path.join(test_repo.repo_root, 'test.txt')
                yield _check_parsed_log_entries, test_txt, commit_infos


def _check_parsed_log_entries(fname, commit_infos):
    log_entries = list(git_log.parse_raw_log(fname))
    eq_(len(commit_infos), len(log_entries))

    for ci_le in zip(commit_infos, log_entries):
        commit_info, log_entry = ci_le
        _validate_parsed_entry(log_entry, commit_info)


def _validate_parsed_entry(parsed_entry, commit_info):
    ok_(parsed_entry)
    ok_(util.uc(commit_info.commit_msg) in parsed_entry.log_msg)
    ok_(commit_info.file_body in util.utf8(parsed_entry.diff))
    eq_(util.uc(commit_info.author_name), parsed_entry.author_name)
    eq_(util.uc(commit_info.author_email), parsed_entry.author_email)


TEST_UNPARSEABLE_LOG_ENTRIES_DATA = [
    'empty_log.log',
    'missing_author.log',
    'bad_author_format.log',
    'missing_commit.log',
    'no_diff.log',
]


def test_unparseable_log_entries():
    for fname in TEST_UNPARSEABLE_LOG_ENTRIES_DATA:
        yield _check_unparseable_log_entry, fname


def _check_unparseable_log_entry(fname):
    parsed_entry = git_log._parse_log_entry(read_test_fname(fname))
    ok_(parsed_entry is None,
        "Parsing %s expected None, got %s " % (fname, parsed_entry))
