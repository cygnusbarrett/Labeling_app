# 🎵 Frontend de Validador de Transcripciones - GUÍA RÁPIDA

## ✅ Estado: LISTO PARA USAR

El frontend está completamente implementado y funcional. Incluye:
- ✅ Template HTML con diseño moderno y responsive
- ✅ Autenticación JWT integrada
- ✅ Reproductor de audio HTML5
- ✅ Formulario de validación/corrección
- ✅ Indicador de progreso visual
- ✅ Vistas diferenciadas por rol (admin vs anotador)
- ✅ API Service con manejo de tokens

---

## 🚀 Ejecución

### Paso 1: Instalar Dependencias (si no las instalaste)
```bash
cd /Users/camilogutierrez/STEM/nuestra-memoria/Repos/Untitled/Labeling_app/src
pip install -r requirements/requirements.txt
```

### Paso 2: Cargar datos de prueba
```bash
python scripts/load_transcription_project.py
```

Deberías ver:
```
✅ Proyecto creado: memoria_1970_1990
✅ 496 palabras importadas
```

### Paso 3: Iniciar servidor Flask
```bash
python app.py
```

Deberías ver:
```
Servidor: http://localhost:8080
```

### Paso 4: Abrir en navegador
```
http://localhost:8080/transcription/validator
```

---

## 🔐 Credenciales de Prueba

### Admin (ve todas las palabras de todos los usuarios):
- **Usuario**: `admin`
- **Contraseña**: `admin123`

### Anotadores (ven solo sus palabras asignadas):
Puedes crear más usuarios en el admin panel o usar:
- **Usuario**: `annotator1`
- **Contraseña**: `1234`

---

## 🎯 Flujo de Uso

1. **Login**: Ingresa tus credenciales
2. **Selecciona Proyecto** (solo si eres admin): Elige el proyecto a validar
3. **Ve la Palabra**: Se muestra la palabra con probabilidad, hablante y timestamps
4. **Reproduce Audio**: Usa los botones para reproducir el segmento de audio
5. **Valida/Corrige**: 
   - **Aprobada ✓**: La palabra es correcta
   - **Corregida ✎**: La palabra necesita corrección (escribe la versión correcta)
6. **Siguiente**: Se carga automáticamente la siguiente palabra
7. **Progreso**: Ve el indicador de progreso actualizado en tiempo real

---

## 📊 Vistas por Rol

### Admin
- ✅ Selector de proyectos
- ✅ Ve TODAS las palabras del proyecto
- ✅ Estadísticas globales
- ✅ Puede asignar palabras a anotadores (via API)

### Anotador
- ✅ Ve solo SUS palabras asignadas
- ✅ Estadísticas personales
- ✅ No puede cambiar de proyecto

---

## 🎨 Características del Frontend

### Reproducción de Audio
- Reproductor HTML5 nativo
- Botones: Reproducir, Pausar, Repetir
- Controles de volumen y barra de progreso
- Audio con márgenes automáticos (0.2s antes y después)

### Validación
- Campo de corrección (opcional si es aprobada)
- Botones claramente diferenciados
- Confirmación visual de envío
- Mensajes de éxito/error

### Progreso Visual
- Barra de progreso con porcentaje
- Estadísticas en tiempo real
- Contador: X de Y palabras completadas
- Color gradient: púrpura (667eea → 764ba2)

### Responsivo
- Funciona en desktop, tablet y móvil
- Interfaz limpia y moderna
- Scroll automático al siguiente elemento

---

## 🔧 Estructura de Archivos

```
src/
├── templates/
│   └── transcription_validator.html    ← Template principal con HTML + CSS
├── static/
│   └── js/
│       ├── services/
│       │   └── transcriptionService.js ← API calls + JWT
│       └── controllers/
│           └── transcriptionController.js ← Lógica de negocio + UI
└── app.py                              ← Ruta /transcription/validator
```

---

## 🧪 Testing Rápido (sin iniciar servidor completo)

```bash
# Verificar que todo compila
python -m py_compile templates/transcription_validator.html static/js/services/transcriptionService.js static/js/controllers/transcriptionController.js

# Verificar sintaxis JavaScript
node -c static/js/services/transcriptionService.js
node -c static/js/controllers/transcriptionController.js
```

---

## 🐛 Troubleshooting

### "Token expirado" después de cerrar navegador
- Normal. Necesitas login nuevamente.
- El token se guarda en localStorage durante la sesión.

### Audio no se reproduce
- Verifica que el archivo .wav existe en la ruta correcta
- Mira la consola del navegador (F12 → Console) para errores

### La palabra no avanza después de enviar
- Comprueba que hay palabras pendientes en la BD
- Ejecuta: `sqlite3 src/labeling_app.db "SELECT COUNT(*) FROM words WHERE status='pending';"`

### "Acceso denegado" en algunos endpoints
- Anotadores solo ven sus propias palabras
- Si viste `annotator_id` vacío, el admin no te asignó palabras

---

## 🚀 Próximos Pasos (Mejoras Opcionales)

- [ ] Buscar palabras por texto
- [ ] Filtrar por hablante
- [ ] Descargar reporte de correcciones (CSV)
- [ ] Estadísticas gráficas (Chart.js)
- [ ] Teclado de accesos rápidos (Enter = aprobada, Ctrl+S = corregida)
- [ ] Dark mode
- [ ] Soporte para múltiples idiomas

---

## 📚 API Endpoints Disponibles

El frontend usa estos endpoints (ver `transcriptionService.js`):

```javascript
GET    /api/v2/transcriptions/projects                    // Listar proyectos
GET    /api/v2/transcriptions/projects/{id}               // Detalles proyecto
GET    /api/v2/transcriptions/projects/{id}/words         // Listar palabras (filtrado)
GET    /api/v2/transcriptions/projects/{id}/words/{id}    // Detalles palabra
GET    /api/v2/transcriptions/projects/{id}/words/{id}/audio // Descargar audio
POST   /api/v2/transcriptions/words/{id}                  // Enviar corrección
GET    /api/v2/transcriptions/projects/{id}/stats         // Estadísticas
POST   /api/v2/login                                       // Login JWT
```

---

## 💡 Consejos

1. **Usa Firefox o Chrome** para mejor compatibilidad
2. **Abre DevTools** (F12) para ver logs de JavaScript
3. **Prueba con Admin primero** para ver todas las palabras
4. **Crea usuarios de prueba** para probar vista de anotador
5. **Verifica la BD** con: `sqlite3 src/labeling_app.db "SELECT * FROM words LIMIT 5;"`

---

## ✨ ¡Listo!

Tu sistema está completamente funcional. ¡Anda y valida esas transcripciones! 🎵

---

**Última actualización**: Enero 28, 2026  
**Estado**: Producción Lista ✅
