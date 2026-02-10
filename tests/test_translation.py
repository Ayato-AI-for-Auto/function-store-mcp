import unittest
from unittest.mock import patch
from solo_mcp.translation import TranslationService

class TestTranslationService(unittest.TestCase):
    def setUp(self):
        # Reset singleton for testing
        TranslationService._instance = None
        self.service = TranslationService()

    def test_detect_language_jp(self):
        self.assertEqual(self.service.detect_language("こんにちは"), "jp")
        self.assertEqual(self.service.detect_language("これはテストです。"), "jp")
        self.assertEqual(self.service.detect_language("Pythonのコード"), "jp")

    def test_detect_language_en(self):
        self.assertEqual(self.service.detect_language("Hello world"), "en")
        self.assertEqual(self.service.detect_language("This is a test."), "en")
        self.assertEqual(self.service.detect_language("12345"), "en")

    @patch("solo_mcp.translation.TranslationService.load_model")
    def test_translate_no_model(self, mock_load):
        mock_load.return_value = False
        self.assertIsNone(self.service.translate("Hello", "ja"))

    def test_ensure_bilingual_both_exist(self):
        en, jp = self.service.ensure_bilingual("desc", "English", "Japanese")
        self.assertEqual(en, "English")
        self.assertEqual(jp, "Japanese")

    @patch("solo_mcp.translation.TranslationService.translate")
    def test_ensure_bilingual_missing_en(self, mock_translate):
        mock_translate.return_value = "Translated English"
        en, jp = self.service.ensure_bilingual("source", None, "日本語の説明")
        self.assertEqual(jp, "日本語の説明")
        self.assertEqual(en, "Translated English")
        mock_translate.assert_called_with("日本語の説明", target_lang="en")

    @patch("solo_mcp.translation.TranslationService.translate")
    def test_ensure_bilingual_missing_jp(self, mock_translate):
        mock_translate.return_value = "翻訳された日本語"
        en, jp = self.service.ensure_bilingual("source", "English description", None)
        self.assertEqual(en, "English description")
        self.assertEqual(jp, "翻訳された日本語")
        mock_translate.assert_called_with("English description", target_lang="ja")

    @patch("solo_mcp.translation.TranslationService.translate")
    def test_ensure_bilingual_both_missing_jp_source(self, mock_translate):
        mock_translate.return_value = "Translated English"
        # Japanese source detected
        en, jp = self.service.ensure_bilingual("日本語のメイン説明", None, None)
        self.assertEqual(jp, "日本語のメイン説明")
        self.assertEqual(en, "Translated English")

    @patch("solo_mcp.translation.TranslationService.translate")
    def test_ensure_bilingual_failed_translation(self, mock_translate):
        mock_translate.return_value = None
        en, jp = self.service.ensure_bilingual("English Source", None, None)
        self.assertEqual(en, "English Source")
        self.assertIsNone(jp) # Should NOT copy English to Japanese on failure

if __name__ == "__main__":
    unittest.main()
