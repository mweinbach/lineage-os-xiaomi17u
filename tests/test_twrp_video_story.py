"""Offline checks of the animated recap's source and pure caption helpers."""

import importlib.util
import json
from pathlib import Path
import re
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'media/twrp-story'
SPEC = importlib.util.spec_from_file_location('twrp_video_audio', PROJECT / 'generate_audio.py')
AUDIO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIO)


class TwrpVideoStoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.story = json.loads((PROJECT / 'story.json').read_text())

    def test_scene_order_and_two_speaking_characters(self):
        self.assertEqual([s['id'] for s in self.story['scenes']], [
            'workshop', 'black-screen', 'working-image', 'slow-touch',
            'no-buzz', 'two-files', 'proof', 'baseline'])
        self.assertEqual(set(self.story['characters']), {'nezha', 'patch'})
        self.assertEqual({c['voice'] for c in self.story['characters'].values()},
                         {'af_heart', 'am_michael'})
        for scene in self.story['scenes']:
            self.assertEqual([line['speaker'] for line in scene['lines']], ['nezha', 'patch'])
            self.assertTrue(scene['title'] and scene['callout'])

    def test_film_is_a_bounded_landscape_recap_of_the_confirmed_milestone(self):
        self.assertEqual((self.story['width'], self.story['height'], self.story['fps']),
                         (1920, 1080, 30))
        self.assertEqual(self.story['source_commit'], 'd50eb53')
        words = sum(len(re.findall(r"\b[\w'-]+\b", line['text']))
                    for scene in self.story['scenes'] for line in scene['lines'])
        self.assertGreater(words, 240)
        self.assertLess(words, 400)

    def test_factual_limits_remain_explicit(self):
        limits = ' '.join(self.story['truth_constraints'])
        for phrase in ('not recorded device footage', 'not a timed benchmark',
                       'not a fresh source build', 'Magisk has not been installed',
                       'not a claim of a verified user-data backup',
                       'Only recovery_a was flashed', 'offline workspace tests',
                       'Data decryption', 'ROM is not completed'):
            self.assertIn(phrase, limits)

    def test_speech_overrides_do_not_change_readable_captions(self):
        first = self.story['scenes'][0]['lines'][0]
        self.assertIn('Xiaomi', first['text'])
        self.assertIn('Shao mee', first['speech'])
        display = ' '.join(line['text'] for scene in self.story['scenes'] for line in scene['lines'])
        self.assertIn('TWRP', display)
        self.assertIn('SELinux', display)
        self.assertIn('root ADB', display)

    def test_caption_chunks_preserve_every_word_and_stay_readable(self):
        for scene in self.story['scenes']:
            for line in scene['lines']:
                chunks = AUDIO.caption_chunks(line['text'])
                self.assertEqual(' '.join(chunks), line['text'])
                self.assertTrue(all(1 <= len(chunk.split()) <= 10 for chunk in chunks))
                self.assertTrue(all(AUDIO.phrase_weight(chunk) > 0 for chunk in chunks))
        self.assertEqual(AUDIO.caption_chunks(''), [])

    def test_subtitle_timestamps_and_helpers_do_not_access_audio_or_network(self):
        with mock.patch('builtins.open', side_effect=AssertionError('Unexpected IO')):
            self.assertEqual(AUDIO.subtitle_timestamp(0), '00:00:00,000')
            self.assertEqual(AUDIO.subtitle_timestamp(61.234, '.'), '00:01:01.234')
            self.assertEqual(AUDIO.subtitle_timestamp(3599.9996), '01:00:00,000')
            self.assertIn('Not forced word alignment', AUDIO.CAPTION_METHOD)


if __name__ == '__main__':
    unittest.main()
