import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from loot_layout import find_saved_item_log, find_saved_layout, saved_item_log
from loot_ui import LootTracker
from guild_quest_ui import GuildQuestTracker


LAYOUT = '''<UIData Version="2">
<UIData Index="159" IsShow="true" PendingType="LeftTop" PosX="519" PosY="265"/>
<UIData Index="161" IsShow="true" PendingType="LeftTop" PosX="357" PosY="134"/>
<UIData Index="21" IsShow="true" PendingType="RightTop" PosX="321" PosY="450" SizeX="305" SizeY="631"/>
<UIData Index="9" IsShow="true" PendingType="RightTop" PosX="327" PosY="20" SizeX="320" SizeY="280"/>
<UIData Index="32" WindowIndex="3" IsShow="true" IsUsing="true" IsCombinedToMainPanel="false" PendingType="RightBottom" PosX="771" PosY="298" SizeX="420" SizeY="222">
<ChatType key="System" value="true"/>
<ChatSystemType key="ChatSystemType_PrivateItem" value="true"/>
</UIData>
</UIData>
<Resolution Width="1920" Height="1080"/>
<UiScale Value="1"/>'''


class LootLayoutTests(unittest.TestCase):
    def test_positions_include_game_window_origin(self):
        bounds = (1, -1920, 40, 0, 1120)
        self.assertEqual(saved_item_log(LAYOUT, bounds), (-1401, 305, 350, 300))
        self.assertEqual(saved_item_log(LAYOUT, bounds, 161), (-1563, 174, 420, 84))
        self.assertEqual(saved_item_log(LAYOUT, bounds, 21), (-321, 490, 305, 630))

    def test_hidden_or_wrong_resolution_does_not_return_a_guess(self):
        bounds = (1, 0, 0, 1920, 1080)
        with self.assertRaises(ValueError):
            saved_item_log(LAYOUT.replace('IsShow="true"', 'IsShow="false"', 1), bounds)
        with self.assertRaises(ValueError):
            saved_item_log(LAYOUT, (1, 0, 0, 1280, 720))
        with self.assertRaises(ValueError):
            saved_item_log(LAYOUT.replace('PendingType="LeftTop"', 'PendingType="Unknown"', 1), bounds)

    def test_right_and_bottom_anchors(self):
        layout = LAYOUT.replace('PendingType="LeftTop"', 'PendingType="RightBottom"', 1)
        self.assertEqual(saved_item_log(layout, (1, 0, 0, 1920, 1080)), (1401, 815, 350, 265))

    def test_layout_entry_can_contain_child_data(self):
        layout = LAYOUT.replace('PosX="519" PosY="265"/>', 'PosX="519" PosY="265"><Extra/></UIData>')
        self.assertEqual(saved_item_log(layout, (1, 0, 0, 1920, 1080)), (519, 265, 350, 300))

    def test_find_reads_saved_account_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'Black Desert' / 'UserCache' / '123'
            root.mkdir(parents=True)
            (root / 'gamevariable.xml').write_text(LAYOUT, encoding='utf-8')
            normal, rare = find_saved_item_log((1, 0, 0, 1920, 1080), [directory])
            layout = find_saved_layout((1, 0, 0, 1920, 1080), [directory])
        self.assertEqual(normal, (519, 265, 350, 300))
        self.assertEqual(rare, (357, 134, 420, 84))
        self.assertEqual(layout['quest_widget'], (1599, 450, 305, 630))
        self.assertEqual(layout['minimap'], (1593, 20, 320, 280))
        self.assertEqual(layout['text_feed'], (1149, 782, 420, 222))

    def test_multiple_personal_feeds_are_ambiguous(self):
        extra = '''<UIData Index="32" WindowIndex="4" IsShow="true" IsUsing="true" IsCombinedToMainPanel="false" PendingType="LeftTop" PosX="1" PosY="1" SizeX="420" SizeY="222">
<ChatType key="System" value="true"/><ChatSystemType key="ChatSystemType_PrivateItem" value="true"/></UIData>'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'Black Desert' / 'UserCache' / '123'
            root.mkdir(parents=True)
            (root / 'gamevariable.xml').write_text(LAYOUT + extra, encoding='utf-8')
            layout = find_saved_layout((1, 0, 0, 1920, 1080), [directory])
        self.assertIsNone(layout['text_feed'])

    def test_saved_map_refreshes_when_layout_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'Black Desert' / 'UserCache' / '123'
            root.mkdir(parents=True)
            path = root / 'gamevariable.xml'
            path.write_text(LAYOUT, encoding='utf-8')
            bounds = (1, 0, 0, 1920, 1080)
            first = find_saved_layout(bounds, [directory])
            path.write_text(LAYOUT.replace('PosX="519"', 'PosX="1059"'), encoding='utf-8')
            second = find_saved_layout(bounds, [directory])
        self.assertEqual(first['item_log'][0], 519)
        self.assertEqual(second['item_log'][0], 1059)

    def test_missing_rare_log_does_not_hide_the_normal_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'Black Desert' / 'UserCache' / '123'
            root.mkdir(parents=True)
            (root / 'gamevariable.xml').write_text(LAYOUT.replace('Index="161"', 'Index="160"'), encoding='utf-8')
            normal, rare = find_saved_item_log((1, 0, 0, 1920, 1080), [directory])
        self.assertEqual(normal, (519, 265, 350, 300))
        self.assertIsNone(rare)

    def test_finding_logs_updates_regions_and_uses_existing_toggle(self):
        tracker = MagicMock()
        tracker.app.busy = False
        tracker.busy = False
        tracker.regions = {'normal': None, 'chat': (1, 2, 3, 4)}
        with patch('windows_bdo.visible_bdo_capture_bounds', return_value=(1, 0, 0, 1920, 1080)), \
             patch('loot_layout.find_saved_layout', return_value={'item_log': (519, 265, 350, 300), 'rare_log': (357, 134, 420, 84), 'text_feed': None}):
            LootTracker.find_item_logs(tracker)
        tracker.feed.set.assert_called_once_with('Item Drop logs')
        self.assertEqual(tracker.regions['normal'], (519, 265, 350, 300))
        self.assertEqual(tracker.regions['chat'], (1, 2, 3, 4))
        self.assertEqual(tracker.rare_region, (357, 134, 420, 84))
        tracker.toggle.assert_called_once()

    def test_failed_discovery_preserves_active_selection(self):
        tracker = MagicMock()
        tracker.app.busy = False
        tracker.busy = False
        tracker.regions = {'normal': (4, 5, 6, 7)}
        with patch('windows_bdo.visible_bdo_capture_bounds', return_value=None):
            LootTracker.find_item_logs(tracker)
        self.assertEqual(tracker.regions['normal'], (4, 5, 6, 7))
        tracker.feed.set.assert_not_called()
        tracker.toggle.assert_not_called()

    def test_capture_alignment_rebaselines_after_layout_move(self):
        tracker = MagicMock()
        tracker.auto_align.get.return_value = True
        tracker.feed.get.return_value = 'Item Drop logs'
        tracker.regions = {'normal': (10, 10, 350, 300), 'chat': None}
        tracker.region = tracker.regions['normal']
        tracker.rare_region = None
        layout = {'item_log': (20, 30, 350, 300), 'rare_log': (40, 50, 420, 84), 'text_feed': None, 'quest_widget': None}
        with patch('windows_bdo.visible_bdo_capture_bounds', return_value=(1, 0, 0, 1920, 1080)), \
             patch('loot_layout.find_saved_layout', return_value=layout):
            self.assertTrue(LootTracker.align_saved_layout(tracker))
            tracker.region = tracker.regions['normal']
            self.assertTrue(LootTracker.align_saved_layout(tracker))
        self.assertEqual(tracker.regions['normal'], (20, 30, 350, 300))
        self.assertEqual(tracker.rare_region, (40, 50, 420, 84))
        tracker.toggle.assert_called_once()

    def test_capture_alignment_never_selects_hidden_log(self):
        tracker = MagicMock()
        tracker.auto_align.get.return_value = True
        tracker.feed.get.return_value = 'Item Drop logs'
        tracker.regions = {'normal': (10, 10, 350, 300), 'chat': None}
        with patch('windows_bdo.visible_bdo_capture_bounds', return_value=(1, 0, 0, 1920, 1080)), \
             patch('loot_layout.find_saved_layout', return_value={'item_log': None, 'rare_log': None, 'text_feed': None}):
            self.assertFalse(LootTracker.align_saved_layout(tracker))
        tracker.toggle.assert_not_called()

    def test_inactive_log_move_preserves_text_feed_baseline(self):
        tracker = MagicMock()
        tracker.auto_align.get.return_value = True
        tracker.feed.get.return_value = 'Text feed'
        tracker.regions = {'normal': (10, 10, 350, 300), 'chat': (100, 100, 420, 222)}
        tracker.region = tracker.regions['chat']
        tracker.rare_region = None
        layout = {'item_log': (20, 30, 350, 300), 'rare_log': None,
                  'text_feed': (100, 100, 420, 222)}
        with patch('windows_bdo.visible_bdo_capture_bounds', return_value=(1, 0, 0, 1920, 1080)), \
             patch('loot_layout.find_saved_layout', return_value=layout):
            self.assertTrue(LootTracker.align_saved_layout(tracker))
        tracker.toggle.assert_not_called()
        tracker.app.save_quietly.assert_called_once()

    def test_quest_reader_uses_saved_widget_when_alignment_is_on(self):
        quest = MagicMock()
        quest._watch_read = False
        quest.tracker.auto_align.get.return_value = True
        quest.saved_widget.side_effect = lambda bounds: GuildQuestTracker.saved_widget(quest, bounds)
        quest.region = (1, 2, 3, 4)
        layout = {'quest_widget': (1599, 450, 305, 630)}
        with patch('guild_quest_ui.visible_bdo_capture_bounds', return_value=(1, 0, 0, 1920, 1080)), \
             patch('guild_quest_ui.item_regions_visible', return_value=(True, 'visible')), \
             patch('loot_layout.find_saved_layout', return_value=layout):
            self.assertEqual(GuildQuestTracker.capture_region(quest), (1599, 450, 1904, 1080))

    def test_moving_widget_discards_cached_guild_card(self):
        quest = MagicMock()
        quest._watch_read = True
        quest.tracker.auto_align.get.return_value = True
        quest.saved_widget.side_effect = lambda bounds: GuildQuestTracker.saved_widget(quest, bounds)
        quest.watch_context = (1, 0, 0, 1920, 1080)
        quest.watch_widget = (1400, 450, 300, 600)
        quest.watch_box = (1450, 500, 1550, 550)
        with patch('guild_quest_ui.visible_bdo_capture_bounds', return_value=quest.watch_context), \
             patch('guild_quest_ui.item_regions_visible', return_value=(True, 'visible')), \
             patch('loot_layout.find_saved_layout', return_value={'quest_widget': (1599, 450, 305, 630)}):
            self.assertEqual(GuildQuestTracker.capture_region(quest), (1599, 450, 1904, 1080))
        self.assertIsNone(quest.watch_box)


if __name__ == '__main__':
    unittest.main()
