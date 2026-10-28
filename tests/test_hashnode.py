import os
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock

from hashnode_engine import (
    clean_text,
    html_to_markdown,
    format_hashnode_tags,
    build_hashnode_input,
    load_state,
    save_state
)

class TestHashnodeSyndicator(unittest.TestCase):

    def test_clean_text(self):
        raw = "<h2>AI Governance &amp; Digital Rights</h2>"
        self.assertEqual(clean_text(raw), "AI Governance & Digital Rights")

    def test_html_to_markdown(self):
        html_input = (
            "<h2>Heading Title</h2>"
            "<p>This is a paragraph with <a href=\"https://aviperera.com\">link</a> and <strong>bold</strong> text.</p>"
            "<blockquote>Important quote</blockquote>"
        )
        md = html_to_markdown(html_input)
        self.assertIn("## Heading Title", md)
        self.assertIn("[link](https://aviperera.com)", md)
        self.assertIn("**bold**", md)
        self.assertIn("> Important quote", md)

    def test_format_hashnode_tags(self):
        categories = ["AI Ethics", "Autonomous Systems", "Policy"]
        tags = format_hashnode_tags(categories)
        self.assertLessEqual(len(tags), 4)
        for t in tags:
            self.assertIn("slug", t)
            self.assertIn("name", t)
            self.assertTrue(t["slug"].replace("-", "").isalnum())

    def test_build_hashnode_input(self):
        post = {
            "title": "Corporate Liability for Autonomous AI",
            "link": "https://aviperera.com/corporate-liability-autonomous-ai/",
            "content_html": "<p>A detailed examination of legal frameworks.</p>",
            "description": "Short summary",
            "categories": ["AI Ethics", "Governance"],
            "image_url": "https://aviperera.com/sample.jpg"
        }
        pub_id = "test_pub_123"
        input_data = build_hashnode_input(post, publication_id=pub_id)

        self.assertEqual(input_data["title"], "Corporate Liability for Autonomous AI")
        self.assertEqual(input_data["publicationId"], "test_pub_123")
        self.assertEqual(input_data["originalArticleURL"], "https://aviperera.com/corporate-liability-autonomous-ai/")
        self.assertIn("aviperera.com", input_data["contentMarkdown"])
        self.assertEqual(input_data["coverImageOptions"]["coverImageURL"], "https://aviperera.com/sample.jpg")

    def test_load_and_save_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_state_file = os.path.join(tmpdir, "state", "hashnode_history.json")
            with patch("hashnode_engine.STATE_FILE", test_state_file):
                state = load_state()
                self.assertEqual(state["syndicated"], {})

                state["syndicated"]["post-101"] = {
                    "title": "Sample Article",
                    "canonical_url": "https://aviperera.com/sample-article",
                    "hashnode_id": "hash999"
                }
                save_state(state)

                reloaded = load_state()
                self.assertIn("post-101", reloaded["syndicated"])
                self.assertEqual(reloaded["syndicated"]["post-101"]["hashnode_id"], "hash999")

if __name__ == "__main__":
    unittest.main()
