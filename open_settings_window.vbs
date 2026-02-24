Set WshShell = CreateObject("WScript.Shell")
scriptPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run chr(34) & scriptPath & "\venv\Scripts\pythonw.exe" & chr(34) & " " & chr(34) & scriptPath & "\ui.py" & chr(34), 1
Set WshShell = Nothing
