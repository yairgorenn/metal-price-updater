

; פתח את דפדפן פיירפוקס ונווט לאתר
Run, firefox.exe "https://www.lme.com/en/Metals/Non-ferrous/LME-Copper#Summary"
Sleep, 15000 ; המתן שהדף יטען

MouseClick left,930,560
Sleep, 2000

; העתק את תוכן הדף ללוח
Send, ^a ; בחר הכל
Sleep, 800
Send, ^c ; העתק ללוח
Sleep, 800

; המתן להעתקה ללוח
ClipWait, 2

; קרא את תוכן הלוח ושמור אותו במשתנה
html := Clipboard

; בדיקה אם הלוח מכיל תוכן
if (html == "")
{
    MsgBox, empty
    return
}

filePath := A_ScriptDir . "\copper_price.txt"


; שמור את התוכן בקובץ טקסט
FileAppend, %html%, %filePath%

; שלח Ctrl+F4 כדי לסגור את הטאב בפיירפוקס
Send, ^{F4}

