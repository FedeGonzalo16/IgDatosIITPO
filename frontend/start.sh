#!/bin/bash
# Script para instalar y ejecutar EduGrade Frontend

echo "=================================="
echo "🎓 EduGrade - Frontend Setup"
echo "=================================="
echo ""

# Verificar que Node.js está instalado
if ! command -v node &> /dev/null; then
    echo "❌ Node.js no está instalado."
    echo "   Descargar desde: https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js encontrado: $(node -v)"
echo "✅ npm encontrado: $(npm -v)"
echo ""

# Navegar a carpeta frontend
cd "$(dirname "$0")" || exit

# Instalar dependencias
echo "📦 Instalando dependencias..."
npm install

if [ $? -eq 0 ]; then
    echo "✅ Dependencias instaladas correctamente"
else
    echo "❌ Error al instalar dependencias"
    exit 1
fi

echo ""
echo "=================================="
echo "🚀 Iniciando aplicación..."
echo "=================================="
echo ""
echo "📍 URL: http://localhost:3000"
echo ""
echo "🔐 Credenciales de prueba:"
echo "   Estudiante: student@example.com / 123456"
echo "   Admin: admin@example.com / 123456"
echo ""
echo "Presiona Ctrl+C para detener la aplicación"
echo "=================================="
echo ""

# Iniciar aplicación
npm start
