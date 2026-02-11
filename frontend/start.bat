@echo off
REM Script para instalar y ejecutar EduGrade Frontend en Windows

echo ==================================
echo 🎓 EduGrade - Frontend Setup
echo ==================================
echo.

REM Verificar que Node.js está instalado
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Node.js no está instalado.
    echo    Descargar desde: https://nodejs.org/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node -v') do set NODE_VERSION=%%i
for /f "tokens=*" %%i in ('npm -v') do set NPM_VERSION=%%i

echo ✅ Node.js encontrado: %NODE_VERSION%
echo ✅ npm encontrado: %NPM_VERSION%
echo.

REM Navegar a carpeta frontend
cd /d "%~dp0"

REM Instalar dependencias
echo 📦 Instalando dependencias...
call npm install

if %ERRORLEVEL% NEQ 0 (
    echo ❌ Error al instalar dependencias
    pause
    exit /b 1
)

echo ✅ Dependencias instaladas correctamente
echo.
echo ==================================
echo 🚀 Iniciando aplicación...
echo ==================================
echo.
echo 📍 URL: http://localhost:3000
echo.
echo 🔐 Credenciales de prueba:
echo    Estudiante: student@example.com / 123456
echo    Admin: admin@example.com / 123456
echo.
echo Presiona Ctrl+C para detener la aplicación
echo ==================================
echo.

REM Iniciar aplicación
call npm start

pause
