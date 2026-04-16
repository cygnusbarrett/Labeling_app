/**
 * Admin Service para Panel Administrativo - Phase 2 (Transcripciones de Audio)
 */

class AdminService {
    constructor() {
        this.token = localStorage.getItem('access_token');
    }

    async makeRequest(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `/api/v1${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || `Error ${response.status}`);
            }
            return data;
        } catch (error) {
            console.error('Admin Service Error:', error);
            throw error;
        }
    }

    // ==================== USUARIOS ====================
    async getUsers() {
        return this.makeRequest('/admin/users');
    }

    async createUser(username, password, role = 'annotator') {
        return this.makeRequest('/admin/users', {
            method: 'POST',
            body: JSON.stringify({ username, password, role })
        });
    }

    async deleteUser(userId) {
        return this.makeRequest(`/admin/users/${userId}`, {
            method: 'DELETE'
        });
    }

    async getUserStats(userId) {
        return this.makeRequest(`/admin/users/${userId}/stats`);
    }

    // ==================== PROYECTOS ====================
    async getProjects() {
        return this.makeRequest('/admin/projects');
    }

    async getProjectStats(projectId) {
        return this.makeRequest(`/admin/projects/${projectId}/stats`);
    }

    // ==================== SEGMENTOS ====================
    async getSegments(projectId, status = 'all') {
        const statusParam = status !== 'all' ? `?status=${status}` : '';
        return this.makeRequest(`/admin/projects/${projectId}/segments${statusParam}`);
    }

    async assignSegment(projectId, segmentId, annotatorId) {
        return this.makeRequest(`/admin/projects/${projectId}/segments/${segmentId}/assign`, {
            method: 'POST',
            body: JSON.stringify({ annotator_id: annotatorId })
        });
    }

    async assignMultipleSegments(projectId, segmentIds, annotatorId) {
        const promises = segmentIds.map(segId => 
            this.assignSegment(projectId, segId, annotatorId)
        );
        return Promise.all(promises);
    }

    async unassignSegment(projectId, segmentId) {
        return this.makeRequest(`/admin/projects/${projectId}/segments/${segmentId}/unassign`, {
            method: 'POST'
        });
    }

    async unassignMultipleSegments(projectId, segmentIds) {
        const promises = segmentIds.map(segId =>
            this.unassignSegment(projectId, segId)
        );
        return Promise.all(promises);
    }

    async getAssignedSegments(projectId) {
        return this.makeRequest(`/admin/projects/${projectId}/assigned`);
    }

    // ==================== ESTADÍSTICAS ====================
    async getProjectStats(projectId) {
        return this.makeRequest(`/admin/projects/${projectId}/stats`);
    }

    async getAllStats() {
        return this.makeRequest('/admin/stats');
    }
}
