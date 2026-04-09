/**
 * Controlador de Validación de Transcripciones
 */

// Estado global
let state = {
    user: null,
    currentProject: null,
    currentWord: null,
    currentWordIndex: 0,
    allWords: [],
    stats: null,
    userRole: 'annotator'
};

/**
 * Inicializa la aplicación
 */
async function initApp() {
    // Si hay token, mostrar validador
    if (transcriptionService.isAuthenticated()) {
        try {
            // Verificar que el token sigue siendo válido
            const projects = await transcriptionService.getProjects();
            showValidatorSection();
            await loadUserData();
        } catch (error) {
            // Token inválido, mostrar login
            showLoginSection();
            transcriptionService.logout();
        }
    } else {
        showLoginSection();
    }
}

/**
 * Muestra la sección de login
 */
function showLoginSection() {
    document.getElementById('loginSection').classList.add('active');
    document.getElementById('validatorSection').classList.remove('active');
}

/**
 * Muestra la sección de validador
 */
function showValidatorSection() {
    document.getElementById('loginSection').classList.remove('active');
    document.getElementById('validatorSection').classList.add('active');
}

/**
 * Maneja el login
 */
document.getElementById('loginForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('loginError');

    errorDiv.textContent = '';

    try {
        // Hacer login a través de la API existente
        const response = await fetch('/api/v2/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            throw new Error('Credenciales inválidas');
        }

        const data = await response.json();
        
        // Guardar token
        transcriptionService.setToken(data.access_token);
        
        // Extraer información del usuario del token
        const tokenPayload = JSON.parse(atob(data.access_token.split('.')[1]));
        state.user = tokenPayload;
        state.userRole = tokenPayload.role;

        // Mostrar validador
        showValidatorSection();
        await loadUserData();

    } catch (error) {
        errorDiv.textContent = error.message || 'Error en el login';
    }
});

/**
 * Carga los datos del usuario y proyectos
 */
async function loadUserData() {
    try {
        // Actualizar información del usuario
        document.getElementById('currentUser').textContent = state.user.username;

        // Mostrar selector de proyecto si es admin
        if (state.userRole === 'admin') {
            document.getElementById('projectSelector').style.display = 'block';
        }

        // Cargar proyectos
        const projectsData = await transcriptionService.getProjects();
        const projects = projectsData.projects || [];

        // Llenar selector de proyectos
        const projectSelect = document.getElementById('projectSelect');
        projectSelect.innerHTML = '';

        projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.id;
            option.textContent = `${project.name} (${project.words_to_review} pendientes)`;
            projectSelect.appendChild(option);
        });

        // Si hay un proyecto, seleccionar el primero
        if (projects.length > 0) {
            state.currentProject = projects[0].id;
            document.getElementById('currentProject').textContent = projects[0].name;
            projectSelect.value = projects[0].id;
            await loadProjectWords();
        } else {
            showMessage('No hay proyectos disponibles', 'info');
        }

    } catch (error) {
        showMessage(`Error cargando datos: ${error.message}`, 'error');
    }
}

/**
 * Selecciona un proyecto
 */
async function selectProject(projectId) {
    if (!projectId) return;

    try {
        state.currentProject = projectId;
        const projectData = await transcriptionService.getProject(projectId);
        document.getElementById('currentProject').textContent = projectData.project.name;

        state.currentWordIndex = 0;
        await loadProjectWords();

    } catch (error) {
        showMessage(`Error cargando proyecto: ${error.message}`, 'error');
    }
}

/**
 * Carga las palabras del proyecto
 */
async function loadProjectWords() {
    try {
        document.getElementById('loadingState').style.display = 'block';
        document.getElementById('wordCard').style.display = 'none';
        document.getElementById('statsPanel').style.display = 'none';

        const wordsData = await transcriptionService.getWords(state.currentProject, 'pending', 100);
        state.allWords = wordsData.words || [];

        if (state.allWords.length === 0) {
            document.getElementById('loadingState').style.display = 'none';
            showMessage('¡Todas las palabras han sido validadas! 🎉', 'success');
            await updateStats();
            return;
        }

        state.currentWordIndex = 0;
        document.getElementById('loadingState').style.display = 'none';

        await displayWord(0);
        await updateStats();

    } catch (error) {
        document.getElementById('loadingState').style.display = 'none';
        showMessage(`Error cargando palabras: ${error.message}`, 'error');
    }
}

/**
 * Muestra una palabra específica
 */
async function displayWord(index) {
    try {
        if (index < 0 || index >= state.allWords.length) {
            showMessage('No hay más palabras', 'info');
            return;
        }

        state.currentWordIndex = index;
        const word = state.allWords[index];
        state.currentWord = word;

        // Actualizar interfaz con los datos de la palabra
        document.getElementById('wordText').textContent = word.word;
        document.getElementById('wordSpeaker').textContent = word.speaker;
        document.getElementById('wordProbability').textContent = (word.probability * 100).toFixed(1) + '%';
        document.getElementById('originalText').textContent = word.word;
        document.getElementById('correctedText').value = '';

        // Badge de probabilidad
        const badge = document.getElementById('probabilityBadge');
        badge.innerHTML = `<span class="probability-badge">${(word.probability * 100).toFixed(0)}% confianza</span>`;

        // Duración
        const duration = (word.end_time - word.start_time).toFixed(2);
        document.getElementById('wordDuration').textContent = `${duration}s (${word.start_time.toFixed(2)}s - ${word.end_time.toFixed(2)}s)`;

        // Cargar audio
        try {
            console.log('🎵 Cargando audio para palabra ID:', word.id);
            console.log('📂 Proyecto:', state.currentProject);
            console.log('🎚️ Margen:', 0.2, 'segundos');
            
            const audioUrl = await transcriptionService.getWordAudio(state.currentProject, word.id, 0.2);
            
            const audioPlayer = document.getElementById('audioPlayer');
            console.log('🔧 Seteando src del audioPlayer a:', audioUrl);
            
            audioPlayer.src = audioUrl;
            console.log('📍 src seteado, llamando .load()');
            
            audioPlayer.load();
            console.log('✅ Audio cargado y listo para reproducir');
            
        } catch (audioError) {
            console.error('❌ Error al cargar audio:', audioError);
            showMessage(`Advertencia: No se pudo cargar el audio - ${audioError.message}`, 'error');
        }

        // Actualizar título del navegador
        document.title = `Palabra ${index + 1}/${state.allWords.length} - Validador`;

        document.getElementById('wordCard').style.display = 'block';
        document.getElementById('loadingState').style.display = 'none';

        // Scroll al card
        document.getElementById('wordCard').scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (error) {
        showMessage(`Error mostrando palabra: ${error.message}`, 'error');
    }
}

/**
 * Envía la validación de una palabra
 */
async function submitWord(status) {
    try {
        if (!state.currentWord) {
            showMessage('Error: No hay palabra seleccionada', 'error');
            return;
        }

        const correctedText = document.getElementById('correctedText').value.trim();

        // Validar que si es "corrected", hay texto
        if (status === 'corrected' && !correctedText) {
            showMessage('Por favor, ingresa la corrección antes de guardar', 'info');
            return;
        }

        // Deshabilitar botones mientras se procesa
        const buttons = document.querySelectorAll('.form-actions button');
        buttons.forEach(btn => btn.disabled = true);

        // Enviar corrección
        await transcriptionService.submitWord(
            state.currentWord.id,
            status,
            correctedText || null
        );

        // Mostrar mensaje de éxito
        const statusText = status === 'approved' ? 'aprobada ✓' : 'corregida ✎';
        showMessage(`Palabra ${statusText}`, 'success');

        // Actualizar estadísticas
        await updateStats();

        // Ir a la siguiente palabra
        setTimeout(() => {
            if (state.currentWordIndex + 1 < state.allWords.length) {
                displayWord(state.currentWordIndex + 1);
            } else {
                showMessage('¡Has completado todas las palabras! 🎉', 'success');
                document.getElementById('wordCard').style.display = 'none';
            }

            buttons.forEach(btn => btn.disabled = false);
        }, 500);

    } catch (error) {
        showMessage(`Error enviando corrección: ${error.message}`, 'error');
        document.querySelectorAll('.form-actions button').forEach(btn => btn.disabled = false);
    }
}

/**
 * Actualiza las estadísticas del proyecto
 */
async function updateStats() {
    try {
        const statsData = await transcriptionService.getStats(state.currentProject);

        if (state.userRole === 'admin') {
            // Vista admin: mostrar totales del proyecto
            const stats = statsData;
            const total = stats.total_words;
            const completed = stats.words_completed;
            const progress = (completed / total * 100) || 0;

            document.getElementById('totalWords').textContent = total;
            document.getElementById('completedWords').textContent = completed;
            document.getElementById('pendingWords').textContent = total - completed;
            document.getElementById('progressPercent').textContent = progress.toFixed(0) + '%';
            document.getElementById('progressFill').style.width = progress + '%';
            document.getElementById('progressText').textContent = `${completed} de ${total} palabras completadas`;

        } else {
            // Vista anotador: mostrar sus estadísticas personales
            const stats = statsData;
            const total = stats.my_total;
            const completed = stats.my_completed;
            const progress = (completed / total * 100) || 0;

            document.getElementById('totalWords').textContent = total;
            document.getElementById('completedWords').textContent = completed;
            document.getElementById('pendingWords').textContent = total - completed;
            document.getElementById('progressPercent').textContent = progress.toFixed(0) + '%';
            document.getElementById('progressFill').style.width = progress + '%';
            document.getElementById('progressText').textContent = `${completed} de ${total} palabras completadas`;
        }

        document.getElementById('statsPanel').style.display = 'grid';

    } catch (error) {
        console.error('Error actualizando estadísticas:', error);
    }
}

/**
 * Muestra un mensaje
 */
function showMessage(text, type = 'info') {
    const messageArea = document.getElementById('messageArea');
    const message = document.createElement('div');
    message.className = `message ${type}`;
    message.textContent = text;

    messageArea.innerHTML = '';
    messageArea.appendChild(message);

    // Auto-remover mensaje después de 5 segundos si es success o info
    if (type !== 'error') {
        setTimeout(() => {
            message.remove();
        }, 5000);
    }
}

/**
 * Controles de audio
 */
function playAudio() {
    const audio = document.getElementById('audioPlayer');
    console.log('▶️  Presionado: Reproducir');
    console.log('   - Src:', audio.src);
    console.log('   - Duración:', audio.duration);
    console.log('   - Paused:', audio.paused);
    console.log('   - Readystate:', audio.readyState, '(0=HAVE_NOTHING, 1=HAVE_METADATA, 2=HAVE_CURRENT_DATA, 3=HAVE_FUTURE_DATA, 4=HAVE_ENOUGH_DATA)');
    
    if (!audio.src) {
        console.error('❌ No hay audio cargado!');
        showMessage('Error: Audio no cargado', 'error');
        return;
    }
    
    audio.play().then(() => {
        console.log('✅ Audio reproduciendo');
    }).catch(error => {
        console.error('❌ Error al reproducir:', error);
        showMessage(`Error al reproducir: ${error.message}`, 'error');
    });
}

function pauseAudio() {
    const audio = document.getElementById('audioPlayer');
    console.log('⏸️  Presionado: Pausar');
    audio.pause();
}

function replayAudio() {
    const audio = document.getElementById('audioPlayer');
    console.log('🔄 Presionado: Repetir');
    audio.currentTime = 0;
    audio.play().then(() => {
        console.log('✅ Audio reiciado');
    }).catch(error => {
        console.error('❌ Error al reiciar:', error);
    });
}

/**
 * Logout
 */
function logout() {
    transcriptionService.logout();
    state = {
        user: null,
        currentProject: null,
        currentWord: null,
        currentWordIndex: 0,
        allWords: [],
        stats: null,
        userRole: 'annotator'
    };
    document.getElementById('messageArea').innerHTML = '';
    showLoginSection();
    document.getElementById('loginForm').reset();
}
