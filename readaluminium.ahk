
; פונקציה להמתנה לצבע מסוים במסך
wait_for_color(x, y, color) {
    CoordMode,Pixel,Screen
    maxAttempts :=50
    OutputVarColor := 0
    AttemptCount := 0
    while ( OutputVarColor != color) {
        PixelGetColor, OutputVarColor, x, y

        Sleep 200
        AttemptCount++
        if (AttemptCount >= maxAttempts) {
            MsgBox, color fail %x% %y% %OutputVarColor%
            return false
        }
    }
    return true
    }
; פתח את דפדפן פיירפוקס ונווט לאתר
Run, firefox.exe "https://www.lme.com/en/Metals/Non-ferrous/LME-Aluminium#Summary"
Sleep, 10000 ; המתן שהדף יטען
Clipboard = ""
if !wait_for_color(1018, 188, 0xFFFFFF) {
        MsgBox, too many tries to OPEN LME
        ExitApp
     }
MouseClick left,930,560
Sleep, 500
; העתק את תוכן הדף ללוח
Send, ^a ; בחר הכל
Sleep, 200
Send, ^c ; העתק ללוח
Sleep, 200

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

filePath := A_ScriptDir . "\aluminium_price.txt"

; שמור את התוכן בקובץ טקסט
FileAppend, %html%, %filePath%

; שלח Ctrl+F4 כדי לסגור את הטאב בפיירפוקס
Send, ^{F4}


