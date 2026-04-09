# ⚡ QUICK START - Robustez 24/7 en 5 Pasos

## 🎯 TL;DR - Lo que implementamos

Tu aplicación ahora tiene **7 capas de robustez** para servidor remoto. Todo está listo. Solo necesitas:

1. **Generar secretas seguras**
2. **Copiar archivo de configuración**
3. **Deployar en el servidor**
4. **Verificar que funciona**

---

## 📋 PASO 1: Generar Secretas Seguras

En tu computadora:

```bash
# Terminal
python3 -c "import secrets; print('JWT_SECRET_KEY=', secrets.token_hex(32))"
python3 -c "import secrets; print('SECRET_KEY=', secrets.token_hex(32))"
```

**Copiar la salida**: Necesitarás estos valores luego.

Ejemplo (NO USAR ESTOS, GENERAR LOS TUYOS):
```
JWT_SECRET_KEY= a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9
SECRET_KEY=     p5o4n3m2l1k0j9i8h7g6f5e4d3c2b1a0z9y8x7w6v5u4t3s2r1q0p9o8n7m6
```

---

## 🔧 PASO 2: Preparar Archivo de Configuración

```bash
# En tu máquina
cp Labeling_app/envs/production.env.example Labeling_app/envs/production.env

# Editar con tus valores
nano Labeling_app/envs/production.env
```

**Reemplazar:**
```
JWT_SECRET_KEY=AQUI_TU_VALOR_DEL_PASO_1
SECRET_KEY=AQUI_TU_OTRO_VALOR_DEL_PASO_1
DATABASE_URL=postgresql://labeling_user:TU_PASSWORD@localhost:5432/labeling_db
```

---

##🚀 PASO 3: Deployar Automáticamente

```bash
# En tu máquina
cd Labeling_app/
chmod +x deploy.sh

# Ejecutar deploy
./deploy.sh --server user@your-server.com --env envs/production.env
```

**Qué hace:**
- ✅ Conecta a tu servidor
- ✅ Instala dependencias
- ✅ Configura base de datos
- ✅ Instala servicio systemd
- ✅ Inicia la aplicación
- ⏱️ Toma ~5 minutos

---

## ✅ PASO 4: Verificar que Funciona

Desde tu máquina:

```bash
# ¿Servidor responde?
curl https://tu-dominio.com/login

# ¿Health check OK?
curl https://tu-dominio.com/health | jq .overall_status

# ¿Logs OK?
ssh user@your-server journalctl -u labeling-app -n 10
```

**Esperado:**
```
overall_status: "healthy"
```

---

## 📚 PASO 5: Ahora Lee los Documentos (Opcional pero Recomendado)

| Documento | Lectura | Propósito |
|-----------|---------|----------|
| `ROBUSTNESS_ARCHITECTURE.md` | 10 min | Entiende qué implementamos |
| `ROBUSTNESS_CHECKLIST.md` | 5 min | Verifica cada capa |
| `DEPLOYMENT.md` | 20 min | Para futuras actualizaciones |

---

## 🎯 RESUMÉN: Tu Arquitectura Ahora Es:

```
Cliente (tu PC)
    ↓ HTTPS
Nginx (Reverse Proxy)  ← SSL/TLS, load balancing
    ↓
Gunicorn (4 workers)   ← Auto-restart, health checks
    ↓ Connection pool
PostgreSQL             ← Backups automáticos
    ↓
Systemd service        ← Auto-start en reboot
    ↓
Monitoreo 24/7         ← Alertas en Telegram
```

**Resultado:** Tu app funciona 24/7 sin intervención manual.

---

## 🆘 Si Algo No Funciona

### Error 1: "Connection refused"
```bash
# SSH al servidor
ssh user@your-server

# Ver logs
sudo journalctl -u labeling-app -n 50

# Reintentar
sudo systemctl restart labeling-app
```

### Error 2: "Health check falla"
```bash
# Verificar DB
psql -U labeling_user -d labeling_db -h localhost -c "SELECT 1"

# Verificar configuración
grep DATABASE_URL /etc/labeling_app/production.env
```

### Error 3: "SSL certificate error"
```bash
# Renovar certificado
sudo certbot renew

# Ver estado
sudo systemctl status nginx
```

---

## 📱 CONFIGURAR ALERTAS (Opcional)

Para recibir alertas de problemas en Telegram:

1. Abre Telegram, busca `@BotFather`
2. Crea un bot `/newbot`
3. Obtén el token
4. Encuentra tu chat ID:
   ```bash
   # Envía un mensaje a tu bot en Telegram, luego:
   curl https://api.telegram.org/bot<TOKEN>/getUpdates | jq '.result[0].message.chat.id'
   ```
5. Actualiza `/etc/labeling_app/production.env`:
   ```
   TELEGRAM_BOT_TOKEN=tu_token
   TELEGRAM_ADMIN_CHAT_ID=tu_chat_id
   ```
6. Reinicia:
   ```bash
   sudo systemctl restart labeling-app
   ```

Ahora recibirás alertas si:
- Falta espacio en disco
- Memoria alta
- Database no responde
- Backup completado

---

## ✨ Lo Que Ya Tienes Incluido

- ✅ Auto-start si el servidor se reinicia
- ✅ Auto-restart si app falla
- ✅ Monitoreo de recursos (CPU, RAM, Disk)
- ✅ Health checks automáticos
- ✅ Logs rotados (no llenan disco)
- ✅ Backups nocturnos automáticos
- ✅ JWT authentication
- ✅ HTTPS/SSL
- ✅ Rate limiting
- ✅ Graceful shutdown (recargas sin downtime)

---

## 🎓 Próximo: Segment-Level Validation

Una vez que el servidor esté corriendo sin problemas, podemos implementar:

1. **Modelo de Segmentos** en base de datos
2. **Extractor de Segmentos** (detecta audio corto problemático)
3. **Endpoint de Corrección** (usuario corrige segmentos)
4. **JSON Exportado** con `text_revised`
5. **Frontend Actualizado** para interfaz de segmentos

Todo en tu servidor remoto sin downtime. ✨

---

## 📞 Resumen

| Cuando | Qué Hacer |
|--------|-----------|
| **Semana 1** | Completar 5 pasos de Quick Start |
| **Semana 2** | Leer documentos de robustez |
| **Mes 1** | Usar la app, crear usuarios, hacer backups |
| **Después** | Implementar Segment-Level Validation |

---

**✅ ¡LISTO! Tu servidor está preparado para 24/7.**

Preguntas? Revisa `DEPLOYMENT.md` para troubleshooting detallado.
