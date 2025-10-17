from jazzer_llm import corpus_observer

import time

import pytest


@pytest.fixture
def test_corpus_dir(tmp_path):
    # Make a corpus directory
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()

    # and start it off with an empty file.
    empty_file = corpus_dir / "empty"
    empty_file.write_text("")

    return corpus_dir


def test_corpus_observer_notices_when_new_libfuzzer_file_created(test_corpus_dir):
    observer = corpus_observer.JazzerCorpusObserver(test_corpus_dir)
    with observer:
        new_file = test_corpus_dir / "0123456789abcdefABCDEF0123456789abcdefAB"
        new_file.write_text("new one")

        time.sleep(0.1)

        assert observer.is_coverage_stuck() == False
        assert observer.last_corpus_file.name == "0123456789abcdefABCDEF0123456789abcdefAB"


def test_corpus_observer_notices_when_new_libafl_file_created(test_corpus_dir):
    observer = corpus_observer.JazzerCorpusObserver(test_corpus_dir)
    with observer:
        new_file = test_corpus_dir / "26e37b1a06d1f49b"
        new_file.write_text("new one")

        time.sleep(0.1)

        assert observer.is_coverage_stuck() == False
        assert observer.last_corpus_file.name == "26e37b1a06d1f49b"


def test_corpus_observer_ignores_non_libfuzzer_file(test_corpus_dir):
    observer = corpus_observer.JazzerCorpusObserver(test_corpus_dir)
    with observer:
        new_file = test_corpus_dir / "hello world"
        new_file.write_text("new one")

        time.sleep(0.1)

        assert observer.is_coverage_stuck() == False
        assert observer.last_corpus_file is None


def test_corpus_observer_returns_true_for_coverage_is_stuck(test_corpus_dir):
    observer = corpus_observer.JazzerCorpusObserver(test_corpus_dir, time_between_entries=0.01)
    with observer:
        time.sleep(0.1)

        assert observer.is_coverage_stuck() == True


def test_observer_returns_false_for_coverage_is_stuck_initially(test_corpus_dir):
    observer = corpus_observer.JazzerCorpusObserver(test_corpus_dir)
    with observer:
        assert observer.is_coverage_stuck() == False


def test_observer_returns_false_for_coverage_is_stuck_when_manually_reset(test_corpus_dir):
    observer = corpus_observer.JazzerCorpusObserver(test_corpus_dir, time_between_entries=0.01)
    with observer:
        time.sleep(0.1)
        assert observer.is_coverage_stuck() == True
        observer.reset_stuck_coverage_time()
        assert observer.is_coverage_stuck() == False
