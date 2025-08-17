import unittest
import os
import bpy

class ImporterTest(unittest.TestCase):
    def test_addon_enabled(self):
        self.assertIsNotNone(bpy.ops.import_scene.x)

    def test_import(self):
        filepath = os.path.dirname(__file__) + '\\models\\test.x'
        result = bpy.ops.import_scene.x(filepath=filepath)
        self.assertSetEqual(result, {'FINISHED'})

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ImporterTest)
    runner = unittest.TextTestRunner()
    runner.run(suite)
