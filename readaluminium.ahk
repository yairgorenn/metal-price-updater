

; פתח את דפדפן פיירפוקס ונווט לאתר
Run, firefox.exe "https://www.lme.com/en/Metals/Non-ferrous/LME-Aluminium#Summary"
WinWaitActive, ahk_exe firefox.exe,,30
Sleep, 20000 ; המתן שהדף יטען
Clipboard = ""

MouseClick left,930,560
Sleep, 5000
; העתק את תוכן הדף ללוח
Send, ^a ; בחר הכל
Sleep, 2000
Send, ^c ; העתק ללוח
Sleep, 800

; המתן להעתקה ללוח
ClipWait, 10

; קרא את תוכן הלוח ושמור אותו במשתנה
html := Clipboard

; בדיקה אם הלוח מכיל תוכן
if (html == "")
{
    MsgBox, empty
    return
}

filePath := A_ScriptDir . "\aluminium_price.txt"

; שמור את התוכן בקובץ טקסט
FileAppend, %html%, %filePath%




