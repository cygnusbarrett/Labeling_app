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
    fullEditMode: false,
    fullEditTouched: false
};

const INITIAL_SEGMENT_LIMIT = 20;

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
        const loadingEl = document.getElementById('loadingState');
        loadingEl.textContent = 'Cargando segmentos...';
        loadingEl.style.display = 'block';
        document.getElementById('wordCard').style.display = 'none';
        document.getElementById('statsPanel').style.display = 'none';
        const completionMsg = document.getElementById('completionMessage');
        if (completionMsg) completionMsg.style.display = 'none';

        const wordsData = await transcriptionService.getWords(state.currentProject, 'pending', INITIAL_SEGMENT_LIMIT);
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
        state.fullEditTouched = false;
        const fullEditSection = document.getElementById('fullEditSection');
        if (fullEditSection) fullEditSection.classList.remove('active');
        const toggleLink = document.querySelector('.full-edit-toggle');
        if (toggleLink) toggleLink.style.display = '';

        // Reset context section
        const contextSection = document.getElementById('contextSection');
        if (contextSection) contextSection.style.display = 'none';
        const contextBtn = document.getElementById('contextBtn');
        if (contextBtn) contextBtn.textContent = '📖 Más contexto';

        // Actualizar interfaz con los datos del SEGMENTO
        // Speaker hidden by design
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
        closeDiscardModal();
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
            // Palabra incierta → input editable inline (placeholder, no pre-llenado)
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'inline-word-input';
            input.value = '';
            input.placeholder = wordObj.word;
            input.dataset.wordIndex = wordObj.word_index;
            input.dataset.originalWord = wordObj.word;
            input.title = `Confianza: ${(wordObj.probability * 100).toFixed(0)}% — escribe la corrección o deja vacío si está bien`;

            // Ancho dinámico basado en placeholder
            input.style.width = (Math.max(wordObj.word.length, 2) + 2) + 'ch';

            input.addEventListener('input', function() {
                this.style.width = (Math.max(this.value.length || this.placeholder.length, 2) + 2) + 'ch';
                // Marcar visualmente si fue modificado
                if (this.value.trim() !== '' && this.value !== this.dataset.originalWord) {
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
            // Palabra segura → texto estático, doble-click para editar
            const span = document.createElement('span');
            span.className = 'inline-word-static';
            span.textContent = wordObj.word;
            span.dataset.wordIndex = wordObj.word_index;
            span.dataset.originalWord = wordObj.word;
            span.title = 'Doble-click para editar';
            span.addEventListener('dblclick', function() {
                convertStaticToInput(this);
            });
            container.appendChild(span);
        }
    });
}

/**
 * Convierte una palabra estática en un input editable
 */
function convertStaticToInput(span) {
    const container = document.getElementById('highlightedText');
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'inline-word-input converted';
    input.value = span.textContent;
    input.dataset.wordIndex = span.dataset.wordIndex;
    input.dataset.originalWord = span.dataset.originalWord;
    input.title = 'Editando palabra (era segura)';
    input.style.width = (Math.max(span.textContent.length, 2) + 2) + 'ch';

    input.addEventListener('input', function() {
        this.style.width = (Math.max(this.value.length, 2) + 2) + 'ch';
        if (this.value !== this.dataset.originalWord) {
            this.classList.add('modified');
        } else {
            this.classList.remove('modified');
        }
        updateChangeIndicator();
    });

    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const allInputs = container.querySelectorAll('.inline-word-input');
            const idx = Array.from(allInputs).indexOf(this);
            if (idx < allInputs.length - 1) {
                allInputs[idx + 1].focus();
            } else {
                submitWord('approved');
            }
        } else if (e.key === 'Escape') {
            // Revertir a estático
            revertInputToStatic(this);
        }
    });

    span.replaceWith(input);
    input.focus();
    input.select();
    updateChangeIndicator();
}

/**
 * Revierte un input convertido a su estado estático original
 */
function revertInputToStatic(input) {
    const span = document.createElement('span');
    span.className = 'inline-word-static';
    span.textContent = input.dataset.originalWord;
    span.dataset.wordIndex = input.dataset.wordIndex;
    span.dataset.originalWord = input.dataset.originalWord;
    span.title = 'Doble-click para editar';
    span.addEventListener('dblclick', function() {
        convertStaticToInput(this);
    });
    input.replaceWith(span);
    updateChangeIndicator();
}

/**
 * Reconstruye el texto completo desde los elementos inline
 */
function reconstructText() {
    const container = document.getElementById('highlightedText');
    if (!container) return (state.currentWord?.text || '').trim();

    const elements = container.querySelectorAll('.inline-word-input, .inline-word-static');

    // Fallback: algunos segmentos no traen array de words en BD.
    // En esos casos usamos el texto mostrado (o el original del segmento)
    // para evitar enviar una corrección vacía.
    if (elements.length === 0) {
        const plainText = (container.textContent || '').trim();
        return plainText || (state.currentWord?.text || '').trim();
    }

    const words = [];

    elements.forEach(el => {
        if (el.classList.contains('inline-word-input')) {
            const val = el.value.trim();
            if (val.length > 0) {
                // Anotador escribió algo → usar lo que escribió
                words.push(val);
            } else {
                // Campo vacío → mantener palabra original del ASR
                words.push(el.dataset.originalWord);
            }
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
        const val = input.value.trim();
        // Cambio = campo con texto que difiere del original
        if (val !== '' && val !== input.dataset.originalWord) return true;
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
    const modifiedCount = Array.from(inputs).filter(i => i.value.trim() !== '' && i.value !== i.dataset.originalWord).length;

    const convertedCount = Array.from(inputs).filter(i => i.classList.contains('converted')).length;

    if (inputs.length === 0) {
        indicator.className = 'change-indicator no-changes';
        indicator.textContent = '✅ Sin palabras inciertas — escucha el audio y confirma (doble-click en cualquier palabra para editarla)';
    } else if (changed) {
        indicator.className = 'change-indicator has-changes';
        indicator.textContent = `✏️ ${modifiedCount} palabra(s) modificada(s) — se enviará como corregida`;
    } else {
        const extra = convertedCount > 0 ? ` (${convertedCount} desbloqueada(s))` : '';
        indicator.className = 'change-indicator no-changes';
        indicator.textContent = `🔍 ${inputs.length} palabra(s) en duda${extra} — escribe la corrección o confirma tal cual`;
    }
}

/**
 * Muestra/oculta el contexto de segmentos adyacentes y extiende el audio
 */
async function toggleContext() {
    const section = document.getElementById('contextSection');
    const btn = document.getElementById('contextBtn');

    if (section.style.display !== 'none') {
        // Ocultar contexto y restaurar audio original
        section.style.display = 'none';
        btn.textContent = '📖 Más contexto';
        try {
            const audioUrl = await transcriptionService.getWordAudio(state.currentProject, state.currentWord.id, 0.2);
            const audioPlayer = document.getElementById('audioPlayer');
            audioPlayer.src = audioUrl;
            audioPlayer.load();
        } catch (e) { console.error('Error restaurando audio:', e); }
        return;
    }

    btn.textContent = '⏳ Cargando...';
    btn.disabled = true;

    try {
        const ctx = await transcriptionService.getSegmentContext(state.currentProject, state.currentWord.id);

        // Texto del segmento actual
        document.getElementById('currentContextText').textContent = state.currentWord.text;

        // Segmento anterior
        const prevDiv = document.getElementById('prevContext');
        if (ctx.prev) {
            document.getElementById('prevContextText').textContent = ctx.prev.text;
            prevDiv.style.display = 'block';
        } else {
            prevDiv.style.display = 'none';
        }

        // Segmento siguiente
        const nextDiv = document.getElementById('nextContext');
        if (ctx.next) {
            document.getElementById('nextContextText').textContent = ctx.next.text;
            nextDiv.style.display = 'block';
        } else {
            nextDiv.style.display = 'none';
        }

        section.style.display = 'block';
        btn.textContent = '📖 Ocultar contexto';

        // Cargar audio extendido (incluye segmentos adyacentes)
        const audioUrl = await transcriptionService.getExtendedAudio(
            state.currentProject, state.currentWord.id,
            ctx.extended_start, ctx.extended_end
        );
        const audioPlayer = document.getElementById('audioPlayer');
        audioPlayer.src = audioUrl;
        audioPlayer.load();

    } catch (e) {
        console.error('Error cargando contexto:', e);
        showMessage('No se pudo cargar el contexto', 'error');
        btn.textContent = '📖 Más contexto';
    } finally {
        btn.disabled = false;
    }
}

/**
 * Alterna al modo de edición completa del texto
 */
function toggleFullEdit() {
    state.fullEditMode = true;
    state.fullEditTouched = false;
    const section = document.getElementById('fullEditSection');
    section.classList.add('active');
    
    // Pre-llenar con el texto reconstruido (por si ya se editó algo inline)
    const textarea = document.getElementById('correctedText');
    textarea.value = reconstructText();
    textarea.focus();

    // Detectar si el usuario realmente edita el textarea
    textarea.addEventListener('input', () => { state.fullEditTouched = true; }, { once: true });

    // Ocultar toggle link
    document.querySelector('.full-edit-toggle').style.display = 'none';
}

/**
 * Avanza al siguiente segmento o finaliza la sesión de revisión actual.
 */
function goToNextSegmentOrFinish() {
    if (state.currentWordIndex + 1 < state.allWords.length) {
        displayWord(state.currentWordIndex + 1);
    } else {
        showMessage('¡Has completado todos los segmentos! 🎉', 'success');
        document.getElementById('wordCard').style.display = 'none';
    }
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

        if (state.fullEditMode && state.fullEditTouched) {
            // Textarea fue editado manualmente: tiene prioridad sobre inline
            textRevised = document.getElementById('correctedText').value.trim();
            review_status = (textRevised !== state.currentWord.text.trim()) ? 'corrected' : 'approved';
        } else {
            // Modo inline (o fullEdit abierto pero no tocado): reconstruir desde inputs
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
        const statusText = review_status === 'approved'
            ? 'aprobada ✓'
            : (review_status === 'discarded' ? 'descartada 🗑️' : 'corregida ✎');
        showMessage(`Segmento ${statusText}`, 'success');

        // Actualizar estadísticas
        await updateStats();

        // Ir al siguiente segmento
        setTimeout(() => {
            goToNextSegmentOrFinish();
            buttons.forEach(btn => btn.disabled = false);
        }, 500);

    } catch (error) {
        showMessage(`Error enviando corrección: ${error.message}`, 'error');
        document.querySelectorAll('.form-actions button').forEach(btn => btn.disabled = false);
    }
}

function openDiscardModal() {
    if (!state.currentWord) {
        showMessage('No hay segmento seleccionado para descartar', 'error');
        return;
    }
    const modal = document.getElementById('discardModal');
    const reasonSelect = document.getElementById('discardReasonType');
    const reasonOther = document.getElementById('discardReasonOther');
    if (reasonSelect) reasonSelect.value = 'not_chilean_spanish';
    if (reasonOther) reasonOther.value = '';
    toggleDiscardOtherReasonInput();
    if (modal) modal.style.display = 'flex';
}

function closeDiscardModal() {
    const modal = document.getElementById('discardModal');
    if (modal) modal.style.display = 'none';
}

function toggleDiscardOtherReasonInput() {
    const reasonSelect = document.getElementById('discardReasonType');
    const otherWrap = document.getElementById('discardReasonOtherWrap');
    if (!reasonSelect || !otherWrap) return;
    otherWrap.style.display = reasonSelect.value === 'other' ? 'block' : 'none';
}

async function confirmDiscard() {
    try {
        if (!state.currentWord) {
            showMessage('No hay segmento seleccionado para descartar', 'error');
            return;
        }

        const reasonType = document.getElementById('discardReasonType')?.value;
        const reasonOther = (document.getElementById('discardReasonOther')?.value || '').trim();

        if (!reasonType) {
            showMessage('Selecciona un motivo de descarte', 'info');
            return;
        }

        if (reasonType === 'other' && !reasonOther) {
            showMessage('Escribe el detalle para el motivo "Otro"', 'info');
            return;
        }

        const formButtons = document.querySelectorAll('.form-actions button');
        const cancelBtn = document.getElementById('discardCancelBtn');
        const confirmBtn = document.getElementById('discardConfirmBtn');
        formButtons.forEach(btn => btn.disabled = true);
        if (cancelBtn) cancelBtn.disabled = true;
        if (confirmBtn) confirmBtn.disabled = true;

        await transcriptionService.submitWord(
            state.currentWord.id,
            'discarded',
            reconstructText(),
            {
                discard_reason_type: reasonType,
                discard_reason_note: reasonType === 'other' ? reasonOther : ''
            }
        );

        closeDiscardModal();
        showMessage('Segmento descartado correctamente', 'success');
        await updateStats();

        setTimeout(() => {
            goToNextSegmentOrFinish();
            formButtons.forEach(btn => btn.disabled = false);
            if (cancelBtn) cancelBtn.disabled = false;
            if (confirmBtn) confirmBtn.disabled = false;
        }, 400);
    } catch (error) {
        showMessage(`Error descartando segmento: ${error.message}`, 'error');
        document.querySelectorAll('.form-actions button').forEach(btn => btn.disabled = false);
        const cancelBtn = document.getElementById('discardCancelBtn');
        const confirmBtn = document.getElementById('discardConfirmBtn');
        if (cancelBtn) cancelBtn.disabled = false;
        if (confirmBtn) confirmBtn.disabled = false;
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
            const completed = (stats.approved_segments || 0) + (stats.corrected_segments || 0) + (stats.discarded_segments || 0) || stats.words_completed || 0;
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
        showMessage(`No se pudieron cargar estadísticas: ${error.message}`, 'error');
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
async function logout() {
    try {
        await transcriptionService.logout();
    } catch (error) {
        console.error('Error al cerrar sesión:', error);
    } finally {
        window.location.href = '/login?logged_out=1';
    }
}
