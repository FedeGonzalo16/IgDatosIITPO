# EduGrade Frontend - Guía de Inicio Rápido

## 🚀 Instalación Rápida

### 1. Instalar dependencias
```bash
cd frontend
npm install
```

### 2. Iniciar el servidor
```bash
npm start
```

La aplicación se abrirá en `http://localhost:3000`

## 🔐 Credenciales de Prueba

**Estudiante:**
- Email: `student@example.com`
- Contraseña: `123456`

**Administrador:**
- Email: `admin@example.com`
- Contraseña: `123456`

## 📱 Funcionalidades

### Dashboard de Estudiante
- Ver materias en curso
- Ver materias aprobadas con notas
- Ver historial académico detallado
- Descargar reporte académico
- Ver promedio general y estadísticas

### Panel de Administración
- **Estudiantes**: Buscar y filtrar estudiantes por estado
- **Materias**: Ver estadísticas de aprobación por materia
- **Calificaciones**: Ver registro de todas las calificaciones
- **Instituciones**: Gestionar instituciones educativas

## 📚 Datos de Ejemplo

El sistema viene con datos de ejemplo precargados:
- 4 estudiantes de prueba
- 6 materias (3 en curso, 3 aprobadas)
- 4 instituciones
- Historial de calificaciones completo

## 🎨 Características de Diseño

✨ **Interfaz moderna con:**
- Gradientes púrpura/azul
- Animaciones suaves
- Responsive design (mobile, tablet, desktop)
- Iconos profesionales
- Navegación intuitiva

## 🔧 Requisitos Técnicos

- Node.js 14+
- npm 6+ o yarn 1.22+
- Backend ejecutándose en `localhost:5000` (con mock data)

## 📝 Próximas Integraciones

Para conectar con el backend real:
1. Descomentar servicios de API en `src/services/api.js`
2. Reemplazar mock data con llamadas reales
3. Configurar autenticación con endpoints backend
4. Habilitar CORS en el backend

## ❓ Preguntas Frecuentes

**¿Cómo cambio los datos de prueba?**
- Edita los arrays `mockData` en cada página

**¿Cómo conecto con el backend real?**
- Ver sección "Conexión al Backend" en README.md

**¿Qué pasa con mi sesión?**
- Se guarda en localStorage. Persiste hasta limpiar datos del navegador

---

¡Listo! Tu aplicación está lista para usar. 🎉
