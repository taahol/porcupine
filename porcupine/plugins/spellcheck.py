from __future__ import annotations

import itertools
import tkinter
from typing import List

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

    def limit_to_visible_part(self, indices: List[str]) -> tuple[str, str]:
        tw = self.tab.textwidget
        if tw.compare(indices[0], "<", tw.index("@0,0")):
            start = tw.index("@0,0")
        else:
            start = indices[0]
        if tw.compare(indices[1], ">", tw.index("@0,10000")):
            end = tw.index("@0,10000")
        else:
            end = indices[1]
        return (start, end)

    def check_spelling(self, event: utils.EventWithData) -> None:
        checker = self.checker
        if not checker:
            return
        tag = event.data_string
        if tag.startswith("tag add Token.Comment") or tag.startswith("tag add Token.Text"):
            start, end = self.limit_to_visible_part(get_main_window().tk.splitlist(tag)[3:])
            text = self.tab.textwidget.get(start, end)
            checker.set_text(text)
            self.tab.event_generate(
                "<<SetUnderlines>>",
                data=underlines.Underlines(
                    id="spelling",
                    underline_list=[
                        underlines.Underline(
                            start=f"{start}+{error.wordpos}c",
                            end=f"{start}+{error.wordpos+len(error.word)}c",
                            message=", ".join(self.dictionary.suggest(error.word)),
                            color="red",
                        )
                        for error in checker
                    ],
                ),
            )

    #                self.textwidget.master.master.event_generate(
    #                    '<<SetUnderlines>>',
    #                    data='Underlines{"id": "strr","underline_list":[{"start":"'+start+str(wordstart)+'c","end":"'+start+str(wordend)+'c","message":"jou"}]}')

    def on_config_changed(self, junk: object) -> None:
        language = self.tab.settings.get("language_iso_code", str)
        self.checker = SpellChecker(language)
        self.dictionary = enchant.Dict(language)


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
