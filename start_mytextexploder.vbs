Set WshShell = CreateObject("WScript.Shell")
scriptPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run chr(34) & scriptPath & "\venv\Scripts\pythonw.exe" & chr(34) & " " & chr(34) & scriptPath & "\main.py" & chr(34), 0
Set WshShell = Nothing
