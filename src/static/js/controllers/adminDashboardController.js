/**
 * Admin Dashboard Controller - Lógica del panel administrativo Phase 2
 */

let adminService;
let currentUser = null;
let currentProject = null;

async function initAdminDashboard() {
    try {
        adminService = new AdminService();
        
        // Verificar que sea admin
        const token = localStorage.getItem('access_token');
        if (!token) {
            window.location.href = '/login';
            return;
        }

        // Extraer info del token
        const tokenPayload = JSON.parse(atob(token.split('.')[1]));
        if (tokenPayload.role !== 'admin') {
            window.location.href = '/transcription/validator';
            return;
        }

        currentUser = tokenPayload;
        document.getElementById('currentAdmin').textContent = currentUser.username;

        // Cargar datos iniciales
        await loadOverviewTab();
        await loadUsersTab();
        await loadAssignmentsTab();
        await loadQualityTab();

    } catch (error) {
        console.error('Error inicializando dashboard:', error);
        showMessage('Error al cargar el panel administrativo', 'error', 'overview');
    }
}

// ==================== NAVEGACIÓN ====================

function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });

    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');

    // Recargar datos si es necesario
    if (tabName === 'users') loadUsersTab();
}

// ==================== TAB: RESUMEN ====================

async function loadOverviewTab() {
    try {
        // Cargar proyectos y estadísticas
        const projectsData = await adminService.getProjects();
        const projects = projectsData.projects || [];

        if (projects.length === 0) {
            showMessage('No hay proyectos disponibles', 'info', 'overview');
            return;
        }

        currentProject = projects[0];
        const stats = await adminService.getProjectStats(currentProject.id);

        // Mostrar estadísticas globales
        const statsGrid = document.getElementById('statsGrid');
        statsGrid.innerHTML = `
            <div class="stat-card">
                <h3>Total Segmentos</h3>
                <div class="value">${stats.total_segments || 0}</div>
                <div class="subtext">en el proyecto</div>
            </div>
            <div class="stat-card">
                <h3>Completados</h3>
                <div class="value">${(stats.approved_segments || 0) + (stats.corrected_segments || 0)}</div>
                <div class="subtext">${stats.words_completed_percentage || 0}% del total</div>
            </div>
            <div class="stat-card">
                <h3>Pendientes</h3>
                <div class="value">${stats.pending_segments || 0}</div>
                <div class="subtext">por revisar</div>
            </div>
            <div class="stat-card">
                <h3>Anotadores</h3>
                <div class="value">${stats.total_annotators || 1}</div>
                <div class="subtext">usuarios activos</div>
            </div>
        `;

        // Cargar estadísticas por usuario
        await loadUserStats();

    } catch (error) {
        console.error('Error en tab resumen:', error);
        showMessage('Error al cargar estadísticas', 'error', 'overview');
    }
}

async function loadUserStats() {
    try {
        const usersData = await adminService.getUsers();
        const users = usersData.users || [];

        const tbody = document.getElementById('userStatsBody');
        tbody.innerHTML = '';

        for (const user of users) {
            if (user.role === 'admin') continue; // No mostrar admins

            const stats = await adminService.getUserStats(user.id);
            const completed = (stats.approved_segments || 0) + (stats.corrected_segments || 0);
            const total = stats.total_segments || 0;
            const progress = total > 0 ? (completed / total) * 100 : 0;

            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${user.username}</strong></td>
                <td><span class="badge">${user.role}</span></td>
                <td>${completed} / ${total}</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                    <small style="color: #999;">${progress.toFixed(0)}%</small>
                </td>
                <td>
                    <button class="btn btn-primary" onclick="viewUserDetail(${user.id})">📊 Ver</button>
                </td>
            `;
            tbody.appendChild(row);
        }
    } catch (error) {
        console.error('Error cargando stats de usuarios:', error);
    }
}

// ==================== TAB: USUARIOS ====================

async function loadUsersTab() {
    try {
        const usersData = await adminService.getUsers();
        const users = usersData.users || [];

        const tbody = document.getElementById('usersTableBody');
        tbody.innerHTML = '';

        for (const user of users) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${user.username}</strong></td>
                <td>
                    <span class="badge ${user.role === 'admin' ? 'admin' : ''}">
                        ${user.role === 'admin' ? '👑 Admin' : '👤 Anotador'}
                    </span>
                </td>
                <td>${new Date(user.created_at || Date.now()).toLocaleDateString('es-ES')}</td>
                <td class="action-buttons">
                    ${user.role !== 'admin' ? `
                        <button class="btn btn-danger" onclick="deleteUserConfirm(${user.id}, '${user.username}')">🗑️ Eliminar</button>
                    ` : '<small style="color: #999;">Principal</small>'}
                </td>
            `;
            tbody.appendChild(row);
        }
    } catch (error) {
        console.error('Error cargando usuarios:', error);
        showMessage('Error al cargar usuarios', 'error', 'users');
    }
}

// ==================== TAB: ASIGNACIONES ====================

async function loadAssignmentsTab() {
    try {
        // Cargar proyectos
        const projectsData = await adminService.getProjects();
        const projects = projectsData.projects || [];

        const projectSelect = document.getElementById('projectSelect');
        projectSelect.innerHTML = '<option value="">Selecciona un proyecto</option>';
        
        projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.id;
            option.textContent = `${project.name} (${project.words_to_review || 0} pendientes)`;
            projectSelect.appendChild(option);
        });

        // Cargar anotadores
        const usersData = await adminService.getUsers();
        const users = usersData.users || [];

        const annotatorSelect = document.getElementById('annotatorSelect');
        annotatorSelect.innerHTML = '<option value="">Selecciona un anotador</option>';
        
        users.forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = user.role === 'admin' ? `${user.username} (admin)` : user.username;
            annotatorSelect.appendChild(option);
        });

    } catch (error) {
        console.error('Error cargando assignments tab:', error);
        showMessage('Error al cargar asignaciones', 'error', 'assignments');
    }
}

async function loadSegments() {
    try {
        const projectId = document.getElementById('projectSelect').value;
        if (!projectId) {
            showMessage('Selecciona un proyecto', 'info', 'assignments');
            return;
        }

        const segmentsData = await adminService.getSegments(projectId, 'pending');
        const segments = segmentsData.words || [];

        const segmentsSelect = document.getElementById('segmentsSelect');
        segmentsSelect.innerHTML = '';

        if (segments.length === 0) {
            segmentsSelect.innerHTML = '<option>No hay segmentos sin asignar</option>';
            return;
        }

        segments.forEach(segment => {
            const option = document.createElement('option');
            option.value = segment.id;
            option.text = `${segment.id} - ${segment.text.substring(0, 50)}...`;
            segmentsSelect.appendChild(option);
        });

        // También cargar segmentos asignados
        await loadAssignedSegments();

    } catch (error) {
        console.error('Error cargando segmentos:', error);
        showMessage('Error al cargar segmentos', 'error', 'assignments');
    }
}

async function assignSegments() {
    try {
        const projectId = document.getElementById('projectSelect').value;
        const annotatorId = document.getElementById('annotatorSelect').value;
        const segmentsSelect = document.getElementById('segmentsSelect');
        const segmentIds = Array.from(segmentsSelect.selectedOptions).map(o => parseInt(o.value));

        if (!projectId || !annotatorId || segmentIds.length === 0) {
            showMessage('Selecciona proyecto, anotador y segmentos', 'info', 'assignments');
            return;
        }

        await adminService.assignMultipleSegments(projectId, segmentIds, annotatorId);
        
        showMessage(`✅ ${segmentIds.length} segmento(s) asignado(s)`, 'success', 'assignments');
        await loadSegments();
        await loadAssignedSegments();

    } catch (error) {
        console.error('Error asignando segmentos:', error);
        showMessage(`Error: ${error.message}`, 'error', 'assignments');
    }
}

async function loadAssignedSegments() {
    const projectId = document.getElementById('projectSelect').value;
    const container = document.getElementById('assignedSegmentsContainer');
    if (!projectId || !container) {
        if (container) container.innerHTML = '';
        return;
    }

    try {
        const data = await adminService.getAssignedSegments(projectId);
        const assigned = data.assigned || [];

        if (assigned.length === 0) {
            container.innerHTML = '<p style="color:#999;padding:10px;">No hay segmentos asignados aún.</p>';
            return;
        }

        let html = '';
        for (const group of assigned) {
            const pending = group.segments.filter(s => s.status === 'pending');
            const completed = group.segments.filter(s => s.status !== 'pending');
            
            html += `
                <div style="background:#f7fafc;padding:15px;border-radius:8px;margin-bottom:15px;border-left:4px solid #667eea;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                        <strong>👤 ${group.username}</strong>
                        <span class="badge">${completed.length}/${group.segments.length} completados</span>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width:${group.segments.length > 0 ? (completed.length / group.segments.length * 100) : 0}%"></div>
                        </div>
                    </div>
                    <select id="assignedSelect_${group.user_id}" multiple style="width:100%;height:100px;font-size:12px;margin-bottom:8px;">
                        ${group.segments.map(s => 
                            `<option value="${s.id}" ${s.status !== 'pending' ? 'style="color:#48bb78;"' : ''}>${s.id} - ${s.text.substring(0, 40)}... [${s.status}]</option>`
                        ).join('')}
                    </select>
                    <button class="btn btn-danger" onclick="unassignSelected('${projectId}', ${group.user_id})" style="font-size:11px;">
                        🔄 Desasignar seleccionados
                    </button>
                </div>
            `;
        }
        container.innerHTML = html;

    } catch (error) {
        console.error('Error cargando segmentos asignados:', error);
        container.innerHTML = '<p style="color:#e53e3e;">Error al cargar asignaciones</p>';
    }
}

async function unassignSelected(projectId, userId) {
    const select = document.getElementById(`assignedSelect_${userId}`);
    if (!select) return;

    const segmentIds = Array.from(select.selectedOptions).map(o => parseInt(o.value));
    if (segmentIds.length === 0) {
        showMessage('Selecciona segmentos para desasignar', 'info', 'assignments');
        return;
    }

    if (!confirm(`¿Desasignar ${segmentIds.length} segmento(s)? Volverán al listado general.`)) return;

    try {
        await adminService.unassignMultipleSegments(projectId, segmentIds);
        showMessage(`✅ ${segmentIds.length} segmento(s) desasignado(s)`, 'success', 'assignments');
        await loadSegments();
        await loadAssignedSegments();
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error', 'assignments');
    }
}

// ==================== TAB: CONTROL DE CALIDAD ====================

async function loadQualityTab() {
    try {
        const projectsData = await adminService.getProjects();
        const projects = projectsData.projects || [];

        const qualityProjectSelect = document.getElementById('qualityProjectSelect');
        qualityProjectSelect.innerHTML = '<option value="">Selecciona un proyecto</option>';
        
        projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.id;
            option.textContent = project.name;
            qualityProjectSelect.appendChild(option);
        });

    } catch (error) {
        console.error('Error cargando quality tab:', error);
    }
}

async function loadQualityData() {
    try {
        const projectId = document.getElementById('qualityProjectSelect').value;
        if (!projectId) {
            showMessage('Selecciona un proyecto', 'info', 'quality');
            return;
        }

        showMessage('Cargando comparativas...', 'info', 'quality');
        
        // Por ahora mostrar mensaje de soporte
        const resultsDiv = document.getElementById('qualityResults');
        resultsDiv.innerHTML = `
            <div style="padding: 20px; background: #f7fafc; border-radius: 8px; border-left: 4px solid #667eea;">
                <p>✓ Sistema de control de calidad está en desarrollo.</p>
                <p style="margin-top: 10px; color: #666; font-size: 14px;">
                    Próximamente podrás comparar anotaciones del admin con las de los anotadores
                    y consolidar discrepancias.
                </p>
            </div>
        `;

    } catch (error) {
        console.error('Error cargando quality data:', error);
        showMessage(`Error: ${error.message}`, 'error', 'quality');
    }
}

// ==================== MODALES ====================

function openCreateUserModal() {
    document.getElementById('createUserModal').classList.add('active');
}

function closeCreateUserModal() {
    document.getElementById('createUserModal').classList.remove('active');
    document.getElementById('newUsername').value = '';
    document.getElementById('newPassword').value = '';
    document.getElementById('newRole').value = 'annotator';
}

async function createUser() {
    try {
        const username = document.getElementById('newUsername').value.trim();
        const password = document.getElementById('newPassword').value;
        const role = document.getElementById('newRole').value;

        if (!username || !password) {
            showMessage('Usuario y contraseña son requeridos', 'error', 'users');
            return;
        }

        if (password.length < 6) {
            showMessage('La contraseña debe tener al menos 6 caracteres', 'error', 'users');
            return;
        }

        await adminService.createUser(username, password, role);
        
        showMessage(`✅ Usuario "${username}" creado exitosamente`, 'success', 'users');
        closeCreateUserModal();
        await loadUsersTab();

    } catch (error) {
        console.error('Error creando usuario:', error);
        showMessage(`Error: ${error.message}`, 'error', 'users');
    }
}

function deleteUserConfirm(userId, username) {
    if (confirm(`¿Eliminar usuario "${username}"? Esta acción no se puede deshacer.`)) {
        deleteUser(userId, username);
    }
}

async function deleteUser(userId, username) {
    try {
        await adminService.deleteUser(userId);
        showMessage(`✅ Usuario "${username}" eliminado`, 'success', 'users');
        await loadUsersTab();

    } catch (error) {
        console.error('Error eliminando usuario:', error);
        showMessage(`Error: ${error.message}`, 'error', 'users');
    }
}

// ==================== DETALLE DE ANOTACIONES ====================

let currentAnnotationsUserId = null;
let currentAnnotations = [];
let editingSegmentId = null;

async function viewUserDetail(userId) {
    try {
        const data = await adminService.getUserAnnotations(userId);
        currentAnnotationsUserId = userId;
        currentAnnotations = data.annotations || [];

        document.getElementById('annotationsModalTitle').textContent =
            `Anotaciones de ${data.username} (${data.total})`;
        document.getElementById('annotationsCount').textContent =
            `${data.total} anotación(es)`;

        renderAnnotationsList();

        document.getElementById('selectAllAnnotations').checked = false;
        updateBulkUI();
        document.getElementById('annotationsModal').style.display = 'block';

    } catch (error) {
        console.error('Error cargando anotaciones:', error);
        showMessage(`Error: ${error.message}`, 'error', 'overview');
    }
}

function renderAnnotationsList() {
    const container = document.getElementById('annotationsList');

    if (currentAnnotations.length === 0) {
        container.innerHTML = '<p style="text-align:center; color:#999; padding:40px;">Este usuario no tiene anotaciones completadas.</p>';
        return;
    }

    container.innerHTML = currentAnnotations.map(ann => {
        const displayText = ann.text_revised || ann.text;
        const wasEdited = ann.review_status === 'corrected' && ann.text_revised;
        const date = ann.completed_at
            ? new Date(ann.completed_at).toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
            : '—';

        return `
        <div class="annotation-item" data-segment-id="${ann.id}">
            <div class="annotation-item__header">
                <input type="checkbox" class="annotation-check" value="${ann.id}" onchange="updateBulkUI()">
                <span class="status-tag ${ann.review_status}">${ann.review_status === 'approved' ? '✓ Aprobada' : '✎ Corregida'}</span>
                <span class="annotation-item__meta">Segmento #${ann.segment_index} · ${date}</span>
            </div>
            <div class="annotation-item__text">${escapeHtml(displayText)}</div>
            ${wasEdited ? `<div class="annotation-item__original">Original: ${escapeHtml(ann.text)}</div>` : ''}
            <div class="annotation-item__actions">
                <button class="btn-edit" onclick="openEditAnnotation(${ann.id})">✏️ Editar</button>
                <button class="btn-delete" onclick="revertSingleAnnotation(${ann.id})">🗑️ Eliminar</button>
            </div>
        </div>`;
    }).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function closeAnnotationsModal() {
    document.getElementById('annotationsModal').style.display = 'none';
}

async function downloadAnnotationsExcel() {
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/v1/admin/annotations/export', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Error al descargar');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = response.headers.get('Content-Disposition')?.match(/filename="?(.+?)"?$/)?.[1] || 'anotaciones.xlsx';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error', 'overview');
    }
}

function toggleSelectAll(checkbox) {
    document.querySelectorAll('.annotation-check').forEach(cb => {
        cb.checked = checkbox.checked;
        cb.closest('.annotation-item').classList.toggle('selected', checkbox.checked);
    });
    updateBulkUI();
}

function updateBulkUI() {
    const checked = document.querySelectorAll('.annotation-check:checked');
    const btn = document.getElementById('bulkRevertBtn');
    const count = document.getElementById('selectedCount');

    if (checked.length > 0) {
        btn.style.display = 'inline-block';
        count.textContent = `${checked.length} seleccionada(s)`;
    } else {
        btn.style.display = 'none';
        count.textContent = '';
    }

    // Toggle visual selection
    document.querySelectorAll('.annotation-check').forEach(cb => {
        cb.closest('.annotation-item').classList.toggle('selected', cb.checked);
    });
}

async function revertSingleAnnotation(segmentId) {
    if (!confirm('¿Eliminar esta anotación? El segmento volverá a estado pendiente.')) return;

    try {
        await adminService.revertAnnotation(segmentId);
        showMessage('Anotación eliminada', 'success', 'overview');
        // Refresh the list
        await viewUserDetail(currentAnnotationsUserId);
        await loadOverviewTab();
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error', 'overview');
    }
}

async function bulkRevertSelected() {
    const checked = document.querySelectorAll('.annotation-check:checked');
    const ids = Array.from(checked).map(cb => parseInt(cb.value));

    if (ids.length === 0) return;
    if (!confirm(`¿Eliminar ${ids.length} anotación(es)? Volverán a estado pendiente.`)) return;

    try {
        await adminService.bulkRevertAnnotations(ids);
        showMessage(`${ids.length} anotación(es) eliminadas`, 'success', 'overview');
        await viewUserDetail(currentAnnotationsUserId);
        await loadOverviewTab();
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error', 'overview');
    }
}

function openEditAnnotation(segmentId) {
    const ann = currentAnnotations.find(a => a.id === segmentId);
    if (!ann) return;

    editingSegmentId = segmentId;
    document.getElementById('editOriginalText').textContent = ann.text;
    document.getElementById('editTextRevised').value = ann.text_revised || ann.text;
    document.getElementById('editReviewStatus').value = ann.review_status;
    document.getElementById('editAnnotationModal').style.display = 'block';
}

function closeEditModal() {
    document.getElementById('editAnnotationModal').style.display = 'none';
    editingSegmentId = null;
}

async function saveAnnotationEdit() {
    if (!editingSegmentId) return;

    const textRevised = document.getElementById('editTextRevised').value.trim();
    const reviewStatus = document.getElementById('editReviewStatus').value;

    if (!textRevised) {
        alert('El texto revisado no puede estar vacío');
        return;
    }

    try {
        await adminService.editAnnotation(editingSegmentId, textRevised, reviewStatus);
        showMessage('Anotación actualizada', 'success', 'overview');
        closeEditModal();
        await viewUserDetail(currentAnnotationsUserId);
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error', 'overview');
    }
}

// ==================== UTILIDADES ====================

function showMessage(text, type = 'info', tabName = 'overview') {
    const messageAreaId = {
        'overview': 'messageArea',
        'users': 'messageArea2',
        'assignments': 'messageArea3',
        'quality': 'messageArea4'
    }[tabName] || 'messageArea';

    const messageArea = document.getElementById(messageAreaId);
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = text;
    messageArea.innerHTML = '';
    messageArea.appendChild(messageDiv);

    setTimeout(() => {
        messageDiv.remove();
    }, 5000);
}

function logout() {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
}
