# 🔗 Guía: Integración con Backend Real

Esta guía te ayudará a conectar el frontend React con tu backend Python/Flask.

## 📋 Checklist Previo

Antes de empezar:

- [ ] Backend ejecutándose en `http://localhost:5000`
- [ ] CORS habilitado en el backend
- [ ] Endpoints de autenticación implementados
- [ ] Base de datos MongoDB populada
- [ ] Variables de entorno correctas

---

## 🔐 Paso 1: Implementar Autenticación en Backend

El backend necesita estos endpoints:

### POST /auth/login
**Request:**
```json
{
  "email": "student@example.com",
  "password": "123456"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": "507f1f77bcf86cd799439011",
    "nombre": "Juan",
    "email": "student@example.com",
    "rol": "student",
    "legajo": "STU20241001"
  }
}
```

### POST /auth/register
**Request:**
```json
{
  "nombre": "Juan",
  "apellido": "González",
  "email": "juan@example.com",
  "password": "123456",
  "documento": "12345678",
  "legajo": "STU20241001",
  "fecha_nacimiento": "2005-03-15"
}
```

**Response:** (mismo que login)

---

## 🛠️ Paso 2: Configurar el Frontend

### 1. Variables de Entorno (.env)

```env
REACT_APP_API_BASE_URL=http://localhost:5000/api/v1
REACT_APP_API_NEO4J_URL=http://localhost:5001/api
REACT_APP_API_REDIS_URL=http://localhost:5002/api
REACT_APP_API_CASSANDRA_URL=http://localhost:5003/api
```

### 2. Habilitar CORS en Backend (Flask)

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Habilita CORS para todas las rutas
```

O específicamente:

```python
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

---

## 💻 Paso 3: Descomentar Servicios en Frontend

### En `src/pages/Login.js`

**Cambiar de:** (líneas 50-55)
```javascript
// Simulamos la autenticación
const mockUser = {
  id: '1',
  nombre: 'Estudiante',
  email: email,
  rol: email.includes('admin') ? 'admin' : 'student',
  legajo: 'STU20241001'
};
const mockToken = 'mock-token-' + Date.now();
```

**A:** (usar el servicio real)
```javascript
import { authService } from '../services/api';

// Llamar al backend real
try {
  const response = await authService.login(email, password);
  const { user, token } = response.data;
  onLogin(user, token);
  navigate(user.rol === 'admin' ? '/admin' : '/student');
} catch (error) {
  setError('Email o contraseña incorrectos');
}
```

### En `src/pages/Register.js`

**Cambiar de:** (líneas 70-75)
```javascript
// Esperar un momento y redirigir
setTimeout(() => {
  alert('Registro exitoso. Por favor inicia sesión.');
  navigate('/login');
}, 1000);
```

**A:**
```javascript
import { authService } from '../services/api';

try {
  await authService.register(formData);
  alert('Registro exitoso. Por favor inicia sesión.');
  navigate('/login');
} catch (error) {
  setError('Error al registrar. El email podría estar duplicado.');
}
```

---

## 📚 Paso 4: Cargar Datos Reales en Dashboards

### En `src/pages/StudentDashboard.js`

**Cambiar de:** (líneas 50-100)
```javascript
// Datos simulados
const mockSubjects = [
  { id: 1, codigo: 'MAT-001', nombre: 'Matemática', ... },
  ...
];
setSubjects(mockSubjects);
```

**A:**
```javascript
import { gradeService, subjectService } from '../services/api';

useEffect(() => {
  const loadSubjects = async () => {
    try {
      const response = await gradeService.getByStudent(user.id);
      setSubjects(response.data);
      
      // Calcular estadísticas
      const passed = response.data.filter(s => s.estado === 'aprobada').length;
      const inProgress = response.data.filter(s => s.estado === 'cursando').length;
      const grades = response.data.filter(s => s.nota).map(s => s.nota);
      const avg = grades.length > 0 ? (grades.reduce((a,b) => a+b) / grades.length).toFixed(2) : 0;
      
      setStats({
        totalSubjects: response.data.length,
        passedSubjects: passed,
        averageGrade: avg,
        inProgress: inProgress
      });
    } catch (error) {
      console.error('Error cargando materias:', error);
    } finally {
      setLoading(false);
    }
  };
  
  loadSubjects();
}, [user.id]);
```

### En `src/pages/AdminDashboard.js`

**Cambiar de:** (líneas 60-130)
```javascript
// Datos simulados para cada tab
if (activeTab === 'students') {
  mockData = [
    { id: 1, legajo: 'STU20241001', ... },
    ...
  ];
}
```

**A:**
```javascript
import { studentService, subjectService, gradeService, institutionService } from '../services/api';

const loadData = async () => {
  try {
    let response;
    
    if (activeTab === 'students') {
      response = await studentService.getAll({ 
        pagina: 1, 
        limite: 100,
        estado: filters.estado 
      });
      setData(response.data);
    } else if (activeTab === 'subjects') {
      response = await subjectService.getAll({ limite: 100 });
      setData(response.data);
    } else if (activeTab === 'grades') {
      response = await gradeService.getAll({ limite: 100 });
      setData(response.data);
    } else if (activeTab === 'institutions') {
      response = await institutionService.getAll({ limite: 100 });
      setData(response.data);
    }
    
    setLoading(false);
  } catch (error) {
    console.error('Error cargando datos:', error);
    setLoading(false);
  }
};

useEffect(() => {
  loadData();
}, [activeTab, filters]);
```

---

## 🔄 Paso 5: Usar Servicios Avanzados (Opcional)

Para consultas con Neo4j, Redis y Cassandra:

```javascript
// En un componente admin
import { neo4jService, cassandraService } from '../services/advancedServices';

// Obtener trayectoria de un estudiante
const getTrayectory = async (studentId) => {
  try {
    const response = await neo4jService.getStudentTrayectory(studentId);
    console.log('Trayectoria:', response.data);
  } catch (error) {
    console.error('Error:', error);
  }
};

// Obtener auditoría
const getAudit = async () => {
  try {
    const response = await cassandraService.getAuditLog();
    console.log('Auditoría:', response.data);
  } catch (error) {
    console.error('Error:', error);
  }
};
```

---

## ✅ Verificación: Checklist de Integración

### Backend
- [ ] Endpoints `/auth/login` y `/auth/register` implementados
- [ ] Array `Authorization: Bearer {token}` en headers
- [ ] CORS habilitado
- [ ] Validaciones de entrada
- [ ] Respuestas en formato JSON correcto

### Frontend
- [ ] .env actualizado con URLs correctas
- [ ] authService.login() descomentar y usar
- [ ] authService.register() descomentar y usar
- [ ] Datos reales cargados en dashboards
- [ ] Manejo de errores implementado

### Pruebas
- [ ] Login con credenciales correctas
- [ ] Login rechaza credenciales incorrectas
- [ ] Registro de nuevo estudiante funciona
- [ ] Dashboard carga materias del estudiante
- [ ] Admin ve datos correctos
- [ ] Búsqueda y filtros funcionan

---

## 🐛 Troubleshooting

### Error: CORS Policy blocked request
**Solución:** Habilita CORS en el backend (ver Paso 2)

### Error: 404 on login attempt
**Solución:** Verifica que el endpoint `/auth/login` existe en el backend

### Datos vacíos en dashboard
**Solución:** 
- Verifica que tu estudiante tiene materias en la BD
- Revisa la consola (F12) para errores
- Comprueba que el user.id se está pasando correctamente

### Token no se guarda
**Solución:** Verifica que localStorage no está bloqueado en navegador

### Backend retorna 401 en requests posteriores
**Solución:** El token no se está enviando correctamente
```javascript
// En api.js, verifica que está así:
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

---

## 📝 Archivo de Ejemplo: Login Real

Aquí hay un ejemplo completo de login con backend real:

```javascript
// src/pages/LoginReal.js
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/api';

const Login = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Llamar al backend real
      const response = await authService.login(email, password);
      
      // response.data contains: { user, token }
      const { user, token } = response.data;
      
      // Guardar en localStorage
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
      
      // Llamar callback del componente padre
      onLogin(user, token);
      
      // Redirigir según rol
      navigate(user.rol === 'admin' ? '/admin' : '/student');
      
    } catch (err) {
      // Manejo de errores
      if (err.response?.status === 401) {
        setError('Email o contraseña incorrectos');
      } else if (err.response?.status === 404) {
        setError('Usuario no encontrado');
      } else {
        setError('Error al conectar con el servidor');
      }
      console.error('Login error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Formulario igual que antes */}
    </form>
  );
};

export default Login;
```

---

## 🎓 Próximas Integraciones

Una vez que el login funcione:

1. **Cargar materias reales**
   - Descomentar `gradeService.getByStudent()`
   - Mostrar datos en dashboard

2. **Cargar datos admin**
   - Descomentar `studentService.getAll()`
   - Implementar búsqueda y filtros

3. **Neo4j Analytics**
   - Usar `neo4jService.getStudentTrayectory()`
   - Mostrar recomendaciones

4. **Cassandra Auditoría**
   - Usar `cassandraService.getAuditLog()`
   - Mostrar historial de cambios

---

## 📞 Necesitas Ayuda?

Consulta:
1. [README.md](./README.md) - Documentación general
2. [src/services/api.js](./src/services/api.js) - Servicios disponibles
3. [src/services/EXAMPLES.md](./src/services/EXAMPLES.md) - Ejemplos de código

---

**¡Éxito con la integración!** 🚀
