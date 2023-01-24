from __future__ import annotations

import itertools
import tkinter
from typing import Any, List, Tuple

import enchant
from enchant.checker import SpellChecker

from porcupine import get_main_window, get_tab_manager, menubar, tabs, utils
from porcupine.plugins import underlines


class EnchantSpellChecker:
    def __init__(self, tab: tabs.FileTab, language: str) -> None:
        self.checker = SpellChecker(language) if language else None
        self.dictionary = enchant.Dict(language) if language else None
        self.tab = tab
        utils.bind_with_data(tab.textwidget, "<<SpellCheckHook>>", self.check_spelling)

    def limit_to_visible_part(self, start: str, end: str) -> Tuple[str, str]:
        tw = self.tab.textwidget
        if tw.compare(start, "<", tw.index("@0,0")):
            start = tw.index("@0,0")
        if tw.compare(end, ">", tw.index("@0,10000")):
            end = tw.index("@0,10000")
        return (start, end)

    def check_spelling(self, event: utils.EventWithData) -> None:
        if not self.checker:
            return

        def _check_text(start: str, end: str) -> List[Tuple[str, int, str, str]]:
            text = self.tab.textwidget.get(start, end)
            if text.strip():
                # print(text)
                self.checker.set_text(text)
                return [(error.word, error.wordpos, start, end) for error in self.checker]
            return []

        tags = event.data_string
        if tags.startswith("tag add Token.Comment") or tags.startswith("tag add Token.Text"):
            underline_list = [
                underlines.Underline(
                    f"{start}+{wordpos}c",
                    f"{start}+{wordpos+len(word)}c",
                    word,  # "Use autocompletion to see suggestions.",
                    "red",
                )
                for error in (
                    _check_text(start, end)
                    for start, end in map(
                        self.limit_to_visible_part,
                        *[iter(get_main_window().tk.splitlist(tags)[3:])] * 2,
                    )
                )
                for word, wordpos, start, end in error
            ]
            if underline_list:
                self.tab.event_generate(
                    "<<SetUnderlines>>", data=underlines.Underlines("spelling", underline_list)
                )

    #                self.textwidget.master.master.event_generate(
    #                    '<<SetUnderlines>>',
    #                    data='Underlines{"id": "strr","underline_list":[{"start":"'+start+str(wordstart)+'c","end":"'+start+str(wordend)+'c","message":"jou"}]}')

    def on_config_changed(self, junk: object) -> None:
        language = self.tab.settings.get("language_iso_code", str)
        self.checker = SpellChecker(language)
        self.dictionary = enchant.Dict(language)

    def get_suggestions(self, junk: object) -> str | None:
        # TODO: convert to autocompletion
        ranges = self.tab.textwidget.tag_ranges("underline:spelling")
        for start, end in zip(ranges[0::2], ranges[1::2]):
            if self.tab.textwidget.compare(start, "<=", "insert") and self.tab.textwidget.compare(
                "insert", "<=", end
            ):
                print(self.dictionary.suggest(self.tab.textwidget.get(start, end)))
                return "break"
        return None


def _add_language_menuitem(lang: str, tk_var: tkinter.StringVar) -> None:
    menubar.get_menu("Languages").add_radiobutton(
        label=lang,
        command=lambda: menubar.get_filetab().settings.set("language_iso_code", lang),
        variable=tk_var,
    )


languages_var: tkinter.StringVar


def on_new_filetab(tab: tabs.FileTab) -> None:
    tab.settings.add_option("language_iso_code", default="")
    language = tab.settings.get("language_iso_code", str)
    languages_var.set(language)
    chkr = EnchantSpellChecker(tab, language)
    tab.bind("<<TabSettingChanged:language_iso_code>>", chkr.on_config_changed, add=True)
    tab.textwidget.bind("<<JumpToDefinitionRequest>>", chkr.get_suggestions, add=True)


def setup() -> None:
    langs = enchant.Broker().list_languages()
    supported_languages = [
        lang
        for lang in langs
        if "_" in lang or lang + "_" not in (l[: len(lang) + 1] for l in langs)
    ]
    if supported_languages:
        global languages_var
        languages_var = tkinter.StringVar()
        for language in supported_languages:
            _add_language_menuitem(language, languages_var)
        get_tab_manager().add_filetab_callback(on_new_filetab)
