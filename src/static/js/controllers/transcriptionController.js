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
    userRole: 'annotator',
    fullEditMode: false
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
        const segment = state.allWords[index];
        state.currentWord = segment;

        // Reset full-edit mode for each new segment
        state.fullEditMode = false;
        const fullEditSection = document.getElementById('fullEditSection');
        if (fullEditSection) fullEditSection.classList.remove('active');
        const toggleLink = document.querySelector('.full-edit-toggle');
        if (toggleLink) toggleLink.style.display = '';

        // Actualizar interfaz con los datos del SEGMENTO
        document.getElementById('wordSpeaker').textContent = segment.speaker || 'UNKNOWN';
        document.getElementById('originalText').textContent = segment.text;

        // Renderizar texto con edición inline de palabras inciertas
        displayHighlightedText(segment);

        // Pre-llenar textarea oculto (para modo edición completa)
        document.getElementById('correctedText').value = segment.text;

        // Duración
        const duration = (segment.end_time - segment.start_time).toFixed(2);
        document.getElementById('wordDuration').textContent = `${duration}s`;
        
        // Info de palabras con baja probabilidad
        const lowProbText = document.getElementById('lowProbText');
        if (segment.low_prob_word_count > 0) {
            lowProbText.textContent = `⚠️ ${segment.low_prob_word_count} palabra(s) con baja confianza`;
            lowProbText.style.color = '#d68910';
        } else {
            lowProbText.textContent = '✓ Segmento completo';
            lowProbText.style.color = '#22863a';
        }

        // Badge (oculto)
        document.getElementById('probabilityBadge').innerHTML = '';

        // Indicador de cambios
        updateChangeIndicator();

        // Cargar audio del SEGMENTO
        try {
            const audioUrl = await transcriptionService.getWordAudio(state.currentProject, segment.id, 0.2);
            const audioPlayer = document.getElementById('audioPlayer');
            audioPlayer.src = audioUrl;
            audioPlayer.load();
        } catch (audioError) {
            console.error('Error al cargar audio:', audioError);
            showMessage(`Advertencia: No se pudo cargar el audio - ${audioError.message}`, 'error');
        }

        // Actualizar título
        document.title = `Segmento ${index + 1}/${state.allWords.length} - Validador`;

        document.getElementById('wordCard').style.display = 'block';
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('wordCard').scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (error) {
        showMessage(`Error mostrando segmento: ${error.message}`, 'error');
    }
}

/**
 * Muestra el texto con palabras editables inline para baja confianza
 */
function displayHighlightedText(segment) {
    const container = document.getElementById('highlightedText');
    if (!container) return;

    container.innerHTML = '';

    if (!segment.words || segment.words.length === 0) {
        // Sin datos de palabras: mostrar texto plano
        container.textContent = segment.text;
        return;
    }

    // Ordenar palabras por índice
    const sortedWords = [...segment.words].sort((a, b) => a.word_index - b.word_index);

    sortedWords.forEach((wordObj, i) => {
        // Espacio entre palabras (excepto la primera)
        if (i > 0) {
            container.appendChild(document.createTextNode(' '));
        }

        if (wordObj.probability < 0.95) {
            // Palabra incierta → input editable inline
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'inline-word-input';
            input.value = wordObj.word;
            input.dataset.wordIndex = wordObj.word_index;
            input.dataset.originalWord = wordObj.word;
            input.title = `Confianza: ${(wordObj.probability * 100).toFixed(0)}% — edita si es incorrecto`;

            // Ancho dinámico basado en contenido
            input.style.width = (Math.max(wordObj.word.length, 2) + 2) + 'ch';

            input.addEventListener('input', function() {
                this.style.width = (Math.max(this.value.length, 2) + 2) + 'ch';
                // Marcar visualmente si fue modificado
                if (this.value !== this.dataset.originalWord) {
                    this.classList.add('modified');
                } else {
                    this.classList.remove('modified');
                }
                updateChangeIndicator();
            });

            // Navegación con Tab entre inputs
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    // Ir al siguiente input o confirmar
                    const allInputs = container.querySelectorAll('.inline-word-input');
                    const idx = Array.from(allInputs).indexOf(this);
                    if (idx < allInputs.length - 1) {
                        allInputs[idx + 1].focus();
                    } else {
                        // Último input: confirmar
                        submitWord('approved');
                    }
                }
            });

            container.appendChild(input);
        } else {
            // Palabra segura → texto estático
            const span = document.createElement('span');
            span.className = 'inline-word-static';
            span.textContent = wordObj.word;
            span.dataset.wordIndex = wordObj.word_index;
            container.appendChild(span);
        }
    });
}

/**
 * Reconstruye el texto completo desde los elementos inline
 */
function reconstructText() {
    const container = document.getElementById('highlightedText');
    const elements = container.querySelectorAll('.inline-word-input, .inline-word-static');
    const words = [];

    elements.forEach(el => {
        if (el.classList.contains('inline-word-input')) {
            const val = el.value.trim();
            if (val.length > 0) words.push(val);
        } else {
            words.push(el.textContent);
        }
    });

    return words.join(' ').trim();
}

/**
 * Verifica si hay cambios en las palabras editables
 */
function hasInlineChanges() {
    const inputs = document.querySelectorAll('#highlightedText .inline-word-input');
    for (const input of inputs) {
        if (input.value !== input.dataset.originalWord) return true;
    }
    return false;
}

/**
 * Actualiza el indicador visual de cambios
 */
function updateChangeIndicator() {
    const indicator = document.getElementById('changeIndicator');
    if (!indicator) return;

    const changed = hasInlineChanges();
    const inputs = document.querySelectorAll('#highlightedText .inline-word-input');
    const modifiedCount = Array.from(inputs).filter(i => i.value !== i.dataset.originalWord).length;

    if (inputs.length === 0) {
        indicator.className = 'change-indicator no-changes';
        indicator.textContent = '✅ Sin palabras inciertas — escucha el audio y confirma';
    } else if (changed) {
        indicator.className = 'change-indicator has-changes';
        indicator.textContent = `✏️ ${modifiedCount} palabra(s) modificada(s) — se enviará como corregida`;
    } else {
        indicator.className = 'change-indicator no-changes';
        indicator.textContent = `🔍 ${inputs.length} palabra(s) editable(s) — modifica o confirma como está`;
    }
}

/**
 * Alterna al modo de edición completa del texto
 */
function toggleFullEdit() {
    state.fullEditMode = true;
    const section = document.getElementById('fullEditSection');
    section.classList.add('active');
    
    // Pre-llenar con el texto reconstruido (por si ya se editó algo inline)
    const textarea = document.getElementById('correctedText');
    textarea.value = reconstructText();
    textarea.focus();

    // Ocultar toggle link
    document.querySelector('.full-edit-toggle').style.display = 'none';
}

/**
 * Envía la validación de un segmento
 */
async function submitWord(status) {
    try {
        if (!state.currentWord) {
            showMessage('Error: No hay segmento seleccionado', 'error');
            return;
        }

        // Determinar texto y estado
        let textRevised;
        let review_status;

        if (state.fullEditMode) {
            // Modo edición completa: usar textarea
            textRevised = document.getElementById('correctedText').value.trim();
            review_status = (textRevised !== state.currentWord.text.trim()) ? 'corrected' : 'approved';
        } else {
            // Modo inline: reconstruir desde los inputs
            textRevised = reconstructText();
            review_status = hasInlineChanges() ? 'corrected' : 'approved';
        }

        // Validar que hay texto
        if (!textRevised) {
            showMessage('Error: no se pudo reconstruir el texto', 'error');
            return;
        }

        // Deshabilitar botones mientras se procesa
        const buttons = document.querySelectorAll('.form-actions button');
        buttons.forEach(btn => btn.disabled = true);

        console.log('📤 Enviando segmento:', {
            segment_id: state.currentWord.id,
            review_status: review_status,
            text_revised: textRevised
        });

        // Enviar corrección
        await transcriptionService.submitWord(
            state.currentWord.id,
            review_status,
            textRevised
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
        userRole: 'annotator',
        fullEditMode: false
    };
    document.getElementById('messageArea').innerHTML = '';
    showLoginSection();
    document.getElementById('loginForm').reset();
}
