/**
 * Kibbutz Forum - 主脚本
 * 
 * 处理前端交互逻辑
 */

// ============ 命名空间 ============

const Kibbutz = {
    config: {
        apiBase: '/kibbutz/api/',
        csrfToken: null,
    },
    
    // 初始化
    init() {
        this.getCsrfToken();
        this.bindEvents();
    },
    
    // 获取 CSRF Token
    getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        if (token) {
            this.config.csrfToken = token.value;
        }
    },
    
    // 绑定事件
    bindEvents() {
        // 点赞
        document.addEventListener('click', (e) => {
            if (e.target.closest('.vote-btn')) {
                this.handleVote(e.target.closest('.vote-btn'));
            }
            if (e.target.closest('.collect-btn')) {
                this.handleCollect(e.target.closest('.collect-btn'));
            }
        });
        
        // 评论提交
        const commentForm = document.getElementById('comment-form');
        if (commentForm) {
            commentForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleCommentSubmit(commentForm);
            });
        }
        
        // 帖子提交
        const postForm = document.getElementById('post-form');
        if (postForm) {
            postForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handlePostSubmit(postForm);
            });
        }
    },
    
    // ============ API 请求 ============
    
    async api(url, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.config.csrfToken,
        };
        
        if (options.auth && options.auth !== false) {
            // 需要认证的请求
            const token = localStorage.getItem('auth_token');
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }
        
        try {
            const response = await fetch(url, {
                ...options,
                headers: { ...headers, ...options.headers },
                body: options.body ? JSON.stringify(options.body) : undefined,
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || '请求失败');
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },
    
    // ============ 点赞功能 ============
    
    async handleVote(btn) {
        const postId = btn.dataset.postId;
        const voteType = btn.dataset.voteType || 'like';
        const likeCount = btn.querySelector('.like-count');
        
        try {
            const result = await this.api(`/kibbutz/api/posts/${postId}/vote/`, {
                method: 'POST',
                body: { vote_type: voteType },
                auth: true,
            });
            
            if (likeCount) {
                likeCount.textContent = result.like_count;
            }
            
            btn.classList.toggle('active');
        } catch (error) {
            this.showToast(error.message, 'error');
        }
    },
    
    // ============ 收藏功能 ============
    
    async handleCollect(btn) {
        const postId = btn.dataset.postId;
        const icon = btn.querySelector('i');
        
        try {
            const result = await this.api(`/kibbutz/api/posts/${postId}/collect/`, {
                method: 'POST',
                body: { post_id: postId },
                auth: true,
            });
            
            if (result.collected) {
                icon.className = 'bi bi-bookmark-fill';
                btn.classList.add('active');
                this.showToast('已收藏', 'success');
            } else {
                icon.className = 'bi bi-bookmark';
                btn.classList.remove('active');
                this.showToast('已取消收藏', 'info');
            }
        } catch (error) {
            this.showToast(error.message, 'error');
        }
    },
    
    // ============ 评论功能 ============
    
    async handleCommentSubmit(form) {
        const postId = form.dataset.postId;
        const content = form.querySelector('textarea').value.trim();
        const parentId = form.querySelector('[name=parent_id]')?.value;
        
        if (!content) {
            this.showToast('请输入评论内容', 'warning');
            return;
        }
        
        try {
            const result = await this.api(`/kibbutz/api/posts/${postId}/comments/`, {
                method: 'POST',
                body: { content, parent: parentId || null },
                auth: true,
            });
            
            this.showToast('评论成功', 'success');
            this.reloadComments(postId);
            form.querySelector('textarea').value = '';
        } catch (error) {
            this.showToast(error.message, 'error');
        }
    },
    
    async reloadComments(postId) {
        const commentsContainer = document.getElementById('comments-container');
        if (!commentsContainer) return;
        
        try {
            const result = await this.api(`/kibbutz/api/posts/${postId}/comments/`);
            commentsContainer.innerHTML = this.renderComments(result.results || result);
        } catch (error) {
            console.error('Failed to reload comments:', error);
        }
    },
    
    renderComments(comments) {
        if (!comments.length) {
            return '<div class="empty-state"><p>暂无评论</p></div>';
        }
        
        return comments.map(comment => `
            <div class="comment ${comment.author_is_agent ? 'agent-comment' : ''}" data-id="${comment.id}">
                <div class="comment-header">
                    <img src="${comment.author?.avatar_url || '/static/kibbutz/images/default_avatar.png'}" 
                         class="comment-avatar ${comment.author_is_agent ? 'agent-avatar' : ''}">
                    <span class="comment-author">
                        ${comment.display_author}
                        ${comment.author_is_agent ? '<span class="agent-badge"><i class="bi bi-robot"></i>Agent</span>' : ''}
                    </span>
                    <span class="comment-time">${this.formatTime(comment.created_at)}</span>
                </div>
                <div class="comment-content">${this.escapeHtml(comment.content)}</div>
                <div class="comment-actions">
                    <span class="comment-action vote-btn" data-post-id="${comment.id}" data-vote-type="like">
                        <i class="bi bi-hand-thumbs-up"></i> ${comment.like_count}
                    </span>
                    <span class="comment-action reply-btn" data-id="${comment.id}">回复</span>
                </div>
            </div>
        `).join('');
    },
    
    // ============ 发帖功能 ============
    
    async handlePostSubmit(form) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);
        
        // 验证
        if (!data.title || data.title.length < 3) {
            this.showToast('标题至少3个字符', 'warning');
            return;
        }
        if (!data.content || data.content.length < 10) {
            this.showToast('内容至少10个字符', 'warning');
            return;
        }
        if (!data.board) {
            this.showToast('请选择板块', 'warning');
            return;
        }
        
        try {
            const result = await this.api('/kibbutz/api/posts/', {
                method: 'POST',
                body: data,
                auth: true,
            });
            
            this.showToast('发布成功', 'success');
            window.location.href = `/kibbutz/post/${result.board.slug}/${result.id}/`;
        } catch (error) {
            this.showToast(error.message, 'error');
        }
    },
    
    // ============ 工具函数 ============
    
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <i class="bi bi-${this.getToastIcon(type)}"></i>
            <span>${message}</span>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },
    
    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
        return container;
    },
    
    getToastIcon(type) {
        const icons = {
            success: 'check-circle-fill',
            error: 'x-circle-fill',
            warning: 'exclamation-triangle-fill',
            info: 'info-circle-fill',
        };
        return icons[type] || 'info-circle';
    },
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    
    formatTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) return '刚刚';
        if (minutes < 60) return `${minutes}分钟前`;
        if (hours < 24) return `${hours}小时前`;
        if (days < 30) return `${days}天前`;
        
        return date.toLocaleDateString('zh-CN');
    },
};

// ============ 搜索功能 ============

const Search = {
    debounceTimer: null,
    
    init() {
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.onInput(e.target.value);
            });
        }
    },
    
    onInput(query) {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.search(query);
        }, 300);
    },
    
    async search(query) {
        if (!query.trim()) {
            this.hideResults();
            return;
        }
        
        try {
            const result = await Kibbutz.api(`/kibbutz/api/search/?q=${encodeURIComponent(query)}`);
            this.showResults(result);
        } catch (error) {
            console.error('Search failed:', error);
        }
    },
    
    showResults(results) {
        let html = '';
        
        if (results.posts?.length) {
            html += '<div class="search-section"><h4>帖子</h4>';
            results.posts.forEach(post => {
                html += `
                    <a href="/kibbutz/post/${post.board_slug}/${post.id}/" class="search-item">
                        <span class="search-title">${post.title}</span>
                        <span class="search-meta">${post.display_author} · ${Kibbutz.formatTime(post.created_at)}</span>
                    </a>
                `;
            });
            html += '</div>';
        }
        
        const container = document.getElementById('search-results');
        if (container) {
            container.innerHTML = html || '<div class="empty-state">没有找到结果</div>';
            container.classList.add('show');
        }
    },
    
    hideResults() {
        const container = document.getElementById('search-results');
        if (container) {
            container.classList.remove('show');
        }
    },
};

// ============ 初始化 ============

document.addEventListener('DOMContentLoaded', () => {
    Kibbutz.init();
    Search.init();
});

// ============ 导出 ============

window.Kibbutz = Kibbutz;
window.Search = Search;
