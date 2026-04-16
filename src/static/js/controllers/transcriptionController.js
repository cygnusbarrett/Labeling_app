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
            // Extraer información del usuario del token
            const token = transcriptionService.token;
            const tokenPayload = JSON.parse(atob(token.split('.')[1]));
            state.user = tokenPayload;
            state.userRole = tokenPayload.role;
            
            // Verificar que el token sigue siendo válido
            const projects = await transcriptionService.getProjects();
            showValidatorSection();
            await loadUserData();
        } catch (error) {
            console.error('Error en initApp:', error);
            // Token inválido, redirigir a login
            transcriptionService.logout();
            window.location.href = '/login';
        }
    } else {
        // No hay token, redirigir a página de login dedicada
        window.location.href = '/login';
    }
}

/**
 * Muestra la sección de validador
 */
function showValidatorSection() {
    document.getElementById('validatorSection').classList.add('active');
}


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
        const completionMsg = document.getElementById('completionMessage');
        if (completionMsg) completionMsg.style.display = 'none';

        const wordsData = await transcriptionService.getWords(state.currentProject, 'pending', 100);
        state.allWords = wordsData.words || [];

        if (state.allWords.length === 0) {
            document.getElementById('loadingState').style.display = 'none';
            
            // Mostrar mensaje de felicitaciones con opción de solicitar más
            const msgContainer = document.getElementById('completionMessage');
            if (msgContainer) {
                msgContainer.style.display = 'block';
                msgContainer.innerHTML = `
                    <div style="text-align:center;padding:40px 20px;">
                        <div style="font-size:64px;margin-bottom:20px;">🎉</div>
                        <h2 style="color:#48bb78;margin-bottom:10px;">¡Felicitaciones!</h2>
                        <p style="color:#666;margin-bottom:20px;">Has completado todos los segmentos asignados.</p>
                        <p style="color:#999;font-size:14px;">Contacta al administrador para que te asigne más segmentos.</p>
                    </div>
                `;
            } else {
                showMessage('🎉 ¡Felicitaciones! Has completado todos los segmentos asignados. Contacta al administrador para recibir más.', 'success');
            }
            
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
            showMessage('No hay más segmentos', 'info');
            return;
        }

        state.currentWordIndex = index;
        const segment = state.allWords[index];  // Ahora es un segmento, no una palabra
        state.currentWord = segment;

        // Actualizar interfaz con los datos del SEGMENTO
        document.getElementById('wordSpeaker').textContent = segment.speaker || 'UNKNOWN';
        
        // IMPORTANTE: Mostrar el TEXTO COMPLETO del segmento (no una palabra)
        document.getElementById('originalText').textContent = segment.text;
        document.getElementById('correctedText').value = segment.text_revised || '';

        // Mostrar el texto con palabras de baja probabilidad destacadas en rojo
        displayHighlightedText(segment);
        
        // Pre-llenar la casilla de corrección con el texto original
        document.getElementById('correctedText').value = segment.text;

        // Duración (sin tiempos de inicio/fin)
        const duration = (segment.end_time - segment.start_time).toFixed(2);
        document.getElementById('wordDuration').textContent = `${duration}s`;
        
        // Mostrar información de palabras con baja probabilidad en metadata
        const lowProbText = document.getElementById('lowProbText');
        if (segment.low_prob_word_count > 0) {
            lowProbText.textContent = `⚠️ ${segment.low_prob_word_count} palabra(s) con baja confianza`;
            lowProbText.style.color = '#d68910';
        } else {
            lowProbText.textContent = '✓ Segmento completo';
            lowProbText.style.color = '#22863a';
        }

        // Badge de palabras de baja probabilidad (oculto)
        const badge = document.getElementById('probabilityBadge');
        badge.innerHTML = '';

        // Mostrar las palabras de baja probabilidad dentro del segmento
        displayLowProbabilityWords(segment);

        // Cargar audio del SEGMENTO
        try {
            console.log('🎵 Cargando audio para SEGMENTO ID:', segment.id);
            console.log('📂 Proyecto:', state.currentProject);
            console.log('⏱️ Duración del segmento:', segment.start_time, '-', segment.end_time);
            
            const audioUrl = await transcriptionService.getWordAudio(state.currentProject, segment.id, 0.2);
            
            const audioPlayer = document.getElementById('audioPlayer');
            console.log('🔧 Seteando src del audioPlayer a:', audioUrl);
            
            audioPlayer.src = audioUrl;
            console.log('📍 src seteado, llamando .load()');
            
            audioPlayer.load();
            console.log('✅ Audio del segmento cargado y listo para reproducir');
            
        } catch (audioError) {
            console.error('❌ Error al cargar audio:', audioError);
            showMessage(`Advertencia: No se pudo cargar el audio - ${audioError.message}`, 'error');
        }

        // Actualizar título del navegador
        document.title = `Segmento ${index + 1}/${state.allWords.length} - Validador`;

        document.getElementById('wordCard').style.display = 'block';
        document.getElementById('loadingState').style.display = 'none';

        // Scroll al card
        document.getElementById('wordCard').scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (error) {
        showMessage(`Error mostrando segmento: ${error.message}`, 'error');
    }
}

/**
 * Muestra las palabras con baja probabilidad dentro de un segmento
 */
function displayLowProbabilityWords(segment) {
    let container = document.getElementById('lowProbabilityWords');
    
    if (!container) {
        // Crear el contenedor si no existe
        const correctionSection = document.getElementById('correctionSection');
        if (correctionSection) {
            const newContainer = document.createElement('div');
            newContainer.id = 'lowProbabilityWords';
            newContainer.style.marginBottom = '1.5rem';
            newContainer.style.padding = '1rem';
            newContainer.style.backgroundColor = '#fff3cd';
            newContainer.style.borderRadius = '0.5rem';
            newContainer.style.borderLeft = '4px solid #ffc107';
            correctionSection.parentNode.insertBefore(newContainer, correctionSection);
            container = newContainer;
        }
    }

    if (!segment.words || segment.words.length === 0) {
        if (container) container.innerHTML = '';
        return;
    }

    // Filtrar palabras con probabilidad < 0.95
    const lowProbWords = segment.words.filter(w => w.probability < 0.95);
    
    if (lowProbWords.length === 0) {
        if (container) container.innerHTML = '';
        return;
    }

    let html = '<strong>📌 Palabras con baja confianza (< 95%):</strong><ul style="margin-top: 0.5rem; padding-left: 1.5rem;">';
    lowProbWords.forEach(word => {
        const probPercent = (word.probability * 100).toFixed(0);
        html += `<li><strong>"${word.word}"</strong> - ${probPercent}% confianza</li>`;
    });
    html += '</ul>';
    
    if (container) container.innerHTML = html;
}

/**
 * Muestra el texto con palabras de baja confianza destacadas en rojo
 */
function displayHighlightedText(segment) {
    const highlightedDiv = document.getElementById('highlightedText');
    
    if (!highlightedDiv) {
        console.error('No se encontró el elemento highlightedText');
        return;
    }

    if (!segment.words || segment.words.length === 0) {
        highlightedDiv.textContent = segment.text;
        return;
    }

    // Crear un mapa de palabras con baja probabilidad (< 0.95)
    const lowProbWords = segment.words.filter(w => w.probability < 0.95);
    const lowProbWordsSet = new Set(lowProbWords.map(w => w.word.toLowerCase()));

    // Dividir el texto en palabras y reconstruirlo con highlighting
    const words = segment.text.split(/(\s+)/); // Mantener espacios
    let highlightedHtml = '';

    words.forEach(word => {
        if (/^\s+$/.test(word)) {
            // Es espacio en blanco, mantenerlo así
            highlightedHtml += word;
        } else {
            // Verificar si la palabra tiene baja probabilidad
            // Comparar sin puntuación para mejor matching
            const cleanWord = word.toLowerCase().replace(/[.,!?;:—-]+$/g, '').replace(/^[¿¡—-]+/, '');
            const punctuation = word.match(/[.,!?;:—-]+$/g)?.[0] || '';
            const prefix = word.match(/^[¿¡—-]+/)?.[0] || '';
            
            if (lowProbWordsSet.has(cleanWord)) {
                highlightedHtml += `${prefix}<span style="color: red; font-weight: bold;">${cleanWord}</span>${punctuation}`;
            } else {
                highlightedHtml += word;
            }
        }
    });

    highlightedDiv.innerHTML = highlightedHtml;
}

/**
 * Envía la validación de una palabra
 */
async function submitWord(status) {
    try {
        if (!state.currentWord) {
            showMessage('Error: No hay segmento seleccionado', 'error');
            return;
        }

        const textRevised = document.getElementById('correctedText').value.trim();

        // El status es equivalente a review_status (pending/approved/corrected)
        const review_status = status === 'approved' ? 'approved' : 'corrected';

        // Validar que si es "corrected", hay texto
        if (review_status === 'corrected' && !textRevised) {
            showMessage('Por favor, ingresa la corrección antes de guardar', 'info');
            return;
        }

        // Deshabilitar botones mientras se procesa
        const buttons = document.querySelectorAll('.form-actions button');
        buttons.forEach(btn => btn.disabled = true);

        console.log('📤 Enviando segmento:', {
            segment_id: state.currentWord.id,
            review_status: review_status,
            text_revised: textRevised || null
        });

        // Enviar corrección (usando submitWord que envía al endpoint /words/<id>)
        await transcriptionService.submitWord(
            state.currentWord.id,
            review_status,
            textRevised || null
        );

        // Mostrar mensaje de éxito
        const statusText = review_status === 'approved' ? 'aprobada ✓' : 'corregida ✎';
        showMessage(`Segmento ${statusText}`, 'success');

        // Actualizar estadísticas
        await updateStats();

        // Ir al siguiente segmento
        setTimeout(() => {
            if (state.currentWordIndex + 1 < state.allWords.length) {
                displayWord(state.currentWordIndex + 1);
            } else {
                showMessage('¡Has completado todos los segmentos! 🎉', 'success');
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
            // Vista admin: mostrar totales del PROYECTO (en SEGMENTOS)
            const stats = statsData;
            const total = stats.total_segments || stats.total_words || 0;
            const completed = (stats.approved_segments || 0) + (stats.corrected_segments || 0) || stats.words_completed || 0;
            const progress = total > 0 ? (completed / total * 100) : 0;

            document.getElementById('totalWords').textContent = total;
            document.getElementById('completedWords').textContent = completed;
            document.getElementById('pendingWords').textContent = total - completed;
            document.getElementById('progressPercent').textContent = progress.toFixed(0) + '%';
            document.getElementById('progressFill').style.width = progress + '%';
            document.getElementById('progressText').textContent = `${completed} de ${total} segmentos completados`;

        } else {
            // Vista anotador: mostrar sus estadísticas personales (SEGMENTOS)
            const stats = statsData;
            const total = stats.my_total || stats.total_segments || 0;
            const completed = stats.my_completed || 0;
            const progress = total > 0 ? (completed / total * 100) : 0;

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
