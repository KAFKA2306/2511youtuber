import os
import unittest
from unittest.mock import patch

from src.main import (
    _EXTERNAL_APPROVAL_ENV,
    _EXTERNAL_APPROVAL_VALUE,
    _PUBLIC_APPROVAL_ENV,
    _PUBLIC_APPROVAL_VALUE,
    _configure_publication_mode,
)


class MainPublicationModeTests(unittest.TestCase):
    def test_normal_run_enables_external_publication(self):
        with patch.dict(os.environ, {}, clear=True):
            _configure_publication_mode(dry_run=False)
            self.assertEqual(
                os.environ[_EXTERNAL_APPROVAL_ENV], _EXTERNAL_APPROVAL_VALUE
            )
            self.assertEqual(
                os.environ[_PUBLIC_APPROVAL_ENV], _PUBLIC_APPROVAL_VALUE
            )
            self.assertNotIn("YOUTUBER_FORCE_DRY_RUN", os.environ)

    def test_dry_run_removes_publication_approvals(self):
        env = {
            _EXTERNAL_APPROVAL_ENV: _EXTERNAL_APPROVAL_VALUE,
            _PUBLIC_APPROVAL_ENV: _PUBLIC_APPROVAL_VALUE,
        }
        with patch.dict(os.environ, env, clear=True):
            _configure_publication_mode(dry_run=True)
            self.assertNotIn(_EXTERNAL_APPROVAL_ENV, os.environ)
            self.assertNotIn(_PUBLIC_APPROVAL_ENV, os.environ)
            self.assertEqual(os.environ["YOUTUBER_FORCE_DRY_RUN"], "1")


if __name__ == "__main__":
    unittest.main()
