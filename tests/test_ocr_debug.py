import sys, tkinter as tk, unittest
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from ocr_debug import OCRReaderView, preview_image, label_montage


class DebugReaderTests(unittest.TestCase):
    def test_images_are_bounded_without_modifying_reader_input(self):
        source=Image.new('RGB',(3840,2160),'white')
        self.assertEqual(source.size,(3840,2160))
        self.assertLessEqual(preview_image(source).height,290)
        self.assertEqual(label_montage([source]*20).size,(880,290))

    def test_close_releases_preview_and_reopened_view_ignores_old_worker(self):
        root=tk.Tk();root.withdraw()
        c={key:'#15111e' for key in ('bg','text','secondary','panel','muted')}
        app=SimpleNamespace(root=root,colors=c,action=lambda parent,text,command,primary:tk.Button(parent,text=text,command=command))
        viewer=OCRReaderView(app,'Test OCR',lambda:None)
        try:
            self.assertIsNone(viewer.token())
            viewer.open();old=viewer.token();image=Image.new('RGB',(50,30))
            viewer.show(old,image,'184 / 600',1)
            self.assertIsNotNone(viewer.photo)
            self.assertIsNotNone(viewer.raw_image)
            viewer.hold.set(True);viewer.show(old,Image.new('RGB',(60,40)),'should be held')
            self.assertEqual(viewer.raw_image.size,(50,30))
            viewer.open_full_image();root.update_idletasks();self.assertTrue(viewer.full_window.winfo_exists())
            for _ in range(100):viewer.paused('BDO covered')
            self.assertLess(len(viewer.text.get('1.0','end')),16001)
            viewer.close();self.assertIsNone(viewer.photo);self.assertIsNone(viewer.token())
            self.assertIsNone(viewer.raw_image)
            viewer.open();viewer.show(old,image,'stale result')
            self.assertIsNone(viewer.photo)
            viewer.paused('BDO covered');self.assertIn('previous capture',viewer.status.get())
        finally:
            viewer.close();root.destroy()


if __name__=='__main__':unittest.main()
