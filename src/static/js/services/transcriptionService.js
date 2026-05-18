/**
 * Servicio de Transcripción - Llamadas a API REST
 */

class TranscriptionService {
    constructor() {
        this.apiBase = '/api/v2/transcriptions';
        this.audioBlobCache = new Map();
    }

    buildAudioEndpoint(projectId, wordId, params = {}) {
        const queryParams = new URLSearchParams(params);
        const queryString = queryParams.toString();
        return `${this.apiBase}/projects/${projectId}/words/${wordId}/audio${queryString ? `?${queryString}` : ''}`;
    }

    trimAudioCache(maxEntries = 24) {
        while (this.audioBlobCache.size > maxEntries) {
            const oldestKey = this.audioBlobCache.keys().next().value;
            this.audioBlobCache.delete(oldestKey);
        }
    }

    async fetchAudioBlob(url) {
        if (!this.audioBlobCache.has(url)) {
            const blobPromise = fetch(url, {
                credentials: 'same-origin',
            }).then(async (response) => {
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`Error ${response.status} al descargar audio: ${errorText || response.statusText}`);
                }

                return await response.blob();
            }).catch((error) => {
                this.audioBlobCache.delete(url);
                throw error;
            });

            this.audioBlobCache.set(url, blobPromise);
            this.trimAudioCache();
        }

        return await this.audioBlobCache.get(url);
    }

    /**
     * Obtiene el header de autorización
     */
    getAuthHeader() {
        return {
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
            const response = await fetch(url, {
                ...options,
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                if (response.status === 401) {
                    localStorage.removeItem('current_user');
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
        const url = this.buildAudioEndpoint(projectId, wordId, { margin });
        const blob = await this.fetchAudioBlob(url);
        return URL.createObjectURL(blob);
    }

    async prefetchWordAudio(projectId, wordId, margin = 0.2) {
        const url = this.buildAudioEndpoint(projectId, wordId, { margin });
        await this.fetchAudioBlob(url);
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
        const url = this.buildAudioEndpoint(projectId, wordId, {
            start_override: startTime,
            end_override: endTime,
            margin: 0.1,
        });
        const blob = await this.fetchAudioBlob(url);
        return URL.createObjectURL(blob);
    }

    clearAudioCache() {
        this.audioBlobCache.clear();
    }

    /**
     * Envía una corrección de segmento (antes "palabra")
     */
    async submitWord(wordId, status, correctedText = null, decisionType = null) {
        const data = {
            review_status: status,  // Usar review_status para segmentos
            status: status  // Para backward compatibility
        };
        if (decisionType) {
            data.decision_type = decisionType;
        }
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

    async getCurrentUser() {
        const response = await fetch('/me', {
            method: 'GET',
            credentials: 'same-origin',
        });

        if (!response.ok) {
            throw new Error('Sesión inválida');
        }

        const data = await response.json();
        if (data?.user) {
            localStorage.setItem('current_user', JSON.stringify(data.user));
            return data.user;
        }

        throw new Error('Usuario no autenticado');
    }

    /**
     * Verifica si el token es válido
     */
    isAuthenticated() {
        return localStorage.getItem('current_user') !== null;
    }

    /**
     * Limpia la sesión
     */
    logout() {
        localStorage.removeItem('current_user');
    }
}

// Instancia global del servicio
const transcriptionService = new TranscriptionService();
