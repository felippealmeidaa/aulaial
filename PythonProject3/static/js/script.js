// ============================================
// FUNÇÃO GLOBAL PARA TOAST MESSAGES
// ============================================
function showToastMessage(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast-message ${type}`;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : type === 'warning' ? '#ffc107' : '#17a2b8'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        z-index: 10000;
        font-weight: 600;
        animation: slideDown 0.3s ease;
        max-width: 400px;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================
// MODO ESCURO (SEM TOAST) - CORRIGIDO
// ============================================
function toggleDarkMode() {
    const body = document.body;
    body.classList.toggle('dark-mode');

    const isDark = body.classList.contains('dark-mode');

    // Atualizar ícones
    const darkIcon = document.querySelector('.dark-icon');
    const lightIcon = document.querySelector('.light-icon');

    if (darkIcon && lightIcon) {
        if (isDark) {
            darkIcon.style.display = 'none';
            lightIcon.style.display = 'inline';
        } else {
            darkIcon.style.display = 'inline';
            lightIcon.style.display = 'none';
        }
    }

    // Salvar preferência no servidor (SEM TOAST) - CORRIGIDO
    fetch('/api/toggle_dark_mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    }).then(response => response.json())
      .then(data => {
          // Modo alterado silenciosamente - SEM showToastMessage
          console.log(isDark ? 'Modo escuro ativado' : 'Modo claro ativado');
      });
}

// Carregar preferência de modo escuro
document.addEventListener('DOMContentLoaded', () => {
    // SEMPRE INICIA NO MODO CLARO (padrão)
    // Para iniciar no modo escuro, mude a linha abaixo para: if (true) {
    if (false) {
        document.body.classList.add('dark-mode');

        // Atualizar ícones
        const darkIcon = document.querySelector('.dark-icon');
        const lightIcon = document.querySelector('.light-icon');

        if (darkIcon && lightIcon) {
            darkIcon.style.display = 'none';
            lightIcon.style.display = 'inline';
        }
    }
});

// ============================================
// SISTEMA DE NOTIFICAÇÕES
// ============================================
let notificacoes = [];
let naoLidas = 0;

async function carregarNotificacoes() {
    try {
        const response = await fetch('/api/notificacoes');
        const data = await response.json();

        if (data.success) {
            notificacoes = data.notificacoes;
            naoLidas = data.nao_lidas;
            atualizarBadgeNotificacoes();
        }
    } catch (error) {
        console.error('Erro ao carregar notificações:', error);
    }
}

function atualizarBadgeNotificacoes() {
    const badge = document.getElementById('notif-badge');
    if (badge) {
        if (naoLidas > 0) {
            badge.textContent = naoLidas;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    }
}

function toggleNotificacoes() {
    const dropdown = document.getElementById('notif-dropdown');
    if (dropdown.style.display === 'block') {
        dropdown.style.display = 'none';
    } else {
        dropdown.style.display = 'block';
        renderNotificacoes();
    }
}

function renderNotificacoes() {
    const lista = document.getElementById('notif-list');
    lista.innerHTML = '';

    if (notificacoes.length === 0) {
        lista.innerHTML = '<div class="notif-empty">📭 Sem notificações</div>';
        return;
    }

    notificacoes.forEach(notif => {
        const div = document.createElement('div');
        div.className = `notif-item ${notif.lida ? '' : 'notif-unread'}`;
        div.innerHTML = `
            <div class="notif-icon">${notif.tipo === 'curtida' ? '❤️' : '💬'}</div>
            <div class="notif-content">
                <p>${notif.mensagem}</p>
                <span class="notif-time">${notif.data}</span>
            </div>
        `;
        div.onclick = () => marcarComoLida(notif.id, notif.link);
        lista.appendChild(div);
    });
}

async function marcarComoLida(notifId, link) {
    try {
        await fetch('/api/notificacoes/marcar_lida', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notificacao_id: notifId })
        });

        await carregarNotificacoes();

        if (link) {
            window.location.href = link;
        }
    } catch (error) {
        console.error('Erro ao marcar notificação:', error);
    }
}

async function marcarTodasLidas() {
    try {
        await fetch('/api/notificacoes/marcar_todas_lidas', {
            method: 'POST'
        });
        await carregarNotificacoes();
        showToastMessage('✅ Todas as notificações foram marcadas como lidas', 'success');
    } catch (error) {
        console.error('Erro:', error);
    }
}

// Carregar notificações a cada 30 segundos
setInterval(carregarNotificacoes, 30000);

// ============================================
// BUSCA E FILTROS DE POSTS
// ============================================
let currentSearchTerm = '';
let currentFilterType = '';

function filtrarPosts() {
    const activeTab = document.querySelector('.curso-tab.active');
    if (!activeTab) return;

    const curso = activeTab.dataset.curso;
    const searchInput = document.getElementById(`searchPosts-${curso}`);
    const filterType = document.getElementById(`filterTipo-${curso}`);

    if (!searchInput || !filterType) return;

    currentSearchTerm = searchInput.value.toLowerCase();
    currentFilterType = filterType.value;

    const activeGrid = document.querySelector('.curso-content.active .community-grid');
    if (!activeGrid) return;

    const posts = activeGrid.querySelectorAll('.post-card');

    posts.forEach(post => {
        const titulo = post.querySelector('.post-content h3').textContent.toLowerCase();
        const conteudo = post.querySelector('.post-content p').textContent.toLowerCase();
        const tags = post.querySelector('.post-tags')?.textContent.toLowerCase() || '';

        let postTipo = '';
        const postTag = post.querySelector('.post-tag');
        if (postTag) {
            if (postTag.classList.contains('projeto')) postTipo = 'projeto';
            else if (postTag.classList.contains('duvida')) postTipo = 'duvida';
            else if (postTag.classList.contains('discussao')) postTipo = 'discussao';
        }

        const matchTermo = !currentSearchTerm ||
                          titulo.includes(currentSearchTerm) ||
                          conteudo.includes(currentSearchTerm) ||
                          tags.includes(currentSearchTerm);

        const matchTipo = !currentFilterType || postTipo === currentFilterType;

        post.style.display = (matchTermo && matchTipo) ? 'block' : 'none';
    });
}

// ============================================
// LAZY LOADING DE POSTS
// ============================================
let currentPage = 1;
const postsPerPage = 10;
let isLoading = false;
let hasMore = true;

async function carregarMaisPosts() {
    if (isLoading || !hasMore) return;

    const activeTab = document.querySelector('.curso-tab.active');
    if (!activeTab) return;

    const curso = activeTab.dataset.curso;
    isLoading = true;

    try {
        const response = await fetch(`/api/posts?curso=${curso}&page=${currentPage}&limit=${postsPerPage}`);
        const data = await response.json();

        if (data.success && data.posts.length > 0) {
            const grid = document.querySelector(`#curso-${curso} .community-grid`);

            data.posts.forEach(post => {
                const postCard = criarPostCard(post, curso);
                grid.appendChild(postCard);
                carregarInteracoes(postCard);
            });

            currentPage++;

            if (data.posts.length < postsPerPage) {
                hasMore = false;
            }
        } else {
            hasMore = false;
        }
    } catch (error) {
        console.error('Erro ao carregar posts:', error);
    } finally {
        isLoading = false;
    }
}

function criarPostCard(post, curso) {
    const avatarMap = {
        'ia': '👨‍💻',
        'ads': '📊',
        'es': '⚙️'
    };

    const tipoLabelMap = {
        'projeto': '📌 Projeto',
        'duvida': '❓ Dúvida',
        'discussao': '💡 Discussão'
    };

    const postCard = document.createElement('div');
    postCard.className = 'post-card';
    postCard.dataset.postId = post.post_id;

    const deleteBtn = post.e_meu ? `
        <button class="btn-delete-post" onclick="deletePost(this, '${post.post_id}')" title="Excluir post">
            🗑️
        </button>
    ` : '';

    const tagsHtml = post.tags ? `<div class="post-tags">🏷️ ${post.tags}</div>` : '';

    postCard.innerHTML = `
        <div class="post-header">
            <div class="user-info">
                <div class="avatar">${avatarMap[curso] || '👨‍💻'}</div>
                <div>
                    <h4>${post.nome_usuario}</h4>
                    <span class="post-time">${post.data}</span>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span class="post-tag ${post.tipo}">
                    ${tipoLabelMap[post.tipo] || ''}
                </span>
                ${deleteBtn}
            </div>
        </div>
        <div class="post-content">
            <h3>${post.titulo}</h3>
            <p>${post.conteudo}</p>
            ${tagsHtml}
        </div>
        <div class="post-footer">
            <button class="post-action like-btn" onclick="likePost(this)">
                👍 <span class="like-count">0</span> curtidas
            </button>
            <button class="post-action comment-btn" onclick="toggleComments(this)">
                💬 <span class="comment-count">0</span> comentários
            </button>
        </div>
        <div class="comments-section" style="display: none;">
            <div class="comments-list"></div>
            <div class="comment-input">
                <input type="text" class="comment-field" placeholder="Escreva um comentário...">
                <button class="btn-comment" onclick="addComment(this)">Enviar</button>
            </div>
        </div>
    `;

    return postCard;
}

window.addEventListener('scroll', () => {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 500) {
        carregarMaisPosts();
    }
});

// ============================================
// NAVEGAÇÃO ENTRE SEÇÕES
// ============================================
function showSection(sectionId, clickedElement) {
    const sections = document.querySelectorAll('.section');
    const navLinks = document.querySelectorAll('.nav-link');

    sections.forEach(section => section.classList.remove('active'));
    navLinks.forEach(link => link.classList.remove('active'));

    const section = document.getElementById(sectionId);
    if (section) {
        section.classList.add('active');
    }

    if (clickedElement) {
        clickedElement.classList.add('active');
    }

    if (sectionId === 'comunidade') {
        carregarTodasInteracoes();
    }

    if (sectionId === 'calendario' && typeof calendar !== 'undefined') {
        calendar.render();
        calendar.refetchEvents();
    }
}

function showCurso(cursoId, clickedElement) {
    const cursoContents = document.querySelectorAll('.curso-content');
    const cursoTabs = document.querySelectorAll('.curso-tab');
    cursoContents.forEach(content => content.classList.remove('active'));
    cursoTabs.forEach(tab => tab.classList.remove('active'));

    const content = document.getElementById('curso-' + cursoId);
    if (content) content.classList.add('active');
    if (clickedElement) clickedElement.classList.add('active');

    currentPage = 1;
    hasMore = true;
}

// ============================================
// CURTIR POST - ULTRA OTIMIZADO (COM DEBOUNCE)
// ============================================
const pendingLikes = new Set();
const likeDebounceTimers = new Map();

async function likePost(button) {
    const postCard = button.closest('.post-card');
    const postId = postCard.dataset.postId;

    if (likeDebounceTimers.has(postId)) {
        clearTimeout(likeDebounceTimers.get(postId));
    }

    const isCurrentlyLiked = button.classList.contains('liked');
    const currentCount = parseInt(button.querySelector('.like-count').textContent) || 0;

    if (isCurrentlyLiked) {
        button.classList.remove('liked');
        button.innerHTML = `👍 <span class="like-count">${currentCount - 1}</span> curtidas`;
    } else {
        button.classList.add('liked');
        button.innerHTML = `❤️ <span class="like-count">${currentCount + 1}</span> curtidas`;
        createHeartAnimation(button);
    }

    const debounceTimer = setTimeout(async () => {
        if (pendingLikes.has(postId)) {
            return;
        }

        pendingLikes.add(postId);

        try {
            const response = await fetch('/api/curtir', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ post_id: postId })
            });
            const data = await response.json();

            if (data.success) {
                if (data.acao === 'curtiu') {
                    button.classList.add('liked');
                    button.innerHTML = `❤️ <span class="like-count">${data.total_curtidas}</span> curtidas`;
                } else {
                    button.classList.remove('liked');
                    button.innerHTML = `👍 <span class="like-count">${data.total_curtidas}</span> curtidas`;
                }
            } else {
                const currentState = button.classList.contains('liked');
                if (currentState !== isCurrentlyLiked) {
                    if (isCurrentlyLiked) {
                        button.classList.add('liked');
                        button.innerHTML = `❤️ <span class="like-count">${currentCount}</span> curtidas`;
                    } else {
                        button.classList.remove('liked');
                        button.innerHTML = `👍 <span class="like-count">${currentCount}</span> curtidas`;
                    }
                }
                showToastMessage(data.error || 'Erro ao curtir', 'error');
            }
        } catch (error) {
            const currentState = button.classList.contains('liked');
            if (currentState !== isCurrentlyLiked) {
                if (isCurrentlyLiked) {
                    button.classList.add('liked');
                    button.innerHTML = `❤️ <span class="like-count">${currentCount}</span> curtidas`;
                } else {
                    button.classList.remove('liked');
                    button.innerHTML = `👍 <span class="like-count">${currentCount}</span> curtidas`;
                }
            }
            console.error('Erro ao curtir:', error);
            showToastMessage('Erro de conexão', 'error');
        } finally {
            pendingLikes.delete(postId);
            likeDebounceTimers.delete(postId);
        }
    }, 300);

    likeDebounceTimers.set(postId, debounceTimer);
}

function createHeartAnimation(button) {
    const heart = document.createElement('span');
    heart.textContent = '❤️';
    heart.style.position = 'absolute';
    heart.style.fontSize = '24px';
    heart.style.animation = 'heartFloat 1s ease-out';
    heart.style.pointerEvents = 'none';
    const rect = button.getBoundingClientRect();
    heart.style.left = rect.left + rect.width / 2 + 'px';
    heart.style.top = rect.top + 'px';
    document.body.appendChild(heart);
    setTimeout(() => heart.remove(), 1000);
}

// ============================================
// COMENTÁRIOS
// ============================================
function toggleComments(button) {
    const postCard = button.closest('.post-card');
    const commentsSection = postCard.querySelector('.comments-section');
    const commentCount = postCard.querySelectorAll('.comment').length;

    if (!commentsSection) return;

    if (commentsSection.style.display === 'none' || commentsSection.style.display === '') {
        commentsSection.style.display = 'block';
        button.innerHTML = `💬 <span class="comment-count">${commentCount}</span> comentários ▲`;
        const commentsList = postCard.querySelector('.comments-list');
        if (commentsList) commentsList.scrollTop = commentsList.scrollHeight;
    } else {
        commentsSection.style.display = 'none';
        button.innerHTML = `💬 <span class="comment-count">${commentCount}</span> comentários`;
    }
}

async function addComment(button) {
    const commentInput = button.previousElementSibling;
    const commentText = commentInput.value.trim();
    if (!commentText) {
        showToastMessage('⚠️ Digite um comentário!', 'warning');
        return;
    }
    const postCard = button.closest('.post-card');
    const postId = postCard.dataset.postId;

    button.disabled = true;

    try {
        const response = await fetch('/api/comentar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ post_id: postId, comentario: commentText })
        });
        const data = await response.json();
        if (data.success) {
            const commentsList = postCard.querySelector('.comments-list');
            const commentButton = postCard.querySelector('.comment-btn');
            const newComment = document.createElement('div');
            newComment.className = 'comment';
            newComment.dataset.commentId = data.comentario_id;
            newComment.innerHTML = `
                <div class="comment-avatar">😊</div>
                <div class="comment-content">
                    <strong>${data.nome_usuario}</strong>
                    <p>${data.comentario}</p>
                    <span class="comment-time">${data.data}</span>
                </div>
                <button class="btn-delete-comment" onclick="deleteComment(this, ${data.comentario_id})" title="Excluir comentário">
                    🗑️
                </button>
            `;
            commentsList.appendChild(newComment);
            const totalComments = commentsList.querySelectorAll('.comment').length;
            commentButton.querySelector('.comment-count').textContent = totalComments;
            commentInput.value = '';
            commentsList.scrollTop = commentsList.scrollHeight;
            showToastMessage('✅ Comentário adicionado!', 'success');
        } else {
            showToastMessage(data.error || 'Erro ao comentar', 'error');
        }
    } catch (error) {
        console.error('Erro ao comentar:', error);
        showToastMessage('Erro de conexão', 'error');
    } finally {
        button.disabled = false;
    }
}

async function deleteComment(button, commentId) {
    if (!confirm('Deseja excluir este comentário?')) return;

    try {
        const response = await fetch('/api/excluir_comentario', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ comentario_id: commentId })
        });
        const data = await response.json();
        if (data.success) {
            const commentElement = button.closest('.comment');
            const postCard = button.closest('.post-card');
            commentElement.remove();
            const totalComments = postCard.querySelectorAll('.comment').length;
            postCard.querySelector('.comment-btn .comment-count').textContent = totalComments;
            showToastMessage('✅ Comentário excluído!', 'success');
        } else {
            showToastMessage('❌ ' + (data.error || 'Erro'), 'error');
        }
    } catch (error) {
        console.error('Erro:', error);
        showToastMessage('❌ Erro de conexão', 'error');
    }
}

// ============================================
// EXCLUIR POST
// ============================================
async function deletePost(buttonElement, postId) {
    if (!confirm('⚠️ Deseja excluir este post?\n\nEsta ação não pode ser desfeita!')) {
        return;
    }

    if (buttonElement) buttonElement.disabled = true;

    try {
        const response = await fetch('/api/excluir_post', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ post_id: postId })
        });
        const data = await response.json();
        if (data.success) {
            const postCard = buttonElement.closest('.post-card');
            postCard.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => postCard.remove(), 300);
            showToastMessage('✅ Post excluído!', 'success');
        } else {
            showToastMessage('❌ ' + (data.error || 'Erro'), 'error');
        }
    } catch (error) {
        console.error('❌ Erro:', error);
        showToastMessage('❌ Erro de conexão', 'error');
    } finally {
        if (buttonElement) buttonElement.disabled = false;
    }
}

// ============================================
// CRIAR POST (COM TAGS)
// ============================================
function openCreatePostModal(curso) {
    const modal = document.getElementById('createPostModal');
    const cursoNames = {
        'ia': 'Inteligência Artificial',
        'ads': 'Análise e Desenvolvimento de Sistemas',
        'es': 'Engenharia de Software'
    };
    document.getElementById('modalCursoName').textContent = cursoNames[curso] || 'Curso';
    document.getElementById('postCurso').value = curso;
    document.getElementById('postTitulo').value = '';
    document.getElementById('postConteudo').value = '';
    document.getElementById('postTags').value = '';
    modal.style.display = 'flex';
}

function closeCreatePostModal() {
    document.getElementById('createPostModal').style.display = 'none';
}

async function createPost() {
    const curso = document.getElementById('postCurso').value;
    const tipo = document.getElementById('postTipo').value;
    const titulo = document.getElementById('postTitulo').value.trim();
    const conteudo = document.getElementById('postConteudo').value.trim();
    const tags = document.getElementById('postTags').value.trim();

    if (!titulo || !conteudo) {
        showToastMessage('⚠️ Preencha todos os campos!', 'warning');
        return;
    }

    const createPostBtn = document.querySelector('#createPostModal .modal-btn-create');

    // Prevenir cliques múltiplos
    if (createPostBtn.disabled) {
        return;
    }

    const originalText = createPostBtn.textContent;
    createPostBtn.textContent = 'Publicando...';
    createPostBtn.disabled = true;

    try {
        const response = await fetch('/api/criar_post', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ curso, tipo, titulo, conteudo, tags })
        });

        const data = await response.json();

        // Fecha o modal
        closeCreatePostModal();

        // Mostra mensagem de sucesso
        showToastMessage('✅ Post criado com sucesso!', 'success');

        // Adiciona o post manualmente na interface (SEM RECARREGAR)
        const grid = document.querySelector(`#curso-${curso} .community-grid`);
        if (grid) {
            // Remover mensagem "nenhum post" se existir
            const noPostMsg = grid.querySelector('.no-posts');
            if (noPostMsg) {
                noPostMsg.remove();
            }

            // Criar objeto do post
            const postObj = {
                post_id: data.post_id || `temp_${Date.now()}`,
                tipo: tipo,
                titulo: titulo,
                conteudo: conteudo,
                tags: tags,
                nome_usuario: data.nome_usuario || 'Você',
                data: data.data || 'Agora',
                e_meu: true
            };

            // Criar e adicionar card
            const postCard = criarPostCard(postObj, curso);
            grid.insertBefore(postCard, grid.firstChild);

            // Carregar interações (curtidas e comentários)
            carregarInteracoes(postCard);

            // Scroll suave até o novo post
            setTimeout(() => {
                postCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 100);
        }

    } catch (error) {
        console.error('Erro ao criar post:', error);
        closeCreatePostModal();
        showToastMessage('✅ Post criado com sucesso!', 'success');
    } finally {
        createPostBtn.textContent = originalText;
        createPostBtn.disabled = false;
    }
}

window.onclick = function(event) {
    const createPostModal = document.getElementById('createPostModal');
    const eventModal = document.getElementById('eventModal');
    if (event.target === createPostModal) {
        closeCreatePostModal();
    }
    if (event.target === eventModal) {
        closeEventModal();
    }
};

// ============================================
// CARREGAR INTERAÇÕES
// ============================================
async function carregarInteracoes(postCard) {
    const postId = postCard.dataset.postId;
    try {
        const response = await fetch(`/api/interacoes/${postId}`);
        const data = await response.json();
        if (data.success) {
            const likeButton = postCard.querySelector('.like-btn');
            if (likeButton) {
                if (data.usuario_curtiu) {
                    likeButton.classList.add('liked');
                    likeButton.innerHTML = `❤️ <span class="like-count">${data.total_curtidas}</span> curtidas`;
                } else {
                    likeButton.classList.remove('liked');
                    likeButton.innerHTML = `👍 <span class="like-count">${data.total_curtidas}</span> curtidas`;
                }
            }

            const commentButton = postCard.querySelector('.comment-btn');
            if (commentButton) {
                commentButton.querySelector('.comment-count').textContent = data.total_comentarios;
            }
            const commentsList = postCard.querySelector('.comments-list');
            if (commentsList) {
                commentsList.innerHTML = '';
                data.comentarios.forEach(comentario => {
                    const commentDiv = document.createElement('div');
                    commentDiv.className = 'comment';
                    commentDiv.dataset.commentId = comentario.id;
                    const deleteButton = comentario.e_meu
                        ? `<button class="btn-delete-comment" onclick="deleteComment(this, ${comentario.id})" title="Excluir">🗑️</button>`
                        : '';
                    commentDiv.innerHTML = `
                        <div class="comment-avatar">😊</div>
                        <div class="comment-content">
                            <strong>${comentario.nome_usuario}</strong>
                            <p>${comentario.comentario}</p>
                            <span class="comment-time">${comentario.data}</span>
                        </div>
                        ${deleteButton}
                    `;
                    commentsList.appendChild(commentDiv);
                });
            }
        }
    } catch (error) {
        console.error('Erro ao carregar interações:', error);
    }
}

function carregarTodasInteracoes() {
    document.querySelectorAll('.post-card').forEach(postCard => {
        if (postCard.dataset.postId) carregarInteracoes(postCard);
    });
}

// ============================================
// CHAT COM MARKDOWN
// ============================================
document.getElementById('chatForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('chatInput');
    const submitBtn = document.querySelector('#chatForm button[type="submit"]');
    const message = input.value.trim();

    // Validar: precisa ter mensagem OU anexo
    if (!message && !currentAttachment) {
        showToastMessage('⚠️ Digite uma mensagem ou anexe um arquivo', 'warning');
        return;
    }

    // Adicionar mensagem do usuário
    addMessage(message || '(Anexo enviado)', 'user');

    // Adicionar preview de anexo na mensagem (se houver)
    if (currentAttachment && attachmentType === 'file') {
        addAttachmentToMessage(currentAttachment);
    } else if (currentAttachment && attachmentType === 'youtube') {
        addYouTubeToMessage(currentAttachment);
    }

    input.value = '';

    const loadingId = 'loading-' + Date.now();
    addLoadingMessage(loadingId);

    try {
        let response;

        // Escolher endpoint baseado no tipo de anexo
        if (attachmentType === 'file') {
            // Enviar com arquivo
            response = await sendMessageWithFile(message || 'Resuma este documento', currentAttachment);
        } else if (attachmentType === 'youtube') {
            // Enviar com YouTube
            response = await sendMessageWithYouTube(message || 'Resuma este vídeo', currentAttachment);
        } else {
            // Mensagem normal
            response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
        }

        const data = await response.json();

        removeLoadingMessage(loadingId);

        // Limpar anexo após envio
        if (currentAttachment) {
            removeAttachment();
        }

        // Verificar rate limit
        if (data.rate_limited && data.wait_time > 0) {
            addMessage(data.response, 'bot');
            input.disabled = true;
            submitBtn.disabled = true;
            const originalText = submitBtn.textContent;
            let countdown = data.wait_time;
            const countdownInterval = setInterval(() => {
                submitBtn.textContent = `Aguarde ${countdown}s...`;
                countdown--;
                if (countdown < 0) {
                    clearInterval(countdownInterval);
                    input.disabled = false;
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                }
            }, 1000);
            return;
        }

        addMessage(data.response, 'bot');

    } catch (error) {
        removeLoadingMessage(loadingId);
        addMessage('Erro de conexão. Tente novamente.', 'bot');
        console.error('Erro:', error);
    }
});

function addLoadingMessage(id) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    messageDiv.id = id;
    messageDiv.innerHTML = `<div class="message-content"><p>Pensando<span class="dots">...</span></p></div>`;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function removeLoadingMessage(id) {
    document.getElementById(id)?.remove();
}

function addMessage(text, type) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;

    let contentHtml = '';
    if (type === 'bot' && typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true,
            headerIds: false,
            mangle: false
        });
        contentHtml = marked.parse(text);
    } else {
        contentHtml = `<p>${text.replace(/\\n/g, '<br>')}</p>`;
    }

    messageDiv.innerHTML = `<div class="message-content">${contentHtml}</div>`;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ============================================
// HISTÓRICO DE CHAT
// ============================================
async function carregarHistoricoChat() {
    try {
        const response = await fetch('/api/historico_chat?limite=20');
        const data = await response.json();
        if (data.success && data.historico.length > 0) {
            const messagesContainer = document.getElementById('chatMessages');
            messagesContainer.innerHTML = `
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, var(--primary), #764ba2); color: white; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
                    <h3 style="margin: 0 0 10px 0;">📜 HISTÓRICO DE CONVERSAS</h3>
                    <p style="margin: 0; opacity: 0.9; font-size: 14px;">Últimas ${data.historico.length} mensagens</p>
                </div>
            `;
            data.historico.reverse().forEach(item => {
                addMessage(item.mensagem, 'user');
                addMessage(item.resposta, 'bot');
            });
            const separator = document.createElement('div');
            separator.style.cssText = `
                text-align: center;
                padding: 15px;
                margin: 20px 0;
                border-top: 2px solid var(--primary);
                border-bottom: 2px solid var(--primary);
                color: var(--primary);
                font-weight: bold;
                background: rgba(74, 144, 226, 0.1);
                border-radius: 10px;
            `;
            separator.textContent = '⬇️ NOVA CONVERSA ⬇️';
            messagesContainer.appendChild(separator);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        } else {
            showToastMessage('📭 Nenhum histórico encontrado', 'info');
        }
    } catch (error) {
        console.error('Erro:', error);
        showToastMessage('❌ Erro ao carregar histórico', 'error');
    }
}

async function limparHistoricoChat() {
    if (!confirm('⚠️ Deseja limpar todo o histórico?\n\nEsta ação não pode ser desfeita!')) {
        return;
    }
    try {
        const response = await fetch('/api/limpar_historico', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            document.getElementById('chatMessages').innerHTML = '';
            showToastMessage('✅ ' + data.message, 'success');
            addMessage('Olá! 😊 Sou o assistente da IAUniev. Como posso ajudar?', 'bot');
        } else {
            showToastMessage('❌ ' + (data.error || 'Erro'), 'error');
        }
    } catch (error) {
        console.error('Erro:', error);
        showToastMessage('❌ Erro ao limpar histórico', 'error');
    }
}

// ============================================
// PERFIL
// ============================================
function showPerfilTab(tabName, clickedElement) {
    document.querySelectorAll('.perfil-content').forEach(content => {
        content.classList.remove('active');
    });
    document.querySelectorAll('.perfil-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    const content = document.getElementById('perfil-' + tabName);
    if (content) content.classList.add('active');
    if (clickedElement) clickedElement.classList.add('active');
}

// ============================================
// EXPORT DE NOTAS
// ============================================
function exportarNotas(formato) {
    window.location.href = `/api/exportar_notas/${formato}`;
    showToastMessage(`📄 Baixando relatório em ${formato.toUpperCase()}...`, 'info');
}

// ============================================
// CALENDÁRIO
// ============================================
let calendar;
let selectedColor = '#4a90e2';

function selectColor(element) {
    document.querySelectorAll('.color-option').forEach(opt => opt.classList.remove('selected'));
    element.classList.add('selected');
    selectedColor = element.dataset.color;
}

function toggleAlertaMinutos() {
    const checkbox = document.getElementById('eventoAlerta');
    const alertaGroup = document.getElementById('alertaMinutosGroup');
    if (!checkbox || !alertaGroup) return;
    alertaGroup.style.display = checkbox.checked ? 'block' : 'none';
}

document.addEventListener('DOMContentLoaded', function() {
    carregarNotificacoes();

    const calendarEl = document.getElementById('calendar');
    if (calendarEl) {
        calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            locale: 'pt-br',
            height: 'auto',
            fixedWeekCount: false,
            showNonCurrentDates: false,
            headerToolbar: {
                left: 'prev,next',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,listMonth'
            },
            buttonText: {
                today: 'Hoje',
                month: 'Mês',
                week: 'Semana',
                list: 'Lista'
            },
            events: function(info, successCallback, failureCallback) {
                fetch('/api/eventos_calendario')
                    .then(response => {
                        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                        return response.json();
                    })
                    .then(data => {
                        if (data.success) {
                            successCallback(data.eventos);
                        } else {
                            failureCallback(data.error);
                        }
                    })
                    .catch(error => {
                        console.error('Erro:', error);
                        failureCallback(error);
                    });
            },
            eventClick: function(info) {
                if (info.event.extendedProps && info.event.extendedProps.pessoal) {
                    if (confirm('❌ Deseja excluir este evento?\n\n' + info.event.title)) {
                        excluirEvento(info.event.id);
                    }
                } else {
                    const descricao = info.event.extendedProps && info.event.extendedProps.descricao
                        ? '\n\n' + info.event.extendedProps.descricao
                        : '';
                    alert('📅 Evento Acadêmico: ' + info.event.title + descricao);
                }
            },
            eventDidMount: function(info) {
                if (info.event.extendedProps && info.event.extendedProps.descricao) {
                    info.el.title = info.event.extendedProps.descricao;
                }
            }
        });
        calendar.render();
    }

    const defaultColorOption = document.querySelector('.color-option[data-color="#4a90e2"]');
    if (defaultColorOption) defaultColorOption.classList.add('selected');

    const alertaGroup = document.getElementById('alertaMinutosGroup');
    if (alertaGroup) alertaGroup.style.display = 'none';

    document.querySelectorAll('.perfil-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            showPerfilTab(this.dataset.tab, this);
        });
    });

    document.querySelectorAll('.curso-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            showCurso(this.dataset.curso, this);
        });
    });

    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.classList.contains('logout')) return;
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const sectionId = this.dataset.section;
            if (sectionId) {
                showSection(sectionId, this);
            }
        });
    });

    document.querySelectorAll('.community-grid').forEach(grid => {
        grid.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && e.target.classList.contains('comment-field')) {
                e.preventDefault();
                addComment(e.target.nextElementSibling);
            }
        });
    });

    const btnCreateEvent = document.getElementById('btnCreateEvent');
    if (btnCreateEvent) {
        btnCreateEvent.addEventListener('click', createEvent);
    }

    carregarTodasInteracoes();

    const initialNavLink = document.querySelector('.nav-link.active');
    if (initialNavLink) {
        const sectionId = initialNavLink.dataset.section;
        if (sectionId) {
            showSection(sectionId, initialNavLink);
        }
    }

    // NÃO adicionar event listener aqui - o botão já usa onclick="createPost()"
});

function openEventModal() {
    const modal = document.getElementById('eventModal');
    if (!modal) return;
    modal.style.display = 'flex';
    const hoje = new Date().toISOString().split('T')[0];
    document.getElementById('eventoTitulo').value = '';
    document.getElementById('eventoDescricao').value = '';
    document.getElementById('eventoData').value = hoje;
    document.getElementById('eventoHora').value = '';
    document.getElementById('eventoTipo').value = 'pessoal';
    document.getElementById('eventoAlerta').checked = false;
    const alertaGroup = document.getElementById('alertaMinutosGroup');
    if (alertaGroup) alertaGroup.style.display = 'none';
    document.getElementById('alertaMinutos').value = '30';
    selectedColor = '#4a90e2';
    document.querySelectorAll('.color-option').forEach(opt => opt.classList.remove('selected'));
    const defaultColorOption = document.querySelector('.color-option[data-color="#4a90e2"]');
    if (defaultColorOption) defaultColorOption.classList.add('selected');
}

function closeEventModal() {
    const modal = document.getElementById('eventModal');
    if (!modal) return;
    modal.style.display = 'none';
}

async function createEvent() {
    const titulo = document.getElementById('eventoTitulo').value.trim();
    const descricao = document.getElementById('eventoDescricao').value.trim();
    const data = document.getElementById('eventoData').value;
    const hora = document.getElementById('eventoHora').value;
    const tipo = document.getElementById('eventoTipo').value;
    const alerta = document.getElementById('eventoAlerta').checked ? 1 : 0;
    const minutos_antes_alerta = parseInt(document.getElementById('alertaMinutos').value || '30', 10);

    if (!titulo || !data) {
        showToastMessage('⚠️ Preencha título e data!', 'warning');
        return;
    }

    const btnCreate = document.getElementById('btnCreateEvent');
    const originalText = btnCreate.textContent;
    btnCreate.textContent = 'Criando...';
    btnCreate.disabled = true;

    try {
        const response = await fetch('/api/criar_evento', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                titulo,
                descricao,
                data,
                hora,
                tipo,
                cor: selectedColor,
                alerta,
                minutos_antes_alerta
            })
        });

        const dataResponse = await response.json();
        if (response.ok && dataResponse.success) {
            showToastMessage('✅ Evento criado!', 'success');
            closeEventModal();
            if (calendar) calendar.refetchEvents();
        } else {
            showToastMessage('❌ Erro: ' + (dataResponse.error || 'Erro desconhecido'), 'error');
        }
    } catch (error) {
        console.error('Erro:', error);
        showToastMessage('❌ Erro: ' + error.message, 'error');
    } finally {
        btnCreate.textContent = originalText;
        btnCreate.disabled = false;
    }
}

async function excluirEvento(eventoId) {
    try {
        const response = await fetch('/api/excluir_evento', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ evento_id: eventoId })
        });

        const data = await response.json();
        if (response.ok && data.success) {
            showToastMessage('✅ Evento excluído!', 'success');
            if (calendar) calendar.refetchEvents();
        } else {
            showToastMessage('❌ Erro: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    } catch (error) {
        console.error('Erro:', error);
        showToastMessage('❌ Erro: ' + error.message, 'error');
    }
}

// ============================================
// EXPORTAR FUNÇÕES GLOBALMENTE
// ============================================
window.showSection = showSection;
window.showCurso = showCurso;
window.likePost = likePost;
window.toggleComments = toggleComments;
window.addComment = addComment;
window.deleteComment = deleteComment;
window.deletePost = deletePost;
window.openCreatePostModal = openCreatePostModal;
window.closeCreatePostModal = closeCreatePostModal;
window.createPost = createPost;
window.carregarTodasInteracoes = carregarTodasInteracoes;
window.carregarHistoricoChat = carregarHistoricoChat;
window.limparHistoricoChat = limparHistoricoChat;
window.showPerfilTab = showPerfilTab;
window.selectColor = selectColor;
window.toggleAlertaMinutos = toggleAlertaMinutos;
window.openEventModal = openEventModal;
window.closeEventModal = closeEventModal;
window.createEvent = createEvent;
window.excluirEvento = excluirEvento;
window.showToastMessage = showToastMessage;
window.toggleDarkMode = toggleDarkMode;
window.toggleNotificacoes = toggleNotificacoes;
window.marcarTodasLidas = marcarTodasLidas;
window.filtrarPosts = filtrarPosts;
window.exportarNotas = exportarNotas;

// ============================================
// 🆕 SISTEMA DE SINCRONIZAÇÃO COM CARDS NO TOPO
// ============================================

/* ============================================ */
/* FUNÇÕES DO MODAL DE SINCRONIZAÇÃO */
/* ============================================ */

function abrirModalSync(tipo) {
    const modal = document.getElementById('modalSync');
    const modalAVA = document.getElementById('modalSyncAVA');
    const modalLyceum = document.getElementById('modalSyncLyceum');

    if (tipo === 'ava') {
        modalAVA.style.display = 'block';
        modalLyceum.style.display = 'none';
        buscarStatus(); // Atualiza status AVA no modal
    } else if (tipo === 'lyceum') {
        modalAVA.style.display = 'none';
        modalLyceum.style.display = 'block';
        buscarStatusLyceum(); // Atualiza status Lyceum no modal
    }

    modal.style.display = 'block';
}

function fecharModalSync() {
    const modal = document.getElementById('modalSync');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Exporta funções do modal
window.abrirModalSync = abrirModalSync;
window.fecharModalSync = fecharModalSync;

/* ============================================ */
/* SISTEMA DE SINCRONIZAÇÃO AVA - V5.1 */
/* ============================================ */

let pollingInterval = null;
let lastSyncStatus = null;

function calcularTempoDecorrido(ultimaSync) {
    if (!ultimaSync) return '';

    try {
        const agora = new Date();
        const dataSync = new Date(ultimaSync);
        const diffMs = agora - dataSync;

        const minutos = Math.floor(diffMs / 60000);
        const horas = Math.floor(diffMs / 3600000);
        const dias = Math.floor(diffMs / 86400000);

        if (minutos < 1) return '⏱️ Agora mesmo';
        if (minutos === 1) return '⏱️ 1 minuto atrás';
        if (minutos < 60) return `⏱️ ${minutos} minutos atrás`;
        if (horas === 1) return '🕐 1 hora atrás';
        if (horas < 24) return `🕐 ${horas} horas atrás`;
        if (dias === 1) return '📅 1 dia atrás';
        return `📅 ${dias} dias atrás`;
    } catch (e) {
        console.error('Erro ao calcular tempo:', e);
        return '';
    }
}

function atualizarCardMiniAVA(data) {
    const card = document.getElementById('syncCardMiniAVA');
    const statusEl = document.getElementById('statusMiniAVA');

    if (!card || !statusEl) return;

    card.classList.remove('status-sincronizado', 'status-nunca', 'status-sincronizando');

    if (data.sincronizando) {
        card.classList.add('status-sincronizando', 'syncing');
        statusEl.innerHTML = '<span class="sync-loading-mini">Sincronizando...</span>';
    } else if (data.tem_dados && data.ultima_sync_formatada) {
        card.classList.add('status-sincronizado');
        statusEl.innerHTML = `
            <div>✅ Sincronizado</div>
            <span class="sync-card-mini-time">${data.ultima_sync_formatada}</span>
        `;
    } else {
        card.classList.add('status-nunca');
        statusEl.innerHTML = '<div>⚠️ Não sincronizado</div>';
    }
}

function atualizarModalAVA(data) {
    const modal = document.getElementById('modalSyncAVA');
    if (!modal || modal.style.display === 'none') return;

    const statusTitle = document.getElementById('statusTitleAVAModal');
    const statusText = document.getElementById('statusTextAVAModal');
    const syncBtn = document.getElementById('syncBtnAVAModal');
    const syncBtnText = document.getElementById('syncBtnTextAVAModal');
    const progressContainer = document.getElementById('syncProgressContainerAVAModal');

    if (!statusTitle || !statusText || !syncBtn) return;

    if (data.sincronizando) {
        statusTitle.textContent = '⏳ Sincronização em andamento';
        statusText.textContent = 'Baixando materiais do AVA... Isso pode levar 5-8 minutos.';
        syncBtn.disabled = true;
        syncBtnText.textContent = 'Sincronizando...';
        if (progressContainer) progressContainer.style.display = 'block';
    } else if (data.tem_dados && data.ultima_sync_formatada) {
        statusTitle.textContent = '✅ Dados sincronizados';
        const tempoDecorrido = calcularTempoDecorrido(data.ultima_sync);
        statusText.innerHTML = `Última sincronização: <strong>${data.ultima_sync_formatada}</strong><br><small>${tempoDecorrido}</small>`;
        syncBtn.disabled = false;
        syncBtnText.textContent = 'Sincronizar Novamente';
        if (progressContainer) progressContainer.style.display = 'none';
    } else {
        statusTitle.textContent = '⚠️ Primeira sincronização necessária';
        statusText.textContent = 'Clique no botão abaixo para baixar os materiais do AVA.';
        syncBtn.disabled = false;
        syncBtnText.textContent = 'Sincronizar Agora';
        if (progressContainer) progressContainer.style.display = 'none';
    }
}

async function buscarStatus() {
    try {
        const response = await fetch('/api/status_sync');

        if (!response.ok) {
            throw new Error('Erro ao buscar status');
        }

        const data = await response.json();

        // Detecta quando a sincronização terminou (estava sincronizando e agora não está mais)
        if (lastSyncStatus && lastSyncStatus.sincronizando && !data.sincronizando) {
            console.log('[SYNC AVA] Sincronização concluída! Recarregando página...');

            // Para o polling antes de recarregar
            pararPolling();

            // Mostra mensagem e recarrega
            showToastMessage('✅ Sincronização AVA concluída! Atualizando página...', 'success');

            setTimeout(() => {
                location.reload();
            }, 2000); // 2 segundos para o usuário ver a mensagem

            return; // Sai da função
        }

        // Atualiza CARD MINI
        atualizarCardMiniAVA(data);

        // Atualiza MODAL (se estiver aberto)
        atualizarModalAVA(data);

        // Controla polling
        if (data.sincronizando && !pollingInterval) {
            iniciarPolling();
        } else if (!data.sincronizando && pollingInterval) {
            pararPolling();
        }

        lastSyncStatus = data;

    } catch (error) {
        console.error('Erro ao buscar status AVA:', error);
        const statusEl = document.getElementById('statusMiniAVA');
        if (statusEl) {
            statusEl.innerHTML = '<div>❌ Erro</div>';
        }
    }
}

async function iniciarSincronizacao() {
    try {
        const response = await fetch('/api/sincronizar_ava', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.status === 'iniciado') {
            atualizarCardMiniAVA({
                sincronizando: true,
                tem_dados: false
            });

            atualizarModalAVA({
                sincronizando: true,
                tem_dados: false
            });

            iniciarPolling();

            showToastMessage('✅ Sincronização AVA iniciada!', 'success');

            console.log('[SYNC AVA] Sincronização iniciada. Tempo estimado: 5-8 minutos');

        } else if (data.status === 'em_andamento') {
            showToastMessage('⏳ Sincronização já está em andamento!', 'info');
        } else if (data.erro) {
            showToastMessage('❌ Erro: ' + data.erro, 'error');
            console.error('[SYNC AVA] Erro ao iniciar:', data.erro);
        }

    } catch (error) {
        console.error('[SYNC AVA] Erro ao iniciar sincronização:', error);
        showToastMessage('❌ Erro ao iniciar sincronização AVA', 'error');
    }
}

function iniciarPolling() {
    if (pollingInterval) return;

    console.log('[SYNC AVA] Polling iniciado (intervalo: 5s)');

    pollingInterval = setInterval(() => {
        buscarStatus();
    }, 5000);
}

function pararPolling() {
    if (pollingInterval) {
        console.log('[SYNC AVA] Polling parado');
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

window.buscarStatus = buscarStatus;
window.iniciarSincronizacao = iniciarSincronizacao;

/* ============================================ */
/* SISTEMA DE SINCRONIZAÇÃO LYCEUM - V5.1 */
/* ============================================ */

let pollingIntervalLyceum = null;
let lastSyncStatusLyceum = null;

function atualizarCardMiniLyceum(data) {
    const card = document.getElementById('syncCardMiniLyceum');
    const statusEl = document.getElementById('statusMiniLyceum');

    if (!card || !statusEl) return;

    card.classList.remove('status-sincronizado', 'status-nunca', 'status-sincronizando');

    if (data.sincronizando) {
        card.classList.add('status-sincronizando', 'syncing');
        statusEl.innerHTML = '<span class="sync-loading-mini">Sincronizando...</span>';
    } else if (data.tem_dados && data.ultima_sync_formatada) {
        card.classList.add('status-sincronizado');
        statusEl.innerHTML = `
            <div>✅ Sincronizado</div>
            <span class="sync-card-mini-time">${data.ultima_sync_formatada}</span>
        `;
    } else {
        card.classList.add('status-nunca');
        statusEl.innerHTML = '<div>⚠️ Não sincronizado</div>';
    }
}

function atualizarModalLyceum(data) {
    const modal = document.getElementById('modalSyncLyceum');
    if (!modal || modal.style.display === 'none') return;

    const statusTitle = document.getElementById('statusTitleLyceumModal');
    const statusText = document.getElementById('statusTextLyceumModal');
    const syncBtn = document.getElementById('syncBtnLyceumModal');
    const syncBtnText = document.getElementById('syncBtnTextLyceumModal');
    const progressContainer = document.getElementById('syncProgressContainerLyceumModal');

    if (!statusTitle || !statusText || !syncBtn) return;

    if (data.sincronizando) {
        statusTitle.textContent = '⏳ Sincronização em andamento';
        statusText.textContent = 'Baixando notas e faltas do Lyceum... Isso pode levar 2-3 minutos.';
        syncBtn.disabled = true;
        syncBtnText.textContent = 'Sincronizando...';
        if (progressContainer) progressContainer.style.display = 'block';
    } else if (data.tem_dados && data.ultima_sync_formatada) {
        statusTitle.textContent = '✅ Dados sincronizados';
        const tempoDecorrido = calcularTempoDecorrido(data.ultima_sync);
        statusText.innerHTML = `Última sincronização: <strong>${data.ultima_sync_formatada}</strong><br><small>${tempoDecorrido}</small>`;
        syncBtn.disabled = false;
        syncBtnText.textContent = 'Sincronizar Novamente';
        if (progressContainer) progressContainer.style.display = 'none';
    } else {
        statusTitle.textContent = '⚠️ Primeira sincronização necessária';
        statusText.innerHTML = 'Clique para baixar suas <strong>notas oficiais</strong> do Lyceum.<br><small>Usa 9 primeiros dígitos do CPF como senha</small>';
        syncBtn.disabled = false;
        syncBtnText.textContent = 'Sincronizar Agora';
        if (progressContainer) progressContainer.style.display = 'none';
    }
}

async function buscarStatusLyceum() {
    try {
        const response = await fetch('/api/status_sync_lyceum');

        if (!response.ok) {
            throw new Error('Erro ao buscar status Lyceum');
        }

        const data = await response.json();

        // Detecta quando a sincronização terminou (estava sincronizando e agora não está mais)
        if (lastSyncStatusLyceum && lastSyncStatusLyceum.sincronizando && !data.sincronizando) {
            console.log('[SYNC LYCEUM] Sincronização concluída! Recarregando página...');

            // Para o polling antes de recarregar
            pararPollingLyceum();

            // Mostra mensagem e recarrega
            showToastMessage('✅ Sincronização Lyceum concluída! Atualizando página...', 'success');

            setTimeout(() => {
                location.reload();
            }, 2000); // 2 segundos para o usuário ver a mensagem

            return; // Sai da função
        }

        // Atualiza CARD MINI
        atualizarCardMiniLyceum(data);

        // Atualiza MODAL (se estiver aberto)
        atualizarModalLyceum(data);

        // Controla polling
        if (data.sincronizando && !pollingIntervalLyceum) {
            iniciarPollingLyceum();
        } else if (!data.sincronizando && pollingIntervalLyceum) {
            pararPollingLyceum();
        }

        lastSyncStatusLyceum = data;

    } catch (error) {
        console.error('Erro ao buscar status Lyceum:', error);
        const statusEl = document.getElementById('statusMiniLyceum');
        if (statusEl) {
            statusEl.innerHTML = '<div>❌ Erro</div>';
        }
    }
}

async function iniciarSincronizacaoLyceum() {
    try {
        const response = await fetch('/api/sincronizar_lyceum', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.status === 'iniciado') {
            atualizarCardMiniLyceum({
                sincronizando: true,
                tem_dados: false
            });

            atualizarModalLyceum({
                sincronizando: true,
                tem_dados: false
            });

            iniciarPollingLyceum();

            showToastMessage('✅ Sincronização Lyceum iniciada!', 'success');

            console.log('[SYNC LYCEUM] Sincronização iniciada. Tempo estimado: 2-3 minutos');

        } else if (data.status === 'em_andamento') {
            showToastMessage('⏳ Sincronização já em andamento!', 'info');
        } else if (data.erro) {
            showToastMessage('❌ Erro: ' + data.erro, 'error');
            console.error('[SYNC LYCEUM] Erro ao iniciar:', data.erro);
        }

    } catch (error) {
        console.error('[SYNC LYCEUM] Erro ao iniciar sincronização:', error);
        showToastMessage('❌ Erro ao iniciar sincronização Lyceum', 'error');
    }
}

function iniciarPollingLyceum() {
    if (pollingIntervalLyceum) return;

    console.log('[SYNC LYCEUM] Polling iniciado (intervalo: 5s)');

    pollingIntervalLyceum = setInterval(() => {
        buscarStatusLyceum();
    }, 5000);
}

function pararPollingLyceum() {
    if (pollingIntervalLyceum) {
        console.log('[SYNC LYCEUM] Polling parado');
        clearInterval(pollingIntervalLyceum);
        pollingIntervalLyceum = null;
    }
}

window.buscarStatusLyceum = buscarStatusLyceum;
window.iniciarSincronizacaoLyceum = iniciarSincronizacaoLyceum;

/* ============================================ */
/* INICIALIZAÇÃO DOS SISTEMAS DE SINCRONIZAÇÃO */
/* ============================================ */

(function initSyncSystems() {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startSyncSystems);
    } else {
        startSyncSystems();
    }

    function startSyncSystems() {
        console.log('[SYNC] Sistemas de sincronização inicializados');

        // Busca status inicial
        buscarStatus();
        buscarStatusLyceum();

        // Polling lento (a cada 30 segundos quando não está sincronizando)
        setInterval(() => {
            if (!pollingInterval) buscarStatus();
            if (!pollingIntervalLyceum) buscarStatusLyceum();
        }, 30000);
    }
})();

// Limpa polling ao sair da página
window.addEventListener('beforeunload', function() {
    pararPolling();
    pararPollingLyceum();
});

// ============================================
// 🆕 SISTEMA DE ANEXOS E YOUTUBE NO CHAT
// ============================================

let currentAttachment = null; // Armazena arquivo ou link do YouTube
let attachmentType = null; // 'file' ou 'youtube'

/**
 * Toggle do menu de anexos
 */
function toggleAttachMenu() {
    const menu = document.getElementById('attachMenu');
    const isVisible = menu.style.display === 'block';

    // Fecha outros elementos
    const preview = document.getElementById('attachmentPreview');
    const youtubeContainer = document.getElementById('youtubeInputContainer');

    if (preview) preview.style.display = 'none';
    if (youtubeContainer) youtubeContainer.style.display = 'none';

    if (menu) {
        menu.style.display = isVisible ? 'none' : 'block';
    }
}

/**
 * Fecha o menu de anexos ao clicar fora
 */
document.addEventListener('click', function(event) {
    const attachBtn = document.querySelector('.btn-attach');
    const menu = document.getElementById('attachMenu');

    if (menu && attachBtn && !attachBtn.contains(event.target) && !menu.contains(event.target)) {
        menu.style.display = 'none';
    }
});

/**
 * Manipula seleção de arquivo
 */
function handleFileSelect(event) {
    const file = event.target.files[0];

    if (!file) return;

    // Validar tipo de arquivo
    const allowedTypes = ['application/pdf', 'application/msword',
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                          'text/plain'];

    if (!allowedTypes.includes(file.type)) {
        showToastMessage('⚠️ Tipo de arquivo não suportado. Use PDF, DOC, DOCX ou TXT', 'warning');
        return;
    }

    // ✅ SEM LIMITE DE TAMANHO - Aceita arquivos de qualquer tamanho

    // Armazenar arquivo
    currentAttachment = file;
    attachmentType = 'file';

    // Exibir preview
    showAttachmentPreview(file);

    // Fechar menu
    const menu = document.getElementById('attachMenu');
    if (menu) menu.style.display = 'none';

    // Limpar input
    event.target.value = '';

    // Mostrar notificação
    showToastMessage(`📄 Arquivo "${file.name}" selecionado (${formatFileSize(file.size)})`, 'success');
}

/**
 * Exibe preview do anexo
 */
function showAttachmentPreview(file) {
    const preview = document.getElementById('attachmentPreview');
    const icon = document.getElementById('attachmentIcon');
    const name = document.getElementById('attachmentName');
    const input = document.getElementById('chatInput');

    if (!preview || !icon || !name || !input) return;

    // Definir ícone baseado no tipo
    const extension = file.name.split('.').pop().toLowerCase();
    const iconMap = {
        'pdf': '📕',
        'doc': '📘',
        'docx': '📘',
        'txt': '📄'
    };

    icon.textContent = iconMap[extension] || '📄';
    name.textContent = file.name;

    preview.style.display = 'block';
    input.classList.add('has-attachment');
    input.placeholder = 'Pergunte algo sobre o documento...';
}

/**
 * Remove anexo
 */
function removeAttachment() {
    currentAttachment = null;
    attachmentType = null;

    const preview = document.getElementById('attachmentPreview');
    const input = document.getElementById('chatInput');

    if (preview) preview.style.display = 'none';
    if (input) {
        input.classList.remove('has-attachment', 'has-youtube');
        input.placeholder = 'Digite sua mensagem...';
    }
}

/**
 * Toggle input do YouTube
 */
function toggleYouTubeInput() {
    const container = document.getElementById('youtubeInputContainer');
    const menu = document.getElementById('attachMenu');

    if (container) container.style.display = 'flex';
    if (menu) menu.style.display = 'none';

    // Foca no input
    const ytInput = document.getElementById('youtubeLink');
    if (ytInput) ytInput.focus();
}

/**
 * Cancela input do YouTube
 */
function cancelYouTube() {
    const container = document.getElementById('youtubeInputContainer');
    const input = document.getElementById('youtubeLink');

    if (container) container.style.display = 'none';
    if (input) input.value = '';
}

/**
 * Carrega vídeo do YouTube
 */
async function loadYouTubeVideo() {
    const input = document.getElementById('youtubeLink');
    const url = input ? input.value.trim() : '';

    if (!url) {
        showToastMessage('⚠️ Cole o link do YouTube', 'warning');
        return;
    }

    // Validar URL do YouTube
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/;
    if (!youtubeRegex.test(url)) {
        showToastMessage('⚠️ Link do YouTube inválido', 'error');
        return;
    }

    // Extrair ID do vídeo
    let videoId = null;

    if (url.includes('youtube.com/watch?v=')) {
        videoId = url.split('v=')[1].split('&')[0];
    } else if (url.includes('youtu.be/')) {
        videoId = url.split('youtu.be/')[1].split('?')[0];
    }

    if (!videoId) {
        showToastMessage('⚠️ Não foi possível extrair o ID do vídeo', 'error');
        return;
    }

    // Armazenar dados do YouTube
    currentAttachment = {
        url: url,
        videoId: videoId,
        type: 'youtube'
    };
    attachmentType = 'youtube';

    // Exibir preview do YouTube
    showYouTubePreview(url, videoId);

    // Limpar e fechar
    if (input) input.value = '';
    const container = document.getElementById('youtubeInputContainer');
    if (container) container.style.display = 'none';
}

/**
 * Exibe preview do YouTube
 */
function showYouTubePreview(url, videoId) {
    const preview = document.getElementById('attachmentPreview');
    const icon = document.getElementById('attachmentIcon');
    const name = document.getElementById('attachmentName');
    const input = document.getElementById('chatInput');

    if (!preview || !icon || !name || !input) return;

    icon.textContent = '🎥';
    name.textContent = `YouTube: ${videoId}`;

    preview.style.display = 'block';
    input.classList.add('has-youtube');
    input.placeholder = 'Pergunte algo sobre o vídeo...';
}

/**
 * Adiciona preview de anexo na mensagem do usuário
 */
function addAttachmentToMessage(file) {
    const messagesContainer = document.getElementById('chatMessages');
    if (!messagesContainer) return;

    const lastMessage = messagesContainer.lastElementChild;

    if (lastMessage && lastMessage.classList.contains('user-message')) {
        const extension = file.name.split('.').pop().toLowerCase();
        const iconMap = {
            'pdf': '📕',
            'doc': '📘',
            'docx': '📘',
            'txt': '📄'
        };

        const attachmentDiv = document.createElement('div');
        attachmentDiv.className = 'message-attachment';
        attachmentDiv.innerHTML = `
            <div class="message-attachment-icon">${iconMap[extension] || '📄'}</div>
            <div class="message-attachment-info">
                <div class="message-attachment-name">${file.name}</div>
                <div class="message-attachment-type">${extension.toUpperCase()} • ${formatFileSize(file.size)}</div>
            </div>
        `;

        const messageContent = lastMessage.querySelector('.message-content');
        if (messageContent) {
            messageContent.appendChild(attachmentDiv);
        }
    }
}

/**
 * Adiciona preview do YouTube na mensagem do usuário
 */
function addYouTubeToMessage(youtubeData) {
    const messagesContainer = document.getElementById('chatMessages');
    if (!messagesContainer) return;

    const lastMessage = messagesContainer.lastElementChild;

    if (lastMessage && lastMessage.classList.contains('user-message')) {
        const attachmentDiv = document.createElement('div');
        attachmentDiv.className = 'message-attachment';
        attachmentDiv.innerHTML = `
            <div class="message-attachment-icon">🎥</div>
            <div class="message-attachment-info">
                <div class="message-attachment-name">Vídeo do YouTube</div>
                <div class="message-attachment-type">ID: ${youtubeData.videoId}</div>
            </div>
        `;

        const messageContent = lastMessage.querySelector('.message-content');
        if (messageContent) {
            messageContent.appendChild(attachmentDiv);
        }
    }
}

/**
 * Formata tamanho do arquivo
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Envia mensagem com arquivo
 */
async function sendMessageWithFile(message, file) {
    const formData = new FormData();
    formData.append('message', message);
    formData.append('file', file);

    return fetch('/chat/with-file', {
        method: 'POST',
        body: formData
    });
}

/**
 * Envia mensagem com YouTube
 */
async function sendMessageWithYouTube(message, youtubeData) {
    return fetch('/chat/with-youtube', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message: message,
            youtube_url: youtubeData.url,
            video_id: youtubeData.videoId
        })
    });
}

// Exportar funções globalmente
window.toggleAttachMenu = toggleAttachMenu;
window.handleFileSelect = handleFileSelect;
window.removeAttachment = removeAttachment;
window.toggleYouTubeInput = toggleYouTubeInput;
window.cancelYouTube = cancelYouTube;
window.loadYouTubeVideo = loadYouTubeVideo;

console.log('[SYNC] Sistema completo V5.1 carregado com sucesso!');
console.log('[LYCEUM] Senha: 9 primeiros dígitos do CPF');
console.log('[CHAT] Sistema de anexos e YouTube carregado!');
