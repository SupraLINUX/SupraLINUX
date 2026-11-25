import unittest
from fixture import boot_disk
from framebuffer import parse_ppm, check_fixture, png_bytes

class FixtureTests(unittest.TestCase):
    def test_boot_disk(self):
        data = boot_disk()
        self.assertEqual(len(data), 1474560)
        self.assertEqual(data[510:512], b"\x55\xaa")

    def test_capture(self):
        pixels = bytes([0,0,170]*4 + [170,0,0]*4)
        width, height, rgb = parse_ppm(b"P6\n2 4\n255\n" + pixels)
        self.assertEqual(check_fixture(width, height, rgb)["top_rgb"], [0,0,170])
        self.assertTrue(png_bytes(width, height, rgb).startswith(b"\x89PNG"))

    def test_rejects_wrong_capture(self):
        with self.assertRaises(ValueError):
            check_fixture(2, 4, bytes(24))
        with self.assertRaises(ValueError):
            parse_ppm(b"P6\n2 4\n255\n" + bytes(23))
        with self.assertRaises(ValueError):
            parse_ppm(b"P6\n99999 4\n255\n")

if __name__ == "__main__":
    unittest.main()
