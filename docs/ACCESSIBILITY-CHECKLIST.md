# NVDA verification checklist

Use the packaged `dist\WorkflowConfigEditor.exe` with NVDA running. Do not save a value during this check.

1. Start the editor. NVDA should announce the keyboard instructions, Help, and the current editor status.
2. Press `Tab` until the configuration combo is focused. It should announce `Configuration` and the selected profile.
3. Press `Tab` to reach `Categories`. Use Up and Down. Each item should include its category name, description, and count.
4. Press `F6` to move through the configuration, category, settings, and value-editor panes. Focus must not disappear or jump to a different pane.
5. In the settings search, type a short name. The result count should update. Press `Escape` after a no-match search; the full list should return.
6. Focus a setting and press `Enter`. NVDA should announce the setting name, current value, type, pending value, and the editable control.
7. Press `F1`, close Help, and confirm focus returns to the control that opened Help.
8. Change the control, but do not save. NVDA should report the pending value. `Review change` should be reachable before `Save change (Ctrl+S)` with Tab.
9. Press `F5` and confirm the reload prompt. The original value should return. Close the editor without saving.

Record any failure with the key pressed, the last spoken label, and whether focus stayed in the expected pane. Automated smoke tests and accessibility trees do not replace this spoken-output check.
