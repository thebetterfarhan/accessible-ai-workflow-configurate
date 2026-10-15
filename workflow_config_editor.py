"""Small accessible wxPython editor for user workflow configuration files.

The backend is deliberately injected (or imported from ``config_backend``)
so this module never discovers or writes configuration by itself.
"""

from __future__ import annotations

import hashlib
import importlib
import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

try:
    import wx
except ImportError:  # Keep importable for CI/static checks without wx installed.
    wx = None  # type: ignore[assignment]


@dataclass(frozen=True)
class _FallbackConfigFile:
    display_name: str
    path: str
    kind: str
    sync_kind: str


class ConfigEditorFrame(wx.Frame if wx else object):
    """One-setting-at-a-time editor using only standard wx controls."""

    def __init__(self, backend: Any = None, parent: Any = None) -> None:
        if wx is None:
            raise RuntimeError("wxPython is required to run the configuration editor")
        super().__init__(parent, title="Workflow configuration", size=(980, 700))
        self.backend = backend or importlib.import_module("config_backend")
        self.files: list[Any] = []
        self.settings: list[Any] = []
        self.file: Any = None
        self.setting: Any = None
        self.file_hash: Optional[str] = None
        self._last_backup: Any = None
        self.dirty = False
        self.category = "All categories"
        self._controls: list[Any] = []
        self._category_order = [
            "All categories", "Model", "Reasoning", "Sandbox", "Approval", "Permissions",
            "Hooks", "Agents", "Instructions", "Tools", "MCP", "Plugins", "Providers",
            "Routing", "Performance", "Output", "Accessibility", "Updates", "Workspace", "Other",
        ]
        self._category_descriptions = {
            "Model": "choose the AI model",
            "Reasoning": "choose how much thinking to use",
            "Sandbox": "choose computer access",
            "Approval": "choose when to ask permission",
            "Permissions": "choose which actions are allowed",
            "Hooks": "choose automation triggers",
            "Agents": "choose agent instructions",
            "Instructions": "choose shared workflow instructions",
            "Tools": "choose available tools",
            "MCP": "choose connected services",
            "Plugins": "choose installed extensions",
            "Providers": "choose service providers",
            "Routing": "choose how requests are routed",
            "Performance": "choose speed and resource use",
            "Output": "choose response formatting",
            "Accessibility": "choose accessibility behavior",
            "Updates": "choose update behavior",
            "Workspace": "choose workspace behavior",
            "Other": "choose other workflow settings",
        }
        self.categories = list(self._category_order)
        self.category_labels = list(self.categories)
        self._build_ui()
        self._bind_keys()
        self._discover()

    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        outer = wx.BoxSizer(wx.VERTICAL)
        instructions = wx.StaticText(panel, label="New here? Activate Start guided change for a category-by-category guide. Use Back and Next to answer each question. You can also edit directly. F6 moves between panes.")
        instructions.SetName("Keyboard instructions")
        instructions.Wrap(940)
        outer.Add(instructions, 0, wx.ALL | wx.EXPAND, 8)
        self.help_button = wx.Button(panel, label="Help (F1)")
        self.help_button.SetName("Help")
        self.help_button.SetToolTip("Read keyboard and editor instructions")
        outer.Add(self.help_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.guided_button = wx.Button(panel, label="Start guided change")
        self.guided_button.SetName("Start guided change")
        self.guided_button.SetToolTip("Guide you through each category with Back and Next")
        outer.Add(self.guided_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.progress = wx.StaticText(panel, label="Ready")
        self.progress.SetName("Guided progress")
        self.progress.Hide()
        outer.Add(self.progress, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        panes = wx.BoxSizer(wx.HORIZONTAL)
        left = wx.Panel(panel)
        left.SetName("Configuration and categories")
        left.SetMinSize((220, -1))
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        config_label = wx.StaticText(left, label="Configuration")
        self.config_choice = wx.ComboBox(left, style=wx.CB_READONLY)
        self.config_choice.SetName("Configuration")
        self.config_choice.Bind(wx.EVT_COMBOBOX, self._on_config_choice)
        category_label = wx.StaticText(left, label="Categories")
        self.category_list = wx.ListBox(left, style=wx.LB_SINGLE)
        self.category_list.SetName("Categories")
        self.category_list.Bind(wx.EVT_LISTBOX, self._on_category_choice)
        left_sizer.Add(config_label, 0, wx.BOTTOM, 3)
        left_sizer.Add(self.config_choice, 0, wx.EXPAND | wx.BOTTOM, 10)
        left_sizer.Add(category_label, 0, wx.BOTTOM, 3)
        left_sizer.Add(self.category_list, 1, wx.EXPAND)
        left.SetSizer(left_sizer)
        middle = wx.Panel(panel)
        middle.SetName("Settings list")
        middle.SetMinSize((300, -1))
        middle_sizer = wx.BoxSizer(wx.VERTICAL)
        middle_sizer.Add(wx.StaticText(middle, label="Settings"), 0, wx.BOTTOM, 3)
        self._setting_search = wx.TextCtrl(middle)
        self._setting_search.SetName("Search settings")
        self._setting_search.SetHint("Type part of a setting name")
        self._setting_search.Bind(wx.EVT_TEXT, self._on_setting_search)
        middle_sizer.Add(self._setting_search, 0, wx.EXPAND | wx.BOTTOM, 6)
        self._setting_list = wx.ListBox(middle, style=wx.LB_SINGLE)
        self._setting_list.SetName("Settings")
        self._setting_list.Bind(wx.EVT_LISTBOX, lambda e: self._choose_setting(e.GetSelection()) or self._refresh_detail())
        middle_sizer.Add(self._setting_list, 1, wx.EXPAND)
        self._setting_empty_message = wx.StaticText(middle, label="")
        self._setting_empty_message.SetName("Setting search result")
        self._setting_empty_message.Wrap(360)
        middle_sizer.Add(self._setting_empty_message, 0, wx.EXPAND | wx.TOP, 8)
        middle.SetSizer(middle_sizer)
        right = wx.Panel(panel)
        right.SetName("Setting editor")
        right.SetMinSize((320, -1))
        self.editor_panel = right
        editor = wx.BoxSizer(wx.VERTICAL)
        self.question = wx.StaticText(right, label="Select a setting")
        self.question.SetName("Setting question")
        self.question.Wrap(420)
        editor.Add(self.question, 0, wx.BOTTOM, 8)
        self.setting_label = wx.StaticText(right, label="")
        self.setting_label.SetName("Setting name")
        editor.Add(self.setting_label, 0, wx.BOTTOM, 4)
        self.type_cue = wx.StaticText(right, label="")
        self.type_cue.SetName("Setting type")
        editor.Add(self.type_cue, 0, wx.BOTTOM, 4)
        self.pending_label = wx.StaticText(right, label="")
        self.pending_label.SetName("Pending value")
        editor.Add(self.pending_label, 0, wx.BOTTOM, 8)
        self.answer_panel = wx.Panel(right)
        self.answer_panel.SetName("Value editor")
        self.answer_sizer = wx.BoxSizer(wx.VERTICAL)
        self.answer_panel.SetSizer(self.answer_sizer)
        editor.Add(self.answer_panel, 1, wx.EXPAND)
        right.SetSizer(editor)
        panes.Add(left, 1, wx.EXPAND | wx.RIGHT, 8)
        panes.Add(middle, 1, wx.EXPAND | wx.RIGHT, 8)
        panes.Add(right, 2, wx.EXPAND)
        outer.Add(panes, 1, wx.ALL | wx.EXPAND, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.review_button = wx.Button(panel, label="Review change")
        self.review_button.Enable(False)
        self.save_button = wx.Button(panel, label="Save change (Ctrl+S)")
        self.another_button = wx.Button(panel, label="Make another change")
        self.another_button.Enable(False)
        self.undo_button = wx.Button(panel, label="Undo last change")
        self.undo_button.Enable(False)
        self.backups_button = wx.Button(panel, label="Backups")
        self.backups_button.Enable(False)
        self.reload_button = wx.Button(panel, label="Reload (F5)")
        buttons.Add(self.review_button, 0, wx.RIGHT, 6)
        buttons.Add(self.save_button, 0, wx.RIGHT, 6)
        buttons.Add(self.another_button, 0, wx.RIGHT, 6)
        buttons.Add(self.undo_button, 0, wx.RIGHT, 6)
        buttons.Add(self.backups_button, 0, wx.RIGHT, 6)
        buttons.Add(self.reload_button, 0)
        outer.Add(buttons, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        guided_buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.guided_back_button = wx.Button(panel, label="Back")
        self.guided_next_button = wx.Button(panel, label="Next")
        self.guided_skip_button = wx.Button(panel, label="Skip category")
        for button in (self.guided_back_button, self.guided_next_button, self.guided_skip_button):
            button.Hide()
            guided_buttons.Add(button, 0, wx.RIGHT, 6)
        outer.Add(guided_buttons, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.status = wx.StaticText(panel, label="Ready")
        self.status.SetName("Status")
        self.status.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))
        outer.Add(self.status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        panel.SetSizer(outer)

        self.review_button.Bind(wx.EVT_BUTTON, self._on_review)
        self.save_button.Bind(wx.EVT_BUTTON, self._on_save)
        self.another_button.Bind(wx.EVT_BUTTON, self._on_another_change)
        self.undo_button.Bind(wx.EVT_BUTTON, self._on_undo)
        self.backups_button.Bind(wx.EVT_BUTTON, self._on_backups)
        self.reload_button.Bind(wx.EVT_BUTTON, self._on_reload)
        self.help_button.Bind(wx.EVT_BUTTON, self._on_help)
        self.guided_button.Bind(wx.EVT_BUTTON, self._start_guided)
        self.guided_back_button.Bind(wx.EVT_BUTTON, self._on_guided_back)
        self.guided_next_button.Bind(wx.EVT_BUTTON, self._on_guided_next)
        self.guided_skip_button.Bind(wx.EVT_BUTTON, self._on_guided_skip)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.step = 3
        self._answer_control = None
        self._radio_values: list[str] = []
        self._draft_value: Optional[str] = None
        self._guided = False
        self._guided_phase: Optional[str] = None
        self._guided_categories: list[str] = []
        self._guided_category_pos = 0

    def _bind_keys(self) -> None:
        self.Bind(wx.EVT_CHAR_HOOK, self._on_key)

    def _start_guided(self, _event: Any) -> None:
        if not self.files:
            self._set_status("No configurations are available. Choose Reload (F5) first.")
            return
        self._guided = True
        self._guided_phase = "category"
        self._guided_categories = [category for category in self.categories[1:] if self._category_has_settings(category)]
        self._guided_category_pos = 0
        if not self._guided_categories:
            self._guided = False
            self._guided_phase = None
            self._set_status("No editable categories are available in this configuration.")
            return
        self.progress.Show()
        for button in (self.guided_back_button, self.guided_next_button, self.guided_skip_button):
            button.Show()
        self.guided_back_button.Enable(False)
        self.Layout()
        self._show_guided_category()

    def _show_guided_category(self) -> None:
        category = self._guided_categories[self._guided_category_pos]
        index = self.categories.index(category)
        self.category_list.SetSelection(index)
        self.category = category
        self.setting = None
        self._draft_value = None
        self._populate_setting_choices()
        self._refresh_detail()
        self._set_guided_step(f"Category {self._guided_category_pos + 1} of {len(self._guided_categories)}. Question 1 of 4: Choose a category.")
        self.category_list.SetFocus()

    def _on_guided_next(self, _event: Any) -> None:
        if not self._guided:
            return
        if self._guided_phase == "category":
            self._guided_phase = "setting"
            self._set_guided_step(f"Category {self._guided_category_pos + 1} of {len(self._guided_categories)}. Question 2 of 4: Choose a setting.")
            self._setting_list.SetFocus()
        elif self._guided_phase == "setting":
            if self.setting is None:
                self._set_status("Choose a setting before continuing.")
                self._setting_list.SetFocus()
                return
            self._guided_phase = "value"
            self._set_guided_step(f"Category {self._guided_category_pos + 1} of {len(self._guided_categories)}. Question 3 of 4: Choose or enter the value.")
            if self._answer_control is not None:
                self._answer_control.SetFocus()
        elif self._guided_phase == "value":
            self._guided_phase = "review"
            self._set_guided_step(f"Category {self._guided_category_pos + 1} of {len(self._guided_categories)}. Question 4 of 4: Check this change.")
            self.review_button.SetFocus()
        elif self._guided_phase == "review":
            self._on_review(None)

    def _on_guided_back(self, _event: Any) -> None:
        if not self._guided:
            return
        if self._guided_phase == "setting":
            self._guided_phase = "category"
            self._show_guided_category()
        elif self._guided_phase == "value":
            self._guided_phase = "setting"
            self._set_guided_step(f"Category {self._guided_category_pos + 1} of {len(self._guided_categories)}. Question 2 of 4: Choose a setting.")
            self._setting_list.SetFocus()
        elif self._guided_phase == "review":
            self._guided_phase = "value"
            self._set_guided_step(f"Category {self._guided_category_pos + 1} of {len(self._guided_categories)}. Question 3 of 4: Choose or enter the value.")
            if self._answer_control is not None:
                self._answer_control.SetFocus()

    def _on_guided_skip(self, _event: Any) -> None:
        if self._guided:
            self._finish_guided_category()

    def _finish_guided_category(self) -> None:
        if self._guided_category_pos + 1 < len(self._guided_categories):
            self._guided_category_pos += 1
            self._guided_phase = "category"
            self._show_guided_category()
            return
        self._guided = False
        self._guided_phase = None
        self.progress.SetLabel("Guided setup complete. Review or save your change.")
        self._set_status("Guided setup complete. Review or save your change.")
        for button in (self.guided_back_button, self.guided_next_button, self.guided_skip_button):
            button.Hide()
        self.Layout()

    def _category_has_settings(self, category: str) -> bool:
        return any(self._setting_category(setting) == category for setting in self.settings)

    def _set_guided_step(self, text: str) -> None:
        self.progress.SetLabel(text)
        self.question.SetLabel(text)
        self.guided_back_button.Enable(self._guided_category_pos > 0 or self._guided_phase not in (None, "category"))
        self.guided_next_button.SetLabel("Next category" if self._guided_phase == "review" else "Next")
        self.guided_skip_button.Enable(self._guided_phase in ("category", "setting", "value", "review"))
        self._set_status(text)

    def _on_config_choice(self, event: Any) -> None:
        if self._confirm_discard():
            self._load_file(event.GetSelection())
            self._refresh_lists()
            if self._guided:
                self._guided_categories = [category for category in self.categories[1:] if self._category_has_settings(category)]
                self._guided_category_pos = 0
                self._guided_phase = "category"
                self._show_guided_category()
        elif self.file in self.files:
            self.config_choice.SetSelection(self.files.index(self.file))

    def _on_category_choice(self, event: Any) -> None:
        index = event.GetSelection()
        if self.dirty and not self._confirm_discard():
            if self.category in self.categories:
                self.category_list.SetSelection(self.categories.index(self.category))
            self._set_status("Change cancelled. The pending value is still active.")
            return
        self.category = self.categories[index]
        self._draft_value = None
        self.setting = None
        self._populate_setting_choices()
        self._refresh_detail()
        self._set_status(f"{self.category_labels[event.GetSelection()]}. Choose a setting.")
        if self._guided:
            self._set_guided_step(
                f"Category {self._guided_category_pos + 1} of {len(self._guided_categories)}. "
                f"Question {'1' if self._guided_phase == 'category' else '2'} of 4: "
                f"{'Choose a category.' if self._guided_phase == 'category' else 'Choose a setting.'}"
            )

    def _refresh_lists(self) -> None:
        self.config_choice.Set([self._file_name(item) for item in self.files])
        if self.file in self.files:
            self.config_choice.SetSelection(self.files.index(self.file))
        self.category_list.Set(self.category_labels)
        if self.category in self.categories:
            self.category_list.SetSelection(self.categories.index(self.category))
        self._populate_setting_choices()
        self._refresh_detail()

    def _refresh_detail(self) -> None:
        if self.setting is None:
            self.review_button.Enable(False)
            self.save_button.Enable(False)
            self.question.SetLabel("Select a setting")
            self.setting_label.SetLabel("")
            self.type_cue.SetLabel("")
            self.pending_label.SetLabel("")
            self._replace_answer(wx.StaticText(self.answer_panel, label="Choose a setting from the list."))
            self._answer_control = None
            return
        self.review_button.Enable(True)
        self.save_button.Enable(True)
        name = self._setting_name(self.setting)
        self.question.SetLabel(f"Edit {name}")
        self.setting_label.SetLabel(f"Current value: {getattr(self.setting, 'value', '')}")
        value_type = str(getattr(self.setting, "value_type", "text"))
        self.type_cue.SetLabel("Type: markdown section body" if value_type == "markdown" else f"Type: {value_type}")
        self._make_value_control(self.setting)
        self._replace_answer(self._controls[0])
        self._update_pending_label()

    def _on_key(self, event: Any) -> None:
        key = event.GetKeyCode()
        source = event.GetEventObject()
        if event.ControlDown() and key in (ord("F"), ord("f")):
            self._setting_search.SetFocus()
            self._setting_search.SelectAll()
        elif event.ControlDown() and key in (ord("G"), ord("g")):
            self._start_guided(event)
        elif event.ControlDown() and key in (ord("R"), ord("r")):
            self._on_review(event)
        elif event.ControlDown() and key in (ord("B"), ord("b")):
            self._on_backups(event)
        elif event.ControlDown() and key in (ord("S"), ord("s")):
            self._on_save(event)
        elif key == wx.WXK_F1:
            self._on_help(event)
        elif key == wx.WXK_ESCAPE and source is getattr(self, "_setting_search", None):
            if self._setting_search.GetValue():
                self._setting_search.ChangeValue("")
                self._on_setting_search(None)
                self._set_status("Search cleared. Choose a setting, then press Enter.")
            else:
                event.Skip()
        elif key == wx.WXK_F6:
            self._focus_pane(event.ShiftDown())
        elif key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            if source is self.config_choice and self._guided:
                self._guided_phase = "category"
                self._set_guided_step(f"Category {self._guided_category_pos + 1} of {len(self._guided_categories)}. Question 1 of 4: Choose a category.")
                self.category_list.SetFocus()
            elif source is self.category_list and self._guided:
                self._guided_phase = "setting"
                self._set_guided_step(f"Category {self._guided_category_pos + 1} of {len(self._guided_categories)}. Question 2 of 4: Choose a setting.")
                self._setting_list.SetFocus()
            elif source is self._setting_list and self._guided and self.setting is not None:
                self._guided_phase = "value"
                self._set_guided_step(f"Category {self._guided_category_pos + 1} of {len(self._guided_categories)}. Question 3 of 4: Choose or enter the value.")
                self._answer_control.SetFocus()
            elif source is self._setting_search and self._visible_settings:
                self._setting_list.SetFocus()
            elif source is self._setting_list and self.setting is not None:
                self._refresh_detail()
                if self._answer_control is not None:
                    self._answer_control.SetFocus()
            else:
                event.Skip()
        elif key == wx.WXK_F5:
            self._on_reload(event)
        else:
            event.Skip()

    def _focus_pane(self, reverse: bool = False) -> None:
        """Move focus among the persistent editor panes with F6."""
        pane_groups = [
            (self.config_choice,),
            (self.category_list,),
            (self._setting_search, self._setting_list),
            (self._answer_control,),
        ]
        pane_groups = [
            tuple(control for control in group if control is not None and control.IsShown() and control.IsEnabled())
            for group in pane_groups
        ]
        pane_groups = [group for group in pane_groups if group]
        if not pane_groups:
            return
        focused = wx.Window.FindFocus()
        try:
            index = next(
                index for index, group in enumerate(pane_groups)
                if any(focused is control or control.IsDescendant(focused) for control in group)
            )
        except StopIteration:
            index = 0 if reverse else -1
        target = pane_groups[(index - 1 if reverse else index + 1) % len(pane_groups)][0]
        target.SetFocus()

    def _discover(self) -> None:
        try:
            self.files = list(self.backend.discover_files())
            if self.files:
                self.save_button.Enable(True)
                self.guided_button.Enable(True)
                self._load_file(0)
                self._refresh_lists()
                self.guided_button.SetFocus()
                self._set_status("New here? Activate Start guided change, or choose a configuration directly.")
            else:
                self._show_unavailable("No configuration files found")
        except Exception as exc:
            self._show_unavailable(f"Could not discover files: {exc}")

    def _show_unavailable(self, message: str) -> None:
        """Keep an empty discovery state actionable through Reload only."""
        self.question.SetLabel(message)
        self.save_button.Enable(False)
        self.review_button.Enable(False)
        self.guided_button.Enable(False)
        self.progress.Hide()
        for button in (self.guided_back_button, self.guided_next_button, self.guided_skip_button):
            button.Hide()
        self.another_button.Enable(False)
        self.undo_button.Enable(False)
        self.backups_button.Enable(False)
        self.reload_button.Enable(True)
        self._set_status(f"{message}. Choose Reload (F5) to try again.")
        self.reload_button.SetFocus()

    def _load_file(self, index: int) -> None:
        item = self.files[index]
        file_changed = item != self.file
        try:
            self.settings, self.file_hash = self.backend.load_settings(item)
            self.file, self.setting, self.dirty = item, None, False
            self._draft_value = None
            if file_changed:
                self._last_backup = None
                self.undo_button.Enable(False)
            self.backups_button.Enable(callable(getattr(self.backend, "list_backups", None)))
            self._derive_categories()
            self._set_status(f"Loaded {self._file_name(item)}")
        except Exception as exc:
            self._set_status(f"Could not load file: {exc}")

    def _replace_answer(self, control: Any) -> None:
        keep_controls = control in self._controls
        for child in self.answer_panel.GetChildren():
            if child is not control:
                child.Destroy()
        if not keep_controls:
            self._controls = []
        self.answer_sizer.Clear(delete_windows=False)
        self._answer_control = control
        self.answer_sizer.Add(control, 0, wx.EXPAND | wx.ALL, 4)
        self.answer_panel.Layout()
        self.editor_panel.Layout()

    def _set_category(self, index: int) -> None:
        self.category = self.categories[index]
        self._draft_value = None
    def _derive_categories(self) -> None:
        """Keep only categories represented by this file and show their counts."""
        counts = {category: 0 for category in self._category_order[1:]}
        for setting in self.settings:
            category = self._setting_category(setting)
            counts.setdefault(category, 0)
            counts[category] += 1
        available = list(self._category_order[1:])
        available.extend(category for category in counts if category not in available)
        self.categories = ["All categories", *available]
        self.category_labels = [f"All settings ({len(self.settings)})"] + [
            f"{category}: {self._category_descriptions.get(category, 'choose settings')} ({counts[category]} settings)"
            for category in available
        ]
        if self.category not in self.categories:
            self.category = "All categories"

    def _choose_setting(self, index: int) -> None:
        if self._visible_settings:
            selected = self._visible_settings[index]
            if selected is not self.setting:
                self._draft_value = None
            self.setting = selected
            self._set_status(f"{self._setting_name(selected)} selected. Press Enter to edit.")
            if self._guided and self._guided_phase in ("setting", "value"):
                self._set_guided_step(f"Category {self._guided_category_pos + 1} of {len(self._guided_categories)}. Question 2 of 4: Choose a setting.")

    def _populate_setting_choices(self) -> None:
        """Apply the question-3 search without losing the selected setting."""
        query = str(getattr(self, "_setting_search", None).GetValue() if getattr(self, "_setting_search", None) else "").strip().lower()
        candidates = [s for s in self._filtered() if not query or query in self._setting_name(s).lower()]
        self._visible_settings = candidates
        self._setting_list.Set([self._setting_name(s) for s in candidates])
        if self.setting in candidates:
            self._setting_list.SetSelection(candidates.index(self.setting))
        elif candidates:
            self._draft_value = None
            self.setting = candidates[0]
            self._setting_list.SetSelection(0)
        else:
            self._draft_value = None
            self.setting = None
        self._update_setting_step_state()

    def _update_setting_step_state(self) -> None:
        """Keep progression and the spoken empty state aligned with search results."""
        if not hasattr(self, "_setting_list"):
            return
        count = len(self._visible_settings)
        has_results = count > 0
        self._setting_list.Enable(has_results)
        empty_message = getattr(self, "_setting_empty_message", None)
        if empty_message is not None:
            if has_results:
                empty_message.SetLabel("")
                empty_message.Hide()
            else:
                query = self._setting_search.GetValue().strip()
                if query:
                    message = f"No settings match {query}. Clear the search or choose another category."
                else:
                    message = "This category has no settings. Choose another category."
                empty_message.SetLabel(message)
                empty_message.Show()
            self.answer_panel.Layout()

    def _on_setting_search(self, _event: Any) -> None:
        self._populate_setting_choices()
        self._refresh_detail()
        count = len(self._visible_settings)
        if count:
            self._set_status(f"{count} setting{'s' if count != 1 else ''} found. Tab to choose a setting.")
        else:
            self._set_status("No matching settings. Clear the search or go back to choose another category.")

    def _value_error(self) -> Optional[str]:
        """Return a spoken correction, or None when the answer is usable."""
        if self.setting is None or not self._controls:
            return "Choose a setting and enter a value first."
        value_type = str(getattr(self.setting, "value_type", "text")).lower().strip()
        value = self._typed_value().strip()
        if value_type in ("bool", "boolean"):
            return None
        if value_type in ("number", "numeric", "float", "double"):
            try:
                number = float(value)
                if not number == number or number in (float("inf"), float("-inf")):
                    raise ValueError
            except (TypeError, ValueError):
                return "That answer must be a number. Enter a number, then press Review change."
        elif value_type in ("integer", "int"):
            try:
                int(value)
            except (TypeError, ValueError):
                return "That answer must be a whole number. Enter digits, then press Review change."
        elif value_type in ("array", "list", "object", "map", "json"):
            try:
                parsed = json.loads(value)
            except (TypeError, ValueError, json.JSONDecodeError):
                return f"That answer must be valid JSON for a {value_type}. Enter it again, then press Review change."
            if value_type in ("array", "list") and not isinstance(parsed, list):
                return "That answer must be a JSON list in square brackets. Enter it again, then press Review change."
            if value_type in ("object", "map") and not isinstance(parsed, dict):
                return "That answer must be a JSON object in curly brackets. Enter it again, then press Review change."
        return None

    def _confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        dialog = wx.MessageDialog(self, "Discard unsaved changes?", "Unsaved changes", wx.YES_NO | wx.ICON_WARNING)
        try:
            return dialog.ShowModal() == wx.ID_YES
        finally:
            dialog.Destroy()

    def _filtered(self) -> list[Any]:
        return [s for s in self.settings if self.category == "All categories" or self._setting_category(s) == self.category]

    def _setting_category(self, setting: Any) -> str:
        declared = str(getattr(setting, "category", "")).strip()
        if declared:
            return declared
        text = " ".join(map(str, [getattr(setting, "label", ""), getattr(setting, "path", "")])).lower()
        aliases = {
            "model": "Model", "reason": "Reasoning", "sandbox": "Sandbox", "approval": "Approval",
            "permission": "Permissions", "hook": "Hooks", "agent": "Agents", "instruction": "Instructions",
            "tool": "Tools", "mcp": "MCP", "plugin": "Plugins", "provider": "Providers", "route": "Routing",
            "performance": "Performance", "output": "Output", "access": "Accessibility", "update": "Updates",
            "workspace": "Workspace",
        }
        for key, category in aliases.items():
            if key in text:
                return category
        return "Other"

    def _setting_name(self, setting: Any) -> str:
        raw = str(getattr(setting, "label", getattr(setting, "path", "Unnamed setting")))
        key = raw.lower().replace("_", " ").replace("-", " ")
        friendly = {
            "model": "Which AI model should I use?",
            "model reasoning effort": "How much reasoning should I use?",
            "reasoning effort": "How much reasoning should I use?",
            "sandbox": "How much computer access should I allow?",
            "approval": "When should I ask before taking action?",
            "service tier": "Which service speed should I use?",
            "hooks": "Should workflow hooks run?",
            "hook": "Should workflow hooks run?",
            "plugins": "Which plugins should be enabled?",
            "plugin": "Which plugins should be enabled?",
        }
        for name, text in friendly.items():
            if key == name:
                return text
        if key.startswith("reasoning effort.") or key.startswith("reasoning effort "):
            return f"Reasoning preference: {raw.split('.', 1)[-1]}"
        if key.startswith("reasoningeffort."):
            return f"Reasoning preference: {raw.split('.', 1)[-1]}"
        return raw.replace(".", " ").replace("_", " ").strip().capitalize()

    def _file_name(self, item: Any) -> str:
        raw = str(getattr(item, "display_name", getattr(item, "path", item)))
        location = str(getattr(item, "path", ""))
        key = f"{raw} {location}".lower()
        filename = Path(location or raw).name.lower()
        if filename == "hooks.json" or "codex\\hooks.json" in key or "/codex/hooks.json" in key:
            return "Codex hooks"
        if filename.endswith(".config.toml"):
            profile = filename.removesuffix(".config.toml")
            return f"Codex {profile} profile"
        if filename == "config.toml" or "codex\\config.toml" in key or "/codex/config.toml" in key:
            return "Main Codex settings"
        if "opencode" in key:
            return "OpenCode settings"
        if filename == "settings.json" and ("commandcode" in key or "command code" in key):
            return "CommandCode settings"
        if filename == "config.json" and ("commandcode" in key or "command code" in key):
            return "CommandCode config"
        if "commandcode" in key or "command code" in key:
            return "CommandCode settings"
        if "agent" in key:
            return "Shared workflow instructions"
        if "taste" in key:
            return "Workflow preferences"
        return raw

    def _make_value_control(self, setting: Any) -> None:
        for control in self._controls:
            control.Destroy()
        self._controls = []
        raw = self._draft_value if self._draft_value is not None else str(getattr(setting, "value", ""))
        value_type = str(getattr(setting, "value_type", "text")).lower()
        label = self._setting_name(setting)
        if value_type in ("bool", "boolean") or raw.lower() in ("true", "false"):
            control = wx.CheckBox(self.answer_panel, label=label)
            control.SetName(label)
            control.SetValue(raw.lower() == "true")
            control.Bind(wx.EVT_CHECKBOX, self._on_typed_value)
            self._controls = [control]
        else:
            options = self._enum_options(setting, raw)
            if options:
                self._radio_values = options
                control = wx.RadioBox(self.answer_panel, label=label, choices=[self._radio_label(v) for v in options], majorDimension=1,
                                      style=wx.RA_SPECIFY_ROWS)
                control.SetName(label)
                control.SetSelection(options.index(raw) if raw in options else 0)
                control.Bind(wx.EVT_RADIOBOX, self._on_typed_value)
                self._controls = [control]
            else:
                control = wx.TextCtrl(self.answer_panel, value=raw, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER,
                                      size=(-1, 130))
                control.SetName(f"{label} value")
                control.Bind(wx.EVT_TEXT, self._on_value)
                self._controls = [control]
        # Keep focus where the user made the selection. NVDA otherwise jumps from
        # the list into a recreated control after every arrow key.

    def _enum_options(self, setting: Any, raw: str) -> list[str]:
        declared = getattr(setting, "options", None)
        if declared:
            return [str(item) for item in declared]
        text = str(getattr(setting, "label", getattr(setting, "path", ""))).lower()
        known = {
            "sandbox": ["read-only", "workspace-write", "danger-full-access"],
            "approval": ["untrusted", "on-failure", "on-request", "never"],
            "service tier": ["default", "priority"],
            "reasoning": ["low", "medium", "high"],
            "effort": ["low", "medium", "high"],
        }
        for key, options in known.items():
            if key in text:
                return options if raw in options else [raw, *options]
        return []

    def _radio_label(self, value: str) -> str:
        labels = {
            "read-only": "Read only: can look, cannot change files",
            "workspace-write": "Workspace files: can change project files",
            "danger-full-access": "Full access: can change anything",
            "untrusted": "Always ask me first",
            "on-failure": "Ask only after something fails",
            "on-request": "Ask when the tool requests it",
            "never": "Never ask me",
            "default": "Standard speed",
            "priority": "Priority speed",
            "low": "Low",
            "medium": "Medium",
            "high": "High",
        }
        return labels.get(value, value.replace("_", " ").capitalize())

    def _typed_value(self) -> str:
        control = self._controls[0]
        if isinstance(control, wx.CheckBox):
            return "true" if control.GetValue() else "false"
        if isinstance(control, wx.RadioBox):
            index = control.GetSelection()
            return self._radio_values[index] if 0 <= index < len(self._radio_values) else control.GetStringSelection()
        return control.GetValue()

    def _on_typed_value(self, _event: Any) -> None:
        if self.setting is not None:
            self.dirty = self._typed_value() != str(getattr(self.setting, "value", ""))
            self._update_pending_label()

    def _on_value(self, _event: Any) -> None:
        if self.setting is not None:
            self.dirty = self._typed_value() != str(getattr(self.setting, "value", ""))
            self._update_pending_label()

    def _update_pending_label(self) -> None:
        if self.setting is None or not self._controls:
            self.pending_label.SetLabel("")
            return
        pending = self._typed_value()
        self.pending_label.SetLabel(f"Pending value: {pending}")
        self._answer_control.SetName(
            f"{self._setting_name(self.setting)}. "
            f"Current value: {getattr(self.setting, 'value', '')}. "
            f"Type: {getattr(self.setting, 'value_type', 'text')}. "
            f"Pending value: {pending}."
        )

    def _review_text(self) -> str:
        if self.file is None or self.setting is None or not self._controls:
            return "Select a setting and enter a value before reviewing."
        return (
            f"Configuration: {self._file_name(self.file)}\n"
            f"Setting: {self._setting_name(self.setting)}\n"
            f"Current value: {getattr(self.setting, 'value', '')}\n"
            f"Pending value: {self._typed_value()}\n\n"
            "Choose Yes to save this change, or No to keep editing."
        )

    def _on_review(self, _event: Any) -> None:
        if self.file is None or self.setting is None:
            self._set_status("Select a setting first")
            return
        error = self._value_error()
        if error:
            self._set_status(error)
            if self._controls:
                self._controls[0].SetFocus()
            return
        dialog = wx.MessageDialog(self, self._review_text(), "Review change", wx.YES_NO | wx.ICON_QUESTION)
        try:
            confirmed = dialog.ShowModal() == wx.ID_YES
        finally:
            dialog.Destroy()
        if confirmed:
            self._on_save(None)
        else:
            self._set_status("Review cancelled. The pending value is still active.")
            if self._controls:
                self._controls[0].SetFocus()

    def _on_save(self, _event: Any) -> None:
        if self.file is None or self.setting is None:
            self._set_status("Select a setting first")
            return
        try:
            error = self._value_error()
            if error:
                self._set_status(error)
                if self._controls:
                    self._controls[0].SetFocus()
                return
            proposed = self._draft_value if self._draft_value is not None else self._typed_value()
            result = self.backend.save_setting(self.file, self.setting, proposed, self.file_hash)
            self.file_hash = getattr(result, "sha256", None) or self._hash_after_save(result)
            continue_guided = self._guided and self._guided_phase == "review" and self._guided_category_pos + 1 < len(self._guided_categories)
            self.dirty = False
            self._draft_value = None
            if continue_guided:
                self._guided_category_pos += 1
                self._guided_phase = "category"
            else:
                self._guided = False
                self._guided_phase = None
                self.progress.Hide()
                for button in (self.guided_back_button, self.guided_next_button, self.guided_skip_button):
                    button.Hide()
            self.Layout()
            backup = getattr(result, "backup_path", None)
            self._last_backup = backup
            self._load_file(self.files.index(self.file))
            self._refresh_lists()
            if continue_guided:
                self._show_guided_category()
            backup_text = f" Backup: {backup}." if backup else ""
            sync_text = str(getattr(result, "sync_message", "")).strip()
            self._set_status(f"Saved.{backup_text} {sync_text}".strip())
            self.another_button.Enable(True)
            self.undo_button.Enable(backup is not None and callable(getattr(self.backend, "restore_backup", None)))
            self.another_button.SetFocus()
        except Exception as exc:
            self._set_status(f"Could not save setting: {exc}")

    def _on_another_change(self, _event: Any) -> None:
        """Start a fresh guided change after a completed save."""
        self.another_button.Enable(False)
        self.setting = None
        self._draft_value = None
        self._refresh_lists()
        self.category_list.SetFocus()
        self._set_status("Choose a category for your next change.")

    def _on_undo(self, _event: Any) -> None:
        """Restore the backup from the most recent successful save."""
        if not self._last_backup or self.file is None:
            self._set_status("There is no saved change to undo.")
            return
        if not callable(getattr(self.backend, "restore_backup", None)):
            self._set_status("Undo is unavailable for this configuration.")
            return
        dialog = wx.MessageDialog(
            self,
            "Undo the last saved change? This will restore the previous value.",
            "Undo last change",
            wx.YES_NO | wx.ICON_WARNING,
        )
        try:
            confirmed = dialog.ShowModal() == wx.ID_YES
        finally:
            dialog.Destroy()
        if not confirmed:
            self._set_status("Undo cancelled. The saved change is still active.")
            self.undo_button.SetFocus()
            return
        try:
            result = self.backend.restore_backup(self.file, self._last_backup, self.file_hash)
            self._last_backup = None
            self.undo_button.Enable(False)
            self._load_file(self.files.index(self.file))
            self._refresh_lists()
            sync_text = str(getattr(result, "sync_message", "")).strip()
            self._set_status(f"Last change undone. {sync_text}".strip())
            self.another_button.SetFocus()
        except Exception as exc:
            self._set_status(f"Could not undo last change: {exc}")
            self.undo_button.SetFocus()

    def _on_backups(self, _event: Any) -> None:
        if self.file is None:
            self._set_status("Load a configuration first")
            return
        list_backups = getattr(self.backend, "list_backups", None)
        if not callable(list_backups):
            self._set_status("Backup history is unavailable for this configuration")
            return
        backups = list_backups(self.file)
        if not backups:
            self._set_status("No backups are available for this configuration")
            return
        choices = [path.name for path in backups]
        dialog = wx.SingleChoiceDialog(self, "Choose a backup to restore.", "Backup history", choices)
        try:
            if dialog.ShowModal() != wx.ID_OK:
                self._set_status("Backup restore cancelled.")
                return
            backup = backups[dialog.GetSelection()]
        finally:
            dialog.Destroy()
        confirm = wx.MessageDialog(
            self,
            f"Restore {backup.name}? The current file will be backed up first.",
            "Restore backup",
            wx.YES_NO | wx.ICON_WARNING,
        )
        try:
            confirmed = confirm.ShowModal() == wx.ID_YES
        finally:
            confirm.Destroy()
        if not confirmed:
            self._set_status("Backup restore cancelled.")
            self.backups_button.SetFocus()
            return
        try:
            result = self.backend.restore_backup(self.file, backup, self.file_hash)
            self._last_backup = getattr(result, "backup_path", None)
            self._load_file(self.files.index(self.file))
            self._refresh_lists()
            self.undo_button.Enable(self._last_backup is not None)
            self._set_status(f"Restored backup {backup.name}.")
            self.another_button.SetFocus()
        except Exception as exc:
            self._set_status(f"Could not restore backup: {exc}")
            self.backups_button.SetFocus()

    def _hash_after_save(self, result: Any) -> Optional[str]:
        # Backend may omit a post-save hash; reload supplies the authoritative one.
        return None

    def _on_reload(self, _event: Any) -> None:
        if self.file is None:
            self._discover()
            return
        if not self._confirm_discard():
            return
        self._load_file(self.files.index(self.file))
        self._refresh_lists()
        self._set_status("Reloaded. Choose a setting.")

    def _on_help(self, _event: Any) -> None:
        """Show short, screen-reader-friendly instructions for the persistent editor."""
        self._help_return_focus = wx.Window.FindFocus()
        message = (
            "Workflow configuration help\n\n"
            "Choose a configuration, category, and setting. The editor stays visible while "
            "you change the value. Guided change walks through populated categories with Back, Next, "
            "and Skip category. Choose Save change when ready.\n\n"
            "Keyboard: Tab moves through controls. F6 moves between configuration, category, "
            "settings, and editor panes. Arrow keys choose list items. Enter selects a setting. "
            "Escape clears the setting search. Ctrl+F focuses and selects the search. "
            "F1 opens this help. F5 reloads. Ctrl+G starts guided mode. Ctrl+R reviews. Ctrl+B opens backups. Ctrl+S saves.\n\n"
            "Saving creates a backup. After saving, choose Make another change to continue, "
            "or Undo last change to restore the previous value.\n\n"
            "For shared workflow instructions, choose an AGENTS.md or taste file, choose a section, "
            "then replace the section body in the multiline editor. Generated TASTE sections are protected."
        )
        dialog = wx.MessageDialog(self, message, "Workflow configuration help", wx.OK | wx.ICON_INFORMATION)
        try:
            dialog.ShowModal()
        finally:
            dialog.Destroy()
        self._restore_help_focus()

    def _restore_help_focus(self) -> None:
        target = getattr(self, "_help_return_focus", None)
        if target is not None and target.IsShown() and target.IsEnabled():
            target.SetFocus()
        elif self.help_button and self.help_button.IsEnabled():
            self.help_button.SetFocus()

    def _on_close(self, event: Any) -> None:
        if self._confirm_discard():
            self.Destroy()
        else:
            event.Veto()

    def _set_status(self, text: str) -> None:
        self.status.SetLabel(text)


def main(backend: Any = None) -> int:
    if wx is None:
        raise RuntimeError("Install wxPython to run workflow_config_editor")
    app = wx.App(False)
    frame = ConfigEditorFrame(backend)
    frame.Show()
    app.MainLoop()
    return 0


class _SmokeBackend:
    """In-memory backend used only by ``--smoke``; it touches no user files."""

    def discover_files(self) -> list[Any]:
        return [_FallbackConfigFile("Smoke configuration", "<memory>", "smoke", "none")]

    def load_settings(self, _file: Any) -> tuple[list[Any], str]:
        return [type("SmokeSetting", (), {"label": "Example setting", "path": "example", "value": "false", "value_type": "boolean"})()], "smoke"

    def save_setting(self, _file: Any, _setting: Any, _value: str, _expected: str) -> Any:
        raise AssertionError("smoke mode must not save")


class _EmptySmokeBackend(_SmokeBackend):
    def __init__(self) -> None:
        self.available = False

    def discover_files(self) -> list[Any]:
        if self.available:
            return super().discover_files()
        return []


class _SaveSmokeBackend(_SmokeBackend):
    def __init__(self) -> None:
        self.saved_value = None

    def save_setting(self, _file: Any, _setting: Any, value: str, _expected: str) -> Any:
        self.saved_value = value
        return type("SaveResult", (), {"sha256": "after-save", "backup_path": None, "sync_message": ""})()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Edit workflow configuration")
    parser.add_argument("--smoke", action="store_true", help="construct controls and exit without touching files")
    args = parser.parse_args()
    if args.smoke:
        if wx is None:
            raise SystemExit("wxPython is required for --smoke")
        app = wx.App(False)
        empty_backend = _EmptySmokeBackend()
        empty_frame = ConfigEditorFrame(empty_backend)
        assert not empty_frame.save_button.IsEnabled()
        assert not empty_frame.guided_button.IsEnabled()
        assert empty_frame.reload_button.IsEnabled()
        empty_backend.available = True
        empty_frame._on_reload(None)
        assert empty_frame.save_button.IsEnabled()
        assert empty_frame.guided_button.IsEnabled()
        empty_frame.Destroy()
        frame = ConfigEditorFrame(_SmokeBackend())
        frame.Show()
        wx.Yield()
        assert frame.step == 3
        assert not frame.progress.IsShown()
        assert frame.guided_button.GetLabel() == "Start guided change"
        assert frame.status.GetLabel().startswith("New here")
        assert wx.Window.FindFocus() is frame.guided_button
        assert frame.config_choice.GetSelection() == 0
        frame._load_file(0)
        assert frame.status.GetLabel().startswith("Loaded Smoke configuration")
        frame._refresh_lists()
        assert frame.category_list.GetCount() == 20
        assert any("Sandbox" in frame.category_list.GetString(i) and "(0 settings)" in frame.category_list.GetString(i) for i in range(frame.category_list.GetCount()))
        declared_category = type("DeclaredCategorySetting", (), {"label": "custom", "path": "custom", "category": "Security"})()
        assert frame._setting_category(declared_category) == "Security"
        assert frame._setting_list.GetCount() == 1
        assert frame.answer_panel.GetName() == "Value editor"
        original_setting = frame.setting
        frame.setting = type("MarkdownSetting", (), {"label": "Shared instructions", "path": "instructions", "value": "body", "value_type": "markdown"})()
        frame._refresh_detail()
        assert frame.type_cue.GetLabel() == "Type: markdown section body"
        frame.setting = original_setting
        frame._refresh_detail()
        assert frame.guided_next_button.GetLabel() == "Next"
        assert frame.guided_back_button.GetLabel() == "Back"
        assert frame.guided_skip_button.GetLabel() == "Skip category"
        frame._start_guided(None)
        assert frame._guided_phase == "category"
        assert frame.progress.GetLabel().startswith("Category 1 of")
        assert frame.progress.IsShown()
        frame._on_guided_next(None)
        assert frame._guided_phase == "setting"
        frame._on_guided_next(None)
        assert frame._guided_phase == "value"
        frame._on_guided_back(None)
        assert frame._guided_phase == "setting"
        guided_called = []
        original_guided = frame._start_guided
        frame._start_guided = lambda _event: guided_called.append(True)
        guided_key = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        guided_key.SetKeyCode(ord("G"))
        guided_key.SetEventObject(frame.config_choice)
        guided_key.SetControlDown(True)
        frame._on_key(guided_key)
        assert guided_called
        frame._start_guided = original_guided
        review_called = []
        original_review = frame._on_review
        frame._on_review = lambda _event: review_called.append(True)
        review_key = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        review_key.SetKeyCode(ord("R"))
        review_key.SetEventObject(frame.config_choice)
        review_key.SetControlDown(True)
        frame._on_key(review_key)
        assert review_called
        frame._on_review = original_review
        backups_called = []
        original_backups = frame._on_backups
        frame._on_backups = lambda _event: backups_called.append(True)
        backups_key = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        backups_key.SetKeyCode(ord("B"))
        backups_key.SetEventObject(frame.config_choice)
        backups_key.SetControlDown(True)
        frame._on_key(backups_key)
        assert backups_called
        frame._on_backups = original_backups
        config_enter = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        config_enter.SetKeyCode(wx.WXK_RETURN)
        config_enter.SetEventObject(frame.config_choice)
        frame._on_key(config_enter)
        assert frame.progress.GetLabel().startswith("Category 1 of")
        assert "Question 1 of 4" in frame.question.GetLabel()
        assert wx.Window.FindFocus() is frame.category_list
        category_enter = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        category_enter.SetKeyCode(wx.WXK_RETURN)
        category_enter.SetEventObject(frame.category_list)
        frame._on_key(category_enter)
        assert "Question 2 of 4" in frame.progress.GetLabel()
        assert wx.Window.FindFocus() is frame._setting_list
        search_enter = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        search_enter.SetKeyCode(wx.WXK_RETURN)
        search_enter.SetEventObject(frame._setting_search)
        frame._on_key(search_enter)
        assert wx.Window.FindFocus() is frame._setting_list
        assert frame.backups_button.GetLabel() == "Backups"
        assert "Current value: false" in frame._answer_control.GetName()
        assert "Type: boolean" in frame._answer_control.GetName()
        assert "Pending value: false" in frame._answer_control.GetName()
        frame._setting_search.SetFocus()
        frame._help_return_focus = frame._setting_search
        frame._restore_help_focus()
        assert wx.Window.FindFocus() is frame._setting_search
        frame._choose_setting(0)
        frame._on_guided_next(None)
        assert "Question 3 of 4" in frame.progress.GetLabel()
        frame._on_guided_next(None)
        assert "Question 4 of 4" in frame.progress.GetLabel()
        review = frame._review_text()
        assert "Current value: false" in review
        assert "Pending value: false" in review
        original_category = frame.category
        frame.dirty = True
        frame._confirm_discard = lambda: False
        frame.category_list.SetSelection(1)
        frame._on_category_choice(type("Event", (), {"GetSelection": lambda self: 1})())
        assert frame.category == original_category
        frame.dirty = False
        frame.category_list.SetFocus()
        frame._focus_pane()
        assert wx.Window.FindFocus() is frame._setting_search
        frame._setting_list.SetFocus()
        enter = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        enter.SetKeyCode(wx.WXK_RETURN)
        enter.SetEventObject(frame._setting_list)
        frame._on_key(enter)
        assert wx.Window.FindFocus() is frame._answer_control
        assert frame.save_button.GetLabel().startswith("Save change")
        assert frame.reload_button.GetLabel().startswith("Reload")
        assert frame.undo_button.GetLabel() == "Undo last change"
        assert not frame.undo_button.IsEnabled()
        frame._setting_search.ChangeValue("no matching setting")
        frame._on_setting_search(None)
        assert not frame._setting_list.IsEnabled()
        assert not frame.review_button.IsEnabled()
        assert not frame.save_button.IsEnabled()
        assert frame.question.GetLabel() == "Select a setting"
        escape = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        escape.SetKeyCode(wx.WXK_ESCAPE)
        escape.SetEventObject(frame._setting_search)
        frame._on_key(escape)
        assert frame._setting_search.GetValue() == ""
        assert frame._setting_list.IsEnabled()
        assert frame.review_button.IsEnabled()
        assert frame.save_button.IsEnabled()
        assert isinstance(frame._answer_control, wx.CheckBox)
        assert frame.pending_label.GetLabel() == "Pending value: false"
        frame._answer_control.SetValue(True)
        frame._on_value(None)
        assert frame.pending_label.GetLabel() == "Pending value: true"
        assert "Pending value: true" in frame._answer_control.GetName()
        frame.dirty = False
        frame._on_reload(None)
        assert frame.step == 3
        assert frame.config_choice.GetSelection() == 0
        frame.files.append(_FallbackConfigFile("Second configuration", "<memory-2>", "smoke", "none"))
        frame._last_backup = "previous-file-backup"
        frame.undo_button.Enable(True)
        frame._load_file(1)
        assert frame._last_backup is None
        assert not frame.undo_button.IsEnabled()
        frame.Destroy()
        save_backend = _SaveSmokeBackend()
        save_frame = ConfigEditorFrame(save_backend)
        save_frame._answer_control.SetValue(True)
        save_frame._on_value(None)
        save_frame._on_save(None)
        assert save_backend.saved_value == "true"
        assert save_frame.status.GetLabel().startswith("Saved.")
        assert save_frame.another_button.IsEnabled()
        save_frame.Destroy()
        app.Destroy()
        raise SystemExit(0)
    raise SystemExit(main())
