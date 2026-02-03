' ========================================================================
' VBScript wrapper to run scheduler in background
' This is MORE RELIABLE than batch file - won't stop when other batch files run
' Use this for Windows Startup instead of .bat file
' ========================================================================

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script is located
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Change to script directory
WshShell.CurrentDirectory = scriptDir

' Create logs directory if it doesn't exist
logsDir = scriptDir & "\logs"
If Not fso.FolderExists(logsDir) Then
    fso.CreateFolder(logsDir)
End If

' Log startup
Set logFile = fso.OpenTextFile(logsDir & "\scheduler_startup.log", 8, True)
logFile.WriteLine Now & " - Scheduler started via VBScript wrapper"
logFile.Close

' Path to pythonw.exe in venv
pythonwPath = Chr(34) & scriptDir & "\venv\Scripts\pythonw.exe" & Chr(34)
scriptPath = Chr(34) & scriptDir & "\run_sync_scheduler.py" & Chr(34)

' Run pythonw.exe with the script
' WindowStyle = 0 means hidden window (pythonw already has no window, but this ensures it)
' WaitOnReturn = False means don't wait for the process to finish
WshShell.Run pythonwPath & " " & scriptPath, 0, False

' Log that process was started
Set logFile = fso.OpenTextFile(logsDir & "\scheduler_startup.log", 8, True)
logFile.WriteLine Now & " - Pythonw process launched (detached)"
logFile.Close
