/**
 * Neshama Workshop - JavaScript 模块
 * 工匠认证技能市场
 */

(function() {
    'use strict';

    // ===================================
    // 工具函数
    // ===================================

    /**
     * 获取 Cookie 值
     */
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    /**
     * 显示 Toast 消息
     */
    function showToast(message, type = 'info') {
        // 移除已存在的 toast
        const existingToast = document.querySelector('.toast');
        if (existingToast) {
            existingToast.remove();
        }

        // 创建新 toast
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);

        // 显示动画
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });

        // 自动隐藏
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    /**
     * 防抖函数
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * API 请求封装
     */
    async function apiRequest(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        const response = await fetch(url, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.message || `HTTP ${response.status}`);
        }

        return response.json();
    }

    // ===================================
    // 组件初始化
    // ===================================

    /**
     * 初始化搜索功能
     */
    function initSearch() {
        const searchInputs = document.querySelectorAll('.search-input');
        
        searchInputs.forEach(input => {
            const handleSearch = debounce(async function() {
                const query = this.value.trim();
                if (query.length < 2) return;

                // 显示搜索建议
                try {
                    const results = await apiRequest(`/workshop/api/skills/?search=${encodeURIComponent(query)}&page_size=5`);
                    showSearchSuggestions(this, results.results);
                } catch (error) {
                    console.error('Search error:', error);
                }
            }, 300);

            input.addEventListener('input', handleSearch);
            input.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    window.location.href = `/workshop/?search=${encodeURIComponent(this.value)}`;
                }
            });
        });
    }

    /**
     * 显示搜索建议
     */
    function showSearchSuggestions(input, results) {
        // 移除旧的建议列表
        const existingList = document.querySelector('.search-suggestions');
        if (existingList) {
            existingList.remove();
        }

        if (!results || results.length === 0) return;

        const suggestions = document.createElement('div');
        suggestions.className = 'search-suggestions';
        suggestions.innerHTML = results.map(skill => `
            <a href="/workshop/skill/${skill.slug}/" class="suggestion-item">
                <img src="${skill.icon || '/static/workshop/img/default-skill.png'}" alt="" class="suggestion-icon">
                <div class="suggestion-info">
                    <span class="suggestion-name">${skill.name}</span>
                    <span class="suggestion-desc">${skill.short_description}</span>
                </div>
            </a>
        `).join('');

        input.parentElement.appendChild(suggestions);
    }

    /**
     * 初始化评分功能
     */
    function initRating() {
        const starBtns = document.querySelectorAll('.star-btn');
        const ratingInput = document.getElementById('rating-value');

        starBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const rating = this.dataset.rating;
                if (ratingInput) {
                    ratingInput.value = rating;
                }
                starBtns.forEach((b, i) => {
                    b.classList.toggle('selected', i < rating);
                });
            });

            btn.addEventListener('mouseenter', function() {
                const rating = this.dataset.rating;
                starBtns.forEach((b, i) => {
                    b.classList.toggle('hover', i < rating);
                });
            });

            btn.addEventListener('mouseleave', function() {
                starBtns.forEach(b => b.classList.remove('hover'));
            });
        });
    }

    /**
     * 初始化评价表单
     */
    function initReviewForm() {
        const reviewForm = document.getElementById('review-form');
        if (!reviewForm) return;

        reviewForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const slug = window.location.pathname.match(/\/skill\/([^/]+)\//)?.[1];

            if (!slug) return;

            try {
                const response = await apiRequest(`/workshop/api/skills/${slug}/rate/`, {
                    method: 'POST',
                    body: JSON.stringify(Object.fromEntries(formData))
                });

                showToast('评价提交成功');
                document.getElementById('review-modal')?.classList.remove('active');
                setTimeout(() => location.reload(), 1000);
            } catch (error) {
                showToast(error.message || '提交失败', 'error');
            }
        });
    }

    /**
     * 初始化安装功能
     */
    function initInstall() {
        const installBtn = document.getElementById('install-btn');
        const uninstallBtn = document.getElementById('uninstall-btn');

        if (installBtn) {
            installBtn.addEventListener('click', async function() {
                const slug = this.dataset.skillSlug;
                this.disabled = true;
                this.textContent = '安装中...';

                try {
                    const result = await apiRequest(`/workshop/api/skills/${slug}/install/`, {
                        method: 'POST'
                    });

                    showToast(result.message || '安装成功');
                    setTimeout(() => location.reload(), 1000);
                } catch (error) {
                    showToast(error.message || '安装失败', 'error');
                    this.disabled = false;
                    this.textContent = '立即安装';
                }
            });
        }

        if (uninstallBtn) {
            uninstallBtn.addEventListener('click', async function() {
                const slug = this.dataset.skillSlug || window.location.pathname.match(/\/skill\/([^/]+)\//)?.[1];
                if (!slug) return;

                try {
                    const result = await apiRequest(`/workshop/api/skills/${slug}/uninstall/`, {
                        method: 'POST'
                    });

                    showToast(result.message || '卸载成功');
                    setTimeout(() => location.reload(), 1000);
                } catch (error) {
                    showToast(error.message || '卸载失败', 'error');
                }
            });
        }
    }

    /**
     * 初始化收藏功能
     */
    function initFavorite() {
        const favoriteBtn = document.getElementById('favorite-btn');
        if (!favoriteBtn) return;

        favoriteBtn.addEventListener('click', async function() {
            const slug = window.location.pathname.match(/\/skill\/([^/]+)\//)?.[1];
            if (!slug) return;

            try {
                const result = await apiRequest(`/workshop/api/skills/${slug}/favorite/`, {
                    method: 'POST'
                });

                this.textContent = result.status === 'favorited' ? '取消收藏' : '收藏';
                showToast(result.message);
            } catch (error) {
                showToast(error.message || '操作失败', 'error');
            }
        });
    }

    /**
     * 初始化有帮助按钮
     */
    function initHelpful() {
        document.querySelectorAll('.helpful-btn').forEach(btn => {
            btn.addEventListener('click', async function() {
                const reviewId = this.dataset.reviewId;
                if (!reviewId) return;

                try {
                    const result = await apiRequest(`/workshop/api/ratings/${reviewId}/helpful/`, {
                        method: 'POST'
                    });

                    this.innerHTML = `👍 有帮助 (${result.helpful_count})`;
                    this.disabled = true;
                } catch (error) {
                    showToast(error.message || '操作失败', 'error');
                }
            });
        });
    }

    /**
     * 初始化模态框
     */
    function initModals() {
        document.querySelectorAll('[data-modal-target]').forEach(trigger => {
            trigger.addEventListener('click', function() {
                const modalId = this.dataset.modalTarget;
                const modal = document.getElementById(modalId);
                if (modal) {
                    modal.classList.add('active');
                }
            });
        });

        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', function(e) {
                if (e.target === this) {
                    this.classList.remove('active');
                }
            });
        });

        document.querySelectorAll('.modal-close').forEach(closeBtn => {
            closeBtn.addEventListener('click', function() {
                this.closest('.modal').classList.remove('active');
            });
        });
    }

    /**
     * 初始化预览图轮播
     */
    function initPreviewCarousel() {
        const carousel = document.querySelector('.preview-carousel');
        if (!carousel) return;

        // 简单实现，可根据需要扩展
        const items = carousel.querySelectorAll('.preview-item');
        if (items.length <= 1) return;

        // 添加左右切换按钮
        const prevBtn = document.createElement('button');
        prevBtn.className = 'carousel-btn prev';
        prevBtn.innerHTML = '‹';

        const nextBtn = document.createElement('button');
        nextBtn.className = 'carousel-btn next';
        nextBtn.innerHTML = '›';

        carousel.appendChild(prevBtn);
        carousel.appendChild(nextBtn);

        let currentIndex = 0;

        function showSlide(index) {
            items.forEach((item, i) => {
                item.style.display = i === index ? 'block' : 'none';
            });
        }

        prevBtn.addEventListener('click', () => {
            currentIndex = (currentIndex - 1 + items.length) % items.length;
            showSlide(currentIndex);
        });

        nextBtn.addEventListener('click', () => {
            currentIndex = (currentIndex + 1) % items.length;
            showSlide(currentIndex);
        });

        showSlide(currentIndex);
    }

    /**
     * 初始化技能卡片交互
     */
    function initSkillCards() {
        document.querySelectorAll('.skill-card').forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-4px)';
            });

            card.addEventListener('mouseleave', function() {
                this.style.transform = '';
            });
        });
    }

    /**
     * 初始化分类筛选
     */
    function initCategoryFilter() {
        const filterBtns = document.querySelectorAll('.category-filter-btn');
        filterBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const category = this.dataset.category;
                
                filterBtns.forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                // 触发筛选更新
                const event = new CustomEvent('categoryFilter', { 
                    detail: { category } 
                });
                document.dispatchEvent(event);
            });
        });
    }

    /**
     * 初始化无限滚动
     */
    function initInfiniteScroll() {
        const loadMoreBtn = document.getElementById('load-more-btn');
        if (!loadMoreBtn) return;

        loadMoreBtn.addEventListener('click', async function() {
            const nextUrl = this.dataset.nextUrl;
            if (!nextUrl) return;

            this.disabled = true;
            this.textContent = '加载中...';

            try {
                const response = await fetch(nextUrl);
                const data = await response.json();

                // 触发自定义事件以添加新内容
                const event = new CustomEvent('loadMoreResults', { 
                    detail: { results: data.results, next: data.next }
                });
                document.dispatchEvent(event);

                if (data.next) {
                    this.dataset.nextUrl = data.next;
                    this.disabled = false;
                    this.textContent = '加载更多';
                } else {
                    this.style.display = 'none';
                }
            } catch (error) {
                showToast('加载失败', 'error');
                this.disabled = false;
                this.textContent = '加载更多';
            }
        });
    }

    // ===================================
    // 初始化入口
    // ===================================

    function init() {
        initSearch();
        initRating();
        initReviewForm();
        initInstall();
        initFavorite();
        initHelpful();
        initModals();
        initPreviewCarousel();
        initSkillCards();
        initCategoryFilter();
        initInfiniteScroll();
    }

    // DOM 加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // 导出公共 API
    window.WorkshopApp = {
        showToast,
        apiRequest,
        getCookie
    };

})();
