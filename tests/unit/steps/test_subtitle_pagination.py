from types import SimpleNamespace
import unittest

from src.steps.subtitle import SubtitleFormatter


class SubtitlePaginationTest(unittest.TestCase):
    def setUp(self):
        self.formatter = object.__new__(SubtitleFormatter)
        self.formatter.max_chars_per_line = 5

    def test_sentence_endings_create_separate_pages(self):
        self.assertEqual(
            self.formatter._paginate_text("最初です。次です！最後?"),
            ["最初です。", "次です！", "最後?"],
        )

    def test_long_sentence_is_hard_split_to_two_line_capacity(self):
        self.assertEqual(
            self.formatter._paginate_text("12345678901"),
            ["1234567890", "1"],
        )

    def test_generated_cues_are_contiguous_and_end_at_audio_duration(self):
        script = SimpleNamespace(segments=[SimpleNamespace(text="最初です。次です。")])
        cues = self.formatter._calculate_timestamps(script, 10.0)

        self.assertEqual([cue["text"] for cue in cues], ["最初です。", "次です。"])
        self.assertEqual(cues[0]["start"], 0.0)
        self.assertEqual(cues[0]["end"], cues[1]["start"])
        self.assertEqual(cues[-1]["end"], 10.0)

    def test_each_page_wraps_to_at_most_two_lines(self):
        for page in self.formatter._paginate_text("12345678901。短い。"):
            self.assertLessEqual(len(self.formatter._wrap_text(page)), 2)


if __name__ == "__main__":
    unittest.main()
