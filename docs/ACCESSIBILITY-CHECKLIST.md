# NVDA verification checklist

Use the packaged `dist\WorkflowConfigEditor.exe` with NVDA running. Do not save a value during this check.

1. Start the editor. NVDA should announce the keyboard instructions, Help, and the current editor status.
   Activate `Welcome` and confirm the orientation is spoken. Toggle `Guidance: Detailed` to `Guidance: Short`; the instructions should become shorter without removing control names.
2. Activate `Start guided change` or press `Ctrl+G`. The first populated category should announce `Category 1 of N, Question 1 of 4`.
3. Use `Back`, `Next`, and `Skip category`. Back must preserve the previous answer; Next must advance; Skip must move to the next category.
4. Press `Tab` to reach `Categories`. Use Up and Down. The known 19 categories should be present, including zero-count categories; declared extra categories should also appear with a count.
5. In guided mode, listen for the category purpose and the possible value explanations before choosing a setting value.
6. Activate `Pause guided setup`, then `Resume guided setup`. NVDA should hear the same category/question and checklist states should remain available.
7. Enter an invalid value and activate `Next`. The wizard must stay on the question, focus the answer, and speak a repair instruction; a valid example should be available.
8. Activate `Change summary` and confirm old/new values are spoken. Activate `Reset category`, cancel once, then confirm; the pending answer must return to its loaded value without a save.
9. Press `F6` to move through the configuration, category, settings, and value-editor panes. Focus must not disappear or jump to a different pane.
10. In the settings search, type a short name. The result count should update. Press `Escape` after a no-match search; the full list should return.
11. Focus a setting and press `Enter`. NVDA should announce the setting name, current value, type, pending value, and the editable control.
   For an AGENTS.md or taste section, the type cue should say `markdown section body`, and the answer should be a multiline editor.
12. Press `F1`, close Help, and confirm focus returns to the control that opened Help.
13. Change the control, but do not save. NVDA should report the pending value. Press `Ctrl+R` or use `Review change`; both should open the review before saving.
14. Press `F5` and confirm the reload prompt. The original value should return. Close the editor without saving.
15. Press `Ctrl+B` or choose `Backups`, select a backup with the keyboard, cancel once, then reopen it and confirm restore. The current file should be backed up before restoration.

Record any failure with the key pressed, the last spoken label, and whether focus stayed in the expected pane. Automated smoke tests and accessibility trees do not replace this spoken-output check.
