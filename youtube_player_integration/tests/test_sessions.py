import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPONENT_DIR = ROOT / "custom_components" / "tritue_youtube_player"


def load_sessions_module():
    spec = importlib.util.spec_from_file_location(
        "tritue_youtube_player_sessions", COMPONENT_DIR / "sessions.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


NOW = datetime(2026, 9, 14, 8, 0, 0, tzinfo=timezone.utc)


class SessionHelperTests(unittest.TestCase):
    def setUp(self):
        self.sessions = load_sessions_module()

    def status(self):
        queue = {"index": 0, "items": [{"source": "youtube", "id": "a", "url": "u-a"}, {"source": "youtube", "id": "b", "url": "u-b"}]}
        return {
            "session": {"state": "playing"},
            "sessions": [
                {"session_id": "s2", "state": "playing", "output_entity_ids": ["media_player.bep"], "queue": queue,
                 "item": {"title": "A"}, "controller": "ha:abc"},
                {"session_id": "web", "state": "playing", "output_entity_ids": [], "queue": queue},
                {"session_id": "s1", "state": "playing", "output_entity_ids": ["media_player.phong_khach"], "queue": queue,
                 "item": {"title": "B"}, "controller": "c2a"},
            ],
        }

    def test_active_sessions_skip_the_web_page_and_keep_order(self):
        self.assertEqual(["s2", "s1"], [s["session_id"] for s in self.sessions.active_sessions(self.status())])
        legacy = {"session": {"state": "playing", "output_entity_ids": ["media_player.x"]}}
        self.assertEqual(1, len(self.sessions.active_sessions(legacy)))
        self.assertTrue(self.sessions.is_controlled_by(legacy["session"], "abc"))

    def test_controller_and_queue(self):
        s2, s1 = self.sessions.active_sessions(self.status())
        self.assertTrue(self.sessions.is_controlled_by(s2, "abc"))
        self.assertFalse(self.sessions.is_controlled_by(s1, "abc"))
        self.assertEqual((1, "u-b"), (self.sessions.queue_item(s2, 1)[0], self.sessions.item_target(self.sessions.queue_item(s2, 1)[1])))
        self.assertIsNone(self.sessions.queue_item(s2, -1))
        compact = self.sessions.compact_sessions(self.status())
        self.assertEqual({"session_id": "s2", "queue_index": 0, "queue_size": 2}, {k: compact[0][k] for k in ("session_id", "queue_index", "queue_size")})
        self.assertNotIn("queue", compact[0])

    def test_track_finished_only_near_the_end(self):
        tracker = {}
        observe = self.sessions.observe_track
        self.assertFalse(observe(tracker, "idle", {}, NOW))  # never played: not finished
        attributes = {"media_position": 190, "media_position_updated_at": NOW.isoformat(), "media_duration": 200}
        self.assertFalse(observe(tracker, "playing", attributes, NOW))
        self.assertFalse(observe(tracker, "paused", {}, NOW + timedelta(seconds=2)))  # pause never counts
        self.assertTrue(observe(tracker, "idle", {}, NOW + timedelta(seconds=9)))
        self.assertFalse(observe(tracker, "idle", {}, NOW + timedelta(seconds=10)))  # reported once

        stopped = {}
        observe(stopped, "playing", {"media_position": 50, "media_position_updated_at": NOW.isoformat(), "media_duration": 200}, NOW)
        self.assertFalse(observe(stopped, "idle", {}, NOW + timedelta(seconds=5)))  # stopped mid-track

        no_position = {}
        observe(no_position, "playing", {}, NOW)
        self.assertTrue(observe(no_position, "off", {}, NOW))  # speaker without position: trust the state

    def test_reports_of_the_previous_song_are_ignored(self):
        import base64
        import json

        def stream_url(video_id):
            payload = base64.urlsafe_b64encode(json.dumps({"exp": 1, "source": "youtube", "target": video_id}).encode()).decode().rstrip("=")
            return f"http://172.16.10.28:8099/api/stream/{payload}.c2lnbmF0dXJl"

        new_song = {"id": "M7lc1UVf-VE", "url": "https://www.youtube.com/watch?v=M7lc1UVf-VE"}
        self.assertEqual("dQw4w9WgXcQ", self.sessions.stream_target(stream_url("dQw4w9WgXcQ")))
        self.assertIsNone(self.sessions.stream_target("M7lc1UVf-VE"))  # a TV's own app: can't tell
        self.assertTrue(self.sessions.plays_item({"media_content_id": "M7lc1UVf-VE"}, new_song))

        observe = self.sessions.observe_track
        tracker = {}
        # "Next" pressed 5 s before the old song ended: the speaker still reports it...
        old = {"media_content_id": stream_url("dQw4w9WgXcQ"), "media_position": 195,
               "media_position_updated_at": NOW.isoformat(), "media_duration": 200}
        self.assertFalse(self.sessions.plays_item(old, new_song))
        self.assertFalse(observe(tracker, "playing", old, NOW, new_song))
        # ...then goes idle while loading the new song: not the new song's end.
        self.assertFalse(observe(tracker, "idle", {}, NOW + timedelta(seconds=6), new_song))
        new = {"media_content_id": stream_url("M7lc1UVf-VE"), "media_position": 0,
               "media_position_updated_at": (NOW + timedelta(seconds=8)).isoformat(), "media_duration": 200}
        self.assertFalse(observe(tracker, "playing", new, NOW + timedelta(seconds=8), new_song))
        self.assertTrue(observe(tracker, "idle", {}, NOW + timedelta(seconds=205), new_song))


if __name__ == "__main__":
    unittest.main()


def stream_url(video_id):
    import base64
    import json
    payload = base64.urlsafe_b64encode(json.dumps({"exp": 1, "source": "youtube", "target": video_id}).encode()).decode().rstrip("=")
    return f"http://172.16.10.28:8099/api/stream/{payload}.c2lnbmF0dXJl"


class ChenGiuaBaiTests(unittest.TestCase):
    """Chủ máy 30/09/2026: "đang phát nhạc, tts thì nhạc dừng không, đặc biệt youtube … loa gg, loa cam, loa r1"."""

    def setUp(self):
        self.s = load_sessions_module()
        self.item = {"id": "dQw4w9WgXcQ", "url": "u"}

    def feed(self, tracker, state, mcid, t, position=None, duration=None):
        attrs = {"media_content_id": mcid}
        if position is not None:
            attrs.update(media_position=position, media_position_updated_at=NOW + timedelta(seconds=t), media_duration=duration)
        now = NOW + timedelta(seconds=t)
        tiep = self.s.observe_interruption(tracker, state, attrs, now, self.item)
        if "chen_tu" not in tracker and tiep is None:
            self.s.observe_track(tracker, state, attrs, now, self.item)
        return tiep

    def test_loa_google_tts_thay_bai_thi_phat_tiep_dung_giay(self):
        tr = {}
        ours = stream_url("dQw4w9WgXcQ")
        self.assertIsNone(self.feed(tr, "playing", ours, 0, position=40, duration=240))
        self.assertIsNone(self.feed(tr, "playing", "http://ha/api/tts_proxy/abc.mp3", 10))   # TTS chen vào
        self.assertAlmostEqual(tr["chen_tu"], 50, delta=0.5)
        self.assertEqual(50, round(self.feed(tr, "idle", "http://ha/api/tts_proxy/abc.mp3", 14)))  # đọc xong
        self.assertIsNone(self.feed(tr, "idle", None, 15), "chỉ phát tiếp MỘT lần")

    def test_loa_tu_quay_ve_bai_minh_thi_khong_lam_gi(self):
        tr = {}
        ours = stream_url("dQw4w9WgXcQ")
        self.feed(tr, "playing", ours, 0, position=40, duration=240)
        self.feed(tr, "playing", "http://ha/api/tts_proxy/abc.mp3", 5)
        self.assertIsNone(self.feed(tr, "playing", ours, 9, position=45, duration=240))
        self.assertNotIn("chen_tu", tr)

    def test_gan_het_bai_hay_chua_phat_luong_minh_thi_khong_chen(self):
        tr = {}
        self.feed(tr, "playing", stream_url("dQw4w9WgXcQ"), 0, position=230, duration=240)
        self.feed(tr, "playing", "http://ha/api/tts_proxy/abc.mp3", 1)
        self.assertNotIn("chen_tu", tr, "gần hết bài: để chuyển bài như thường")
        tr2 = {}
        self.feed(tr2, "playing", "http://radio/stream.mp3", 0)
        self.assertIsNone(self.feed(tr2, "idle", "http://radio/stream.mp3", 5))
