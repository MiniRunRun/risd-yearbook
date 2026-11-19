import io, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import app, safe_name
from PIL import Image
import tifffile

class YearbookTest(unittest.TestCase):
    def setUp(self): self.client=app.test_client()
    def test_name(self):
        self.assertEqual(safe_name('a_GD_Nicole_Sun_1645426.RAW','1'),'1_a_GD_Nicole_Sun_1645426.tif')
        for n in ['0','-1','1.5','abc','']:
            with self.assertRaises(ValueError): safe_name('image.cr3',n)
    def test_preview_and_export(self):
        image=io.BytesIO(); Image.new('RGB',(12,8),(20,120,30)).save(image,'PNG'); data=image.getvalue()
        r=self.client.post('/api/preview-local',data={'photo':(io.BytesIO(data),'photo.png')}); self.assertEqual(r.status_code,200); self.assertEqual(Image.open(io.BytesIO(r.data)).size,(12,8))
        r=self.client.post('/api/export',data={'number':'1','name':'photo.RAW','mode':'demo','composite':(io.BytesIO(data),'composite.png')}); self.assertEqual(r.status_code,200)
        self.assertIn('1_photo.tif',r.headers['Content-Disposition'])
        with tifffile.TiffFile(io.BytesIO(r.data)) as t:
            self.assertEqual(t.pages[0].bitspersample,8); self.assertEqual(t.asarray().shape,(8,12,3)); self.assertEqual(t.asarray()[0,0].tolist(),[20,120,30])
    def test_drive_requires_authorization(self):
        r=self.client.post('/api/export',data={'number':'1','mode':'drive'}); self.assertEqual(r.status_code,403)
if __name__=='__main__': unittest.main()
