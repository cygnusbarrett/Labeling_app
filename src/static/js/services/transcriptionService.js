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
                    this.token = null;
                    localStorage.removeItem('token');
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
     * Envía una corrección de segmento (antes "palabra")
     */
    async submitWord(wordId, status, correctedText = null) {
        const data = {
            review_status: status,  // Usar review_status para segmentos
            status: status  // Para backward compatibility
        };
        if (correctedText) {
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
    logout() {
        this.token = null;
        // Limpiar con la clave correcta
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('current_user');
    }
}

// Instancia global del servicio
const transcriptionService = new TranscriptionService();
