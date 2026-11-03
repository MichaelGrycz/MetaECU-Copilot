"""Focused regressions for the trailer's encoded clock and scene boundaries."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from playwright.sync_api import sync_playwright
from tools.render_motion_graphics_video import FPS, TOTAL_DURATION, verify_streams

ROOT = Path(__file__).resolve().parents[1]


class TrailerSyncTests(unittest.TestCase):
    def test_missing_narration_fails_instead_of_silent_export(self):
        from tools.build_kokoro_master_audio import build_kokoro_master_audio
        with patch("tools.build_kokoro_master_audio.load_cue", side_effect=FileNotFoundError("missing cue")):
            with self.assertRaises(FileNotFoundError):
                build_kokoro_master_audio(Path("unused.wav"))

    def test_narration_overlap_and_truncation_are_rejected(self):
        import numpy as np
        from tools.build_kokoro_master_audio import SAMPLE_RATE, build_kokoro_master_audio
        for duration in (8, 57):
            with self.subTest(duration=duration), patch(
                "tools.build_kokoro_master_audio.load_cue",
                return_value=np.zeros(duration * SAMPLE_RATE, dtype=np.float32),
            ):
                with self.assertRaisesRegex(ValueError, "overlaps or exceeds"):
                    build_kokoro_master_audio(Path("unused.wav"))

    def test_rejects_short_video_even_if_container_audio_is_full_length(self):
        probe = {"streams": [
            {"codec_type": "video", "duration": "51.0", "nb_frames": "1275", "r_frame_rate": "25/1"},
            {"codec_type": "audio", "duration": "56.5"},
        ]}
        with patch("tools.render_motion_graphics_video.subprocess.run", return_value=SimpleNamespace(stdout=json.dumps(probe))):
            with self.assertRaisesRegex(ValueError, "Wrong video duration"):
                verify_streams(Path("old_demo.mp4"))

    def test_full_length_frames_accepted(self):
        probe = {"streams": [
            {"codec_type": "video", "duration": str(TOTAL_DURATION), "nb_frames": str(round(TOTAL_DURATION * FPS)), "r_frame_rate": "30/1"},
            {"codec_type": "audio", "duration": str(TOTAL_DURATION)},
        ]}
        with patch("tools.render_motion_graphics_video.subprocess.run", return_value=SimpleNamespace(stdout=json.dumps(probe))):
            self.assertEqual(verify_streams(Path("demo.mp4"))["frames"], 1695)

    def test_scene_boundaries_and_complete_narration(self):
        from scipy.io import wavfile
        starts = (0.15, 7.25, 17.8, 23.8, 32.8, 40.8, 45.8)
        names = ("hook", "ingest", "intent", "intercept", "pass", "map3d", "outro")
        end = 0
        for i, (start, name) in enumerate(zip(starts, names), 1):
            rate, data = wavfile.read(ROOT / "demo_assets" / "_kokoro_vo" / f"sc{i}_{name}.wav")
            self.assertGreaterEqual(start, end)
            end = start + len(data) / rate
        self.assertLess(end, TOTAL_DURATION)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.goto((ROOT / "demo_assets" / "trailer.html").as_uri())
            timeline = page.evaluate("window.trailerTimeline")
            for previous, current in zip(timeline, timeline[1:]):
                before = page.evaluate("t => window.setTime(t)", current["t"] - 0.001)
                after = page.evaluate("t => window.setTime(t)", current["t"])
                self.assertEqual(before["stage"], previous["stage"])
                self.assertEqual(after["stage"], current["stage"])
            for seconds, stage in ((31, "s5"), (38, "s6"), (44, "s7"), (50, "s8"), (55, "s9")):
                self.assertEqual(page.evaluate("t => window.setTime(t)", seconds)["stage"], stage)
            # Manual seeking must stop autoplay and make the same frame repeatable.
            page.evaluate("window.setTime(0.2)")
            first = page.screenshot()
            page.evaluate("window.setTime(0.2)")
            self.assertEqual(first, page.screenshot())
            browser.close()


if __name__ == "__main__":
    unittest.main()
