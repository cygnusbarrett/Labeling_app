/**
 * Servicio de Transcripción - Llamadas a API REST
 */

class TranscriptionService {
    constructor() {
        this.apiBase = '/api/v2/transcriptions';
        // Leer token de localStorage con la clave correcta (compatible con JWT service)
        this.token = localStorage.getItem('access_token') || null;
    }

    /**
     * Establece el token JWT
     */
    setToken(token) {
        this.token = token;
        // Guardar con la clave correcta para que otros servicios lo encuentren
        localStorage.setItem('access_token', token);
    }

    /**
     * Obtiene el header de autorización
     */
    getAuthHeader() {
        return {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
        };
    }

    /**
     * Limpia estado de autenticación del navegador (storage + cookies)
     */
    clearBrowserAuthState() {
        this.token = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('current_user');

        // Limpiar cookies usadas por rutas HTML protegidas
        document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
        document.cookie = 'refresh_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
        document.cookie = 'labeling_session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    }

    /**
     * Realiza una llamada a la API
     */
    async apiCall(method, endpoint, data = null) {
        const url = `${this.apiBase}${endpoint}`;
        const options = {
            method: method,
            headers: this.getAuthHeader()
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, options);
            
            if (!response.ok) {
                if (response.status === 401) {
                    this.clearBrowserAuthState();
                    throw new Error('Token expirado. Por favor, inicia sesión nuevamente.');
                }
                throw new Error(`Error ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`Error en API call: ${endpoint}`, error);
            throw error;
        }
    }

    /**
     * Obtiene lista de proyectos
     */
    async getProjects() {
        return await this.apiCall('GET', '/projects');
    }

    /**
     * Obtiene detalles de un proyecto
     */
    async getProject(projectId) {
        return await this.apiCall('GET', `/projects/${projectId}`);
    }

    /**
     * Obtiene lista de palabras pendientes
     */
    async getWords(projectId, status = 'pending', limit = 50, offset = 0) {
        const params = new URLSearchParams({
            status: status,
            limit: limit,
            offset: offset
        });
        return await this.apiCall('GET', `/projects/${projectId}/words?${params}`);
    }

    /**
     * Obtiene detalles de una palabra específica
     */
    async getWord(projectId, wordId) {
        return await this.apiCall('GET', `/projects/${projectId}/words/${wordId}`);
    }

    /**
     * Descarga el audio de una palabra
     */
    async getWordAudio(projectId, wordId, margin = 0.2) {
        const url = `${this.apiBase}/projects/${projectId}/words/${wordId}/audio?margin=${margin}`;
        console.log('📥 Descargando audio de:', url);
        
        try {
            const response = await fetch(url, {
                headers: this.getAuthHeader()
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ Error en descarga de audio:', response.status, errorText);
                throw new Error(`Error ${response.status} al descargar audio: ${response.statusText}`);
            }

            const blob = await response.blob();
            console.log('✅ Blob de audio recibido:', blob.size, 'bytes');
            
            const objectUrl = URL.createObjectURL(blob);
            console.log('✅ URL de objeto creada:', objectUrl);
            
            return objectUrl;
        } catch (error) {
            console.error('❌ Error en getWordAudio:', error);
            throw error;
        }
    }

    /**
     * Obtiene contexto de segmentos adyacentes
     */
    async getSegmentContext(projectId, wordId) {
        return await this.apiCall('GET', `/projects/${projectId}/words/${wordId}/context`);
    }

    /**
     * Descarga audio con rango de tiempo personalizado (para contexto extendido)
     */
    async getExtendedAudio(projectId, wordId, startTime, endTime) {
        const url = `${this.apiBase}/projects/${projectId}/words/${wordId}/audio?start_override=${startTime}&end_override=${endTime}&margin=0.1`;
        const response = await fetch(url, { headers: this.getAuthHeader() });
        if (!response.ok) throw new Error(`Error ${response.status}`);
        const blob = await response.blob();
        return URL.createObjectURL(blob);
    }

    /**
     * Envía una corrección de segmento (antes "palabra")
     */
    async submitWord(wordId, status, correctedText = null, extraPayload = {}) {
        const data = {
            review_status: status,  // Usar review_status para segmentos
            status: status,  // Para backward compatibility
            ...extraPayload
        };
        if (correctedText !== null && correctedText !== undefined) {
            data.text_revised = correctedText;  // Usar text_revised para segmentos
            data.corrected_text = correctedText;  // Para backward compatibility
        }
        return await this.apiCall('POST', `/words/${wordId}`, data);
    }

    /**
     * Obtiene estadísticas del proyecto
     */
    async getStats(projectId) {
        return await this.apiCall('GET', `/projects/${projectId}/stats`);
    }

    /**
     * Verifica si el token es válido
     */
    isAuthenticated() {
        return this.token !== null;
    }

    /**
     * Limpia la sesión
     */
    async logout() {
        try {
            // Avisar al backend para limpieza de cookies del lado servidor
            await fetch('/logout', {
                method: 'POST',
                headers: this.token ? this.getAuthHeader() : { 'Content-Type': 'application/json' }
            });
        } catch (error) {
            console.warn('Logout backend falló, se limpiará sesión local igual:', error);
        } finally {
            this.clearBrowserAuthState();
        }
    }
}

// Instancia global del servicio
const transcriptionService = new TranscriptionService();
