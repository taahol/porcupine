from __future__ import annotations

import itertools
import tkinter
from typing import Any, Iterator

from enchant.checker import SpellChecker

from porcupine import textutils

from .base_highlighter import BaseHighlighter


class EnchantHighlighter(BaseHighlighter):
    def __init__(self, textwidget: tkinter.Text, language_code: str) -> None:
        super().__init__(textwidget)
        self._checker = SpellChecker(language_code)
        self._check_spelling()

    def on_scroll(self) -> None:
        self._check_spelling()

    def on_change(self, changes: textutils.Changes) -> None:
        pass

    def _check_spelling(self) -> None:
        checker = self._checker
        start, end = self.get_visible_part()
        text = self.textwidget.get(start, end)
        checker.set_text(text)
        self.delete_tags(start, end)
        for error in checker:
            wordstart = error.wordpos
            wordend = wordstart + len(error.word)
            self.textwidget.tag_add("Token.Keyword", f"{start}+{wordstart}c", f"{start}+{wordend}c")
