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
            "Routing", "Performance", "Output", "Accessibility", "Updates", "Other",
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
        instructions = wx.StaticText(panel, label="Answer one question at a time. Tab moves forward. Shift+Tab moves back. Enter chooses. Ctrl+S saves.")
        instructions.SetName("Keyboard instructions")
        instructions.Wrap(940)
        outer.Add(instructions, 0, wx.ALL | wx.EXPAND, 8)
        self.help_button = wx.Button(panel, label="Help (F1)")
        self.help_button.SetName("Help")
        self.help_button.SetToolTip("Read keyboard and wizard instructions")
        outer.Add(self.help_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.progress = wx.StaticText(panel, label="Question 1 of 5")
        self.progress.SetName("Wizard progress")
        outer.Add(self.progress, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.question = wx.StaticText(panel, label="Which configuration do you want to edit?")
        self.question.SetName("Question")
        self.question.Wrap(900)
        outer.Add(self.question, 0, wx.ALL | wx.EXPAND, 8)
        self.answer_panel = wx.Panel(panel)
        self.answer_sizer = wx.BoxSizer(wx.VERTICAL)
        self.answer_panel.SetSizer(self.answer_sizer)
        outer.Add(self.answer_panel, 1, wx.ALL | wx.EXPAND, 8)
        editor = wx.BoxSizer(wx.VERTICAL)
        self.setting_label = wx.StaticText(panel, label="")
        editor.Add(self.setting_label, 0, wx.BOTTOM, 4)
        self.type_cue = wx.StaticText(panel, label="")
        editor.Add(self.type_cue, 0, wx.BOTTOM, 4)
        self.value_panel = wx.Panel(panel)
        self.value_sizer = wx.BoxSizer(wx.VERTICAL)
        self.value_panel.SetSizer(self.value_sizer)
        self.value = wx.TextCtrl(self.value_panel, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER, size=(-1, 130))
        self.value.SetName("Current value")
        self.value_sizer.Add(self.value, 1, wx.EXPAND)
        self._controls = [self.value]
        self.value_panel.Hide()
        editor.Add(self.value_panel, 1, wx.EXPAND | wx.BOTTOM, 6)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.back_button = wx.Button(panel, label="Back")
        self.next_button = wx.Button(panel, label="Next")
        self.save_button = wx.Button(panel, label="Save (Ctrl+S)")
        self.another_button = wx.Button(panel, label="Make another change")
        self.another_button.Enable(False)
        self.undo_button = wx.Button(panel, label="Undo last change")
        self.undo_button.Enable(False)
        self.reload_button = wx.Button(panel, label="Reload (F5)")
        buttons.Add(self.back_button, 0, wx.RIGHT, 6)
        buttons.Add(self.next_button, 0, wx.RIGHT, 12)
        buttons.Add(self.save_button, 0, wx.RIGHT, 6)
        buttons.Add(self.another_button, 0, wx.RIGHT, 6)
        buttons.Add(self.undo_button, 0, wx.RIGHT, 6)
        buttons.Add(self.reload_button, 0)
        editor.Add(buttons, 0, wx.BOTTOM, 4)
        outer.Add(editor, 0, wx.ALL | wx.EXPAND, 8)
        self.status = wx.StaticText(panel, label="Ready")
        self.status.SetName("Status")
        self.status.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))
        outer.Add(self.status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        panel.SetSizer(outer)

        self.back_button.Bind(wx.EVT_BUTTON, self._on_back)
        self.next_button.Bind(wx.EVT_BUTTON, self._on_next)
        self.save_button.Bind(wx.EVT_BUTTON, self._on_save)
        self.another_button.Bind(wx.EVT_BUTTON, self._on_another_change)
        self.undo_button.Bind(wx.EVT_BUTTON, self._on_undo)
        self.reload_button.Bind(wx.EVT_BUTTON, self._on_reload)
        self.help_button.Bind(wx.EVT_BUTTON, self._on_help)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.step = 0
        self._answer_control = None
        self._radio_values: list[str] = []
        self._draft_value: Optional[str] = None

    def _bind_keys(self) -> None:
        self.Bind(wx.EVT_CHAR_HOOK, self._on_key)

    def _on_key(self, event: Any) -> None:
        key = event.GetKeyCode()
        if event.ControlDown() and key in (ord("S"), ord("s")):
            self._on_save(event)
        elif key == wx.WXK_F1:
            self._on_help(event)
        elif key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            source = event.GetEventObject()
            setting_step_control = self.step == 2 and (
                source is getattr(self, "_setting_search", None)
                or source is getattr(self, "_setting_list", None)
            )
            if source is self._answer_control or setting_step_control:
                self._on_next(event)
            else:
                event.Skip()
        elif key == wx.WXK_F5:
            self._on_reload(event)
        else:
            event.Skip()

    def _discover(self) -> None:
        try:
            self.files = list(self.backend.discover_files())
            if self.files:
                self._load_file(0)
                self._show_step(0)
            else:
                self._set_status("No configuration files found")
        except Exception as exc:
            self._set_status(f"Could not discover files: {exc}")

    def _load_file(self, index: int) -> None:
        item = self.files[index]
        try:
            self.settings, self.file_hash = self.backend.load_settings(item)
            self.file, self.setting, self.dirty = item, None, False
            self._draft_value = None
            self._derive_categories()
            self._set_status("Loaded")
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
        control.SetFocus()

    def _show_step(self, step: int) -> None:
        self.step = max(0, min(4, step))
        self.progress.SetLabel(f"Question {self.step + 1} of 5")
        self.back_button.Enable(self.step > 0)
        self.next_button.SetLabel("Save this change" if self.step == 4 else ("Review change" if self.step == 3 else "Next"))
        if self.step == 0:
            self.question.SetLabel("Which configuration do you want to edit?")
            control = wx.RadioBox(self.answer_panel, label="Choose a configuration", choices=[self._file_name(f) for f in self.files], majorDimension=1, style=wx.RA_SPECIFY_ROWS)
            control.SetName("Configuration choice")
            control.SetSelection(self.files.index(self.file) if self.file in self.files else 0)
            control.Bind(wx.EVT_RADIOBOX, lambda e: self._load_file(e.GetSelection()))
            self._replace_answer(control)
        elif self.step == 1:
            self.question.SetLabel("Which area of the workflow do you want to change?")
            control = wx.RadioBox(self.answer_panel, label="Choose a category", choices=self.category_labels, majorDimension=1, style=wx.RA_SPECIFY_ROWS)
            control.SetName("Workflow category")
            control.SetSelection(self.categories.index(self.category))
            control.Bind(wx.EVT_RADIOBOX, lambda e: self._set_category(e.GetSelection()))
            self._replace_answer(control)
        elif self.step == 2:
            self.question.SetLabel("Which setting do you want to change?")
            container = wx.Panel(self.answer_panel)
            container_sizer = wx.BoxSizer(wx.VERTICAL)
            search_label = wx.StaticText(container, label="Search settings (optional)")
            search_label.SetName("Setting search label")
            search = wx.TextCtrl(container)
            search.SetName("Search settings")
            search.SetHint("Type part of a setting name")
            control = wx.ListBox(container, style=wx.LB_SINGLE)
            control.SetName("Workflow setting")
            empty_message = wx.StaticText(container, label="")
            empty_message.SetName("Setting search result")
            empty_message.Wrap(880)
            container_sizer.Add(search_label, 0, wx.EXPAND | wx.BOTTOM, 3)
            container_sizer.Add(search, 0, wx.EXPAND | wx.BOTTOM, 6)
            container_sizer.Add(control, 1, wx.EXPAND)
            container_sizer.Add(empty_message, 0, wx.EXPAND | wx.TOP, 8)
            container.SetSizer(container_sizer)
            self._visible_settings = self._filtered()
            self._setting_search = search
            self._setting_list = control
            self._setting_empty_message = empty_message
            self._populate_setting_choices()
            search.Bind(wx.EVT_TEXT, self._on_setting_search)
            control.Bind(wx.EVT_LISTBOX, lambda e: self._choose_setting(e.GetSelection()))
            self._replace_answer(container)
            search.SetFocus()
        elif self.step == 3:
            if self.setting is None:
                self._show_step(2)
                return
            self.question.SetLabel(f"How should I set {self._setting_name(self.setting)}?")
            self.setting_label.SetLabel(self._setting_name(self.setting))
            self.type_cue.SetLabel(f"Current type: {getattr(self.setting, 'value_type', 'text')}")
            self._make_value_control(self.setting)
            self._answer_control = self._controls[0]
            self._replace_answer(self._answer_control)
        else:
            if self.setting is None:
                self._show_step(2)
                return
            name = self._setting_name(self.setting)
            current = str(getattr(self.setting, "value", ""))
            proposed = self._typed_value()
            self.question.SetLabel("Please review this change before saving.")
            review = wx.Panel(self.answer_panel)
            sizer = wx.BoxSizer(wx.VERTICAL)
            for label, value in (("Setting", name), ("Current value", current), ("New value", proposed)):
                text = wx.StaticText(review, label=f"{label}: {value}")
                text.SetName(label)
                text.Wrap(880)
                sizer.Add(text, 0, wx.EXPAND | wx.BOTTOM, 10)
            hint = wx.StaticText(review, label="Choose Save this change to write it, or Back to edit it.")
            hint.SetName("Review instructions")
            hint.Wrap(880)
            sizer.Add(hint, 0, wx.EXPAND | wx.BOTTOM, 10)
            review.SetSizer(sizer)
            self._replace_answer(review)
            self._answer_control = review
        self._set_status("Use arrow keys to choose. Press Tab for the next button.")

    def _set_category(self, index: int) -> None:
        self.category = self.categories[index]
        self._draft_value = None

    def _derive_categories(self) -> None:
        """Keep only categories represented by this file and show their counts."""
        counts = {category: 0 for category in self._category_order[1:]}
        for setting in self.settings:
            counts[self._setting_category(setting)] += 1
        available = [category for category in self._category_order[1:] if counts[category]]
        self.categories = ["All categories", *available]
        self.category_labels = [f"All settings ({len(self.settings)})"] + [
            f"{category}: {self._category_descriptions.get(category, 'choose settings')} ({counts[category]})"
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
        if self.step != 2 or not hasattr(self, "_setting_list"):
            return
        count = len(self._visible_settings)
        has_results = count > 0
        self.next_button.Enable(has_results)
        self._setting_list.Enable(has_results)
        empty_message = getattr(self, "_setting_empty_message", None)
        if empty_message is not None:
            if has_results:
                empty_message.SetLabel("")
                empty_message.Hide()
            else:
                query = self._setting_search.GetValue().strip()
                if query:
                    message = f"No settings match {query}. Clear the search or Tab to Back, then press Enter to choose another category."
                else:
                    message = "This category has no settings. Tab to Back, then press Enter to choose another category."
                empty_message.SetLabel(message)
                empty_message.Show()
            self.answer_panel.Layout()

    def _on_setting_search(self, _event: Any) -> None:
        self._populate_setting_choices()
        count = len(self._visible_settings)
        if count:
            self._set_status(f"{count} setting{'s' if count != 1 else ''} found. Tab to choose a setting.")
        else:
            self._set_status("No matching settings. Clear the search or go back to choose another category.")

    def _on_back(self, _event: Any) -> None:
        self._show_step(self.step - 1)

    def _on_next(self, _event: Any) -> None:
        if self.step == 0 and self._answer_control is not None:
            self._load_file(self._answer_control.GetSelection())
        if self.step == 2 and self.setting is None:
            self._set_status("Choose a setting first")
            return
        if self.step == 3:
            error = self._value_error()
            if error:
                self._set_status(error)
                if self._controls:
                    self._controls[0].SetFocus()
                return
            self._draft_value = self._typed_value()
        if self.step == 4:
            self._on_save(_event)
            return
        self._show_step(self.step + 1)

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

    def _on_file(self, event: Any) -> None:
        if not self._confirm_discard():
            self.file_list.SetSelection(self.files.index(self.file) if self.file in self.files else wx.NOT_FOUND)
            return
        self._load_file(event.GetSelection())

    def _filtered(self) -> list[Any]:
        return [s for s in self.settings if self.category == "All categories" or self._setting_category(s) == self.category]

    def _setting_category(self, setting: Any) -> str:
        text = " ".join(map(str, [getattr(setting, "label", ""), getattr(setting, "path", "")])).lower()
        aliases = {
            "model": "Model", "reason": "Reasoning", "sandbox": "Sandbox", "approval": "Approval",
            "permission": "Permissions", "hook": "Hooks", "agent": "Agents", "instruction": "Instructions",
            "tool": "Tools", "mcp": "MCP", "plugin": "Plugins", "provider": "Providers", "route": "Routing",
            "performance": "Performance", "output": "Output", "access": "Accessibility", "update": "Updates",
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

    def _refresh_settings(self) -> None:
        focused = wx.Window.FindFocus()
        visible = self._filtered()
        self.setting_list.Set([self._setting_name(s) for s in visible])
        self._visible_settings = visible
        if visible:
            self.setting_list.SetSelection(0)
            self._show_setting(visible[0])
        else:
            self.setting = None
            self.setting_label.SetLabel("No matching setting")
        if focused and focused.IsEnabled() and focused.GetParent() is not None:
            focused.SetFocus()

    def _on_search(self, _event: Any) -> None:
        self._refresh_settings()

    def _on_category(self, event: Any) -> None:
        self.category = self.categories[event.GetSelection()]
        self._refresh_settings()

    def _on_setting(self, event: Any) -> None:
        if not self._confirm_discard():
            return
        self._show_setting(self._visible_settings[event.GetSelection()])

    def _show_setting(self, setting: Any) -> None:
        self.setting = setting
        self.dirty = False
        self.setting_label.SetLabel(self._setting_name(setting))
        self.type_cue.SetLabel(f"Type: {getattr(setting, 'value_type', 'text')}")
        self._make_value_control(setting)
        self._set_status(f"Selected {self._setting_name(setting)}. Press Tab to edit.")

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
        self.value_sizer.Clear(delete_windows=False)
        self.value_panel.Layout()
        self.value = self._controls[0]
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

    def _on_value(self, _event: Any) -> None:
        if self.setting is not None:
            self.dirty = self._typed_value() != str(getattr(self.setting, "value", ""))

    def _on_save(self, _event: Any) -> None:
        if self.file is None or self.setting is None:
            self._set_status("Select a setting first")
            return
        if self.step != 4:
            self._show_step(4)
            self._set_status("Review the change, then choose Save this change.")
            return
        try:
            result = self.backend.save_setting(self.file, self.setting, self._typed_value(), self.file_hash)
            self.file_hash = getattr(result, "sha256", None) or self._hash_after_save(result)
            self.dirty = False
            self._draft_value = None
            backup = getattr(result, "backup_path", None)
            self._last_backup = backup
            self._load_file(self.files.index(self.file))
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
        self._show_step(1)
        self._set_status("Choose the area for your next change.")

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
            sync_text = str(getattr(result, "sync_message", "")).strip()
            self._set_status(f"Last change undone. {sync_text}".strip())
            self.undo_button.SetFocus()
        except Exception as exc:
            self._set_status(f"Could not undo last change: {exc}")
            self.undo_button.SetFocus()

    def _hash_after_save(self, result: Any) -> Optional[str]:
        # Backend may omit a post-save hash; reload supplies the authoritative one.
        return None

    def _on_reload(self, _event: Any) -> None:
        if self.file is None or not self._confirm_discard():
            return
        self._load_file(self.files.index(self.file))
        self._show_step(0)
        self._set_status("Reloaded. Choose a configuration.")

    def _on_help(self, _event: Any) -> None:
        """Show short, screen-reader-friendly instructions without changing the wizard."""
        message = (
            "Workflow configuration help\n\n"
            "This wizard asks one question at a time. Choose a configuration, "
            "an area, a setting, and its new value. Then review the change before saving.\n\n"
            "Keyboard: Tab moves forward. Shift+Tab moves back. Arrow keys choose a radio "
            "button. Enter activates the focused choice. F1 opens this help. F5 reloads. "
            "Control plus S opens the review or saves after review.\n\n"
            "Saving creates a backup. After saving, choose Make another change to continue, "
            "or Undo last change to restore the previous value."
        )
        dialog = wx.MessageDialog(self, message, "Workflow configuration help", wx.OK | wx.ICON_INFORMATION)
        try:
            dialog.ShowModal()
        finally:
            dialog.Destroy()
        if self.help_button and self.help_button.IsEnabled():
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Edit workflow configuration")
    parser.add_argument("--smoke", action="store_true", help="construct controls and exit without touching files")
    args = parser.parse_args()
    if args.smoke:
        if wx is None:
            raise SystemExit("wxPython is required for --smoke")
        app = wx.App(False)
        frame = ConfigEditorFrame(_SmokeBackend())
        assert frame.step == 0
        assert frame.progress.GetLabel() == "Question 1 of 5"
        assert frame.save_button.GetLabel().startswith("Save")
        assert frame.reload_button.GetLabel().startswith("Reload")
        assert frame.undo_button.GetLabel() == "Undo last change"
        assert not frame.undo_button.IsEnabled()
        frame._show_step(1)
        frame._show_step(2)
        frame._setting_search.ChangeValue("no matching setting")
        frame._on_setting_search(None)
        assert not frame.next_button.IsEnabled()
        assert not frame._setting_list.IsEnabled()
        frame._setting_search.ChangeValue("")
        frame._on_setting_search(None)
        event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        event.SetKeyCode(wx.WXK_RETURN)
        event.SetEventObject(frame._setting_list)
        frame._on_key(event)
        assert frame.step == 3
        assert isinstance(frame._answer_control, wx.CheckBox)
        frame._answer_control.SetValue(True)
        frame._on_typed_value(None)
        frame._on_next(None)
        assert frame.step == 4
        frame._on_back(None)
        assert frame.step == 3
        assert frame._answer_control.GetValue()
        children = frame.answer_panel.GetChildren()
        assert len(children) == 1
        assert children[0].GetName() == frame._answer_control.GetName()
        frame._show_step(4)
        assert frame.progress.GetLabel() == "Question 5 of 5"
        assert frame.next_button.GetLabel() == "Save this change"
        frame.dirty = False
        frame._on_reload(None)
        assert frame.step == 0
        frame.Destroy()
        app.Destroy()
        raise SystemExit(0)
    raise SystemExit(main())
