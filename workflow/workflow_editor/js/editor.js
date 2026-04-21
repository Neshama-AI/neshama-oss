/**
 * Neshama Workflow Editor
 * Main editor logic and initialization
 */

class WorkflowEditor {
    constructor() {
        this.canvas = null;
        this.storage = new WorkflowStorage();
        this.currentWorkflow = this.createEmptyWorkflow();
        this.selectedNode = null;
        this.clipboard = null;
        this.history = [];
        this.historyIndex = -1;
        this.maxHistory = 50;
        
        this.init();
    }
    
    init() {
        // Initialize canvas
        this.canvas = new Canvas({
            onNodeSelect: (node) => this.onNodeSelect(node),
            onNodeDelete: (nodeId) => this.onNodeDelete(nodeId),
            onConnectionCreate: (from, to) => this.onConnectionCreate(from, to),
            onCanvasChange: () => this.saveToHistory()
        });
        
        // Bind events
        this.bindToolbarEvents();
        this.bindNodePaletteEvents();
        this.bindContextMenu();
        this.bindKeyboardShortcuts();
        this.bindModalEvents();
        this.bindFileEvents();
        
        // Load saved workflow or create new
        this.loadOrCreate();
        
        // Load templates
        this.loadTemplates();
        
        console.log('Neshama Workflow Editor initialized');
    }
    
    createEmptyWorkflow() {
        return {
            id: this.generateId(),
            name: '未命名工作流',
            version: '1.0.0',
            trigger: {
                type: 'schedule',
                cron: '0 8 * * *'
            },
            nodes: [],
            edges: []
        };
    }
    
    generateId() {
        return 'wf_' + Math.random().toString(36).substr(2, 8);
    }
    
    loadOrCreate() {
        const saved = this.storage.loadCurrent();
        if (saved) {
            this.currentWorkflow = saved;
            document.getElementById('workflowName').value = saved.name;
            this.renderWorkflow();
            this.showToast('已加载保存的工作流', 'success');
        }
    }
    
    // ============ Toolbar Events ============
    
    bindToolbarEvents() {
        // Save
        document.getElementById('btnSave').addEventListener('click', () => this.saveWorkflow());
        
        // Run
        document.getElementById('btnRun').addEventListener('click', () => this.runWorkflow());
        
        // Export
        document.getElementById('btnExport').addEventListener('click', () => this.exportWorkflow());
        
        // Import
        document.getElementById('btnImport').addEventListener('click', () => {
            document.getElementById('fileImport').click();
        });
        
        // Templates
        document.getElementById('btnTemplates').addEventListener('click', () => {
            this.showModal('modalTemplates');
        });
        
        // Zoom controls
        document.getElementById('btnZoomIn').addEventListener('click', () => this.canvas.zoomIn());
        document.getElementById('btnZoomOut').addEventListener('click', () => this.canvas.zoomOut());
        document.getElementById('btnZoomReset').addEventListener('click', () => this.canvas.zoomReset());
        document.getElementById('btnFitView').addEventListener('click', () => this.canvas.fitView());
        
        // Undo/Redo
        document.getElementById('btnUndo').addEventListener('click', () => this.undo());
        document.getElementById('btnRedo').addEventListener('click', () => this.redo());
        
        // Workflow name change
        document.getElementById('workflowName').addEventListener('change', (e) => {
            this.currentWorkflow.name = e.target.value;
            this.autoSave();
        });
        
        // Close properties panel
        document.getElementById('btnCloseProperties').addEventListener('click', () => {
            this.hidePropertiesPanel();
        });
    }
    
    // ============ Node Palette Events ============
    
    bindNodePaletteEvents() {
        const nodeItems = document.querySelectorAll('.node-item');
        
        nodeItems.forEach(item => {
            item.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('nodeType', item.dataset.type);
                e.dataTransfer.setData('nodeSubtype', item.dataset.subtype);
            });
        });
        
        // Canvas drop zone
        const canvas = document.getElementById('canvas');
        
        canvas.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
        });
        
        canvas.addEventListener('drop', (e) => {
            e.preventDefault();
            const nodeType = e.dataTransfer.getData('nodeType');
            const nodeSubtype = e.dataTransfer.getData('nodeSubtype');
            
            if (nodeType && nodeSubtype) {
                const rect = canvas.getBoundingClientRect();
                const x = (e.clientX - rect.left) / this.canvas.scale - this.canvas.offsetX;
                const y = (e.clientY - rect.top) / this.canvas.scale - this.canvas.offsetY;
                
                this.addNode(nodeType, nodeSubtype, x, y);
            }
        });
    }
    
    // ============ Node Management ============
    
    addNode(type, subtype, x, y) {
        const nodeId = 'node_' + this.generateId();
        
        const nodeConfig = this.getNodeConfig(type, subtype);
        
        const node = {
            id: nodeId,
            type: type,
            subtype: subtype,
            name: nodeConfig.name,
            description: nodeConfig.description,
            x: Math.round(x / 20) * 20,  // Snap to grid
            y: Math.round(y / 20) * 20,
            config: nodeConfig.defaultConfig
        };
        
        this.currentWorkflow.nodes.push(node);
        this.canvas.addNode(node);
        this.autoSave();
        this.saveToHistory();
        
        return node;
    }
    
    getNodeConfig(type, subtype) {
        const configs = {
            trigger: {
                schedule: {
                    name: '定时触发',
                    description: '按 Cron 表达式触发',
                    defaultConfig: { cron: '0 8 * * *', timezone: 'Asia/Shanghai' }
                },
                event: {
                    name: '事件触发',
                    description: '当事件发生时触发',
                    defaultConfig: { event: '', source: 'any' }
                },
                webhook: {
                    name: 'Webhook',
                    description: '接收 HTTP 请求触发',
                    defaultConfig: { path: '/webhook', method: 'POST' }
                }
            },
            action: {
                send_message: {
                    name: '发送消息',
                    description: '发送消息到指定渠道',
                    defaultConfig: { channel: 'default', template: '' }
                },
                call_skill: {
                    name: '调用技能',
                    description: '调用已安装的技能',
                    defaultConfig: { skill: '', params: {} }
                },
                get_info: {
                    name: '获取信息',
                    description: '从外部获取信息',
                    defaultConfig: { source: 'weather', params: {} }
                },
                generate: {
                    name: '生成内容',
                    description: '使用 AI 生成内容',
                    defaultConfig: { prompt: '', model: 'default' }
                },
                api: {
                    name: '调用 API',
                    description: '调用外部 HTTP API',
                    defaultConfig: { url: '', method: 'GET', headers: {}, body: '' }
                }
            },
            condition: {
                if: {
                    name: 'IF 分支',
                    description: '根据条件进行分支',
                    defaultConfig: { field: '', operator: 'eq', value: '' }
                },
                loop: {
                    name: '循环',
                    description: '循环执行一组节点',
                    defaultConfig: { items: '', times: 1 }
                },
                delay: {
                    name: '延时',
                    description: '等待指定时间后继续',
                    defaultConfig: { seconds: 5 }
                }
            },
            transform: {
                assign: {
                    name: '变量赋值',
                    description: '设置或修改变量',
                    defaultConfig: { variable: '', value: '' }
                },
                format: {
                    name: '格式转换',
                    description: '转换数据格式',
                    defaultConfig: { input: '', outputFormat: 'text' }
                },
                extract: {
                    name: '数据提取',
                    description: '从数据中提取字段',
                    defaultConfig: { source: '', pattern: '' }
                }
            }
        };
        
        return configs[type]?.[subtype] || {
            name: '未知节点',
            description: '',
            defaultConfig: {}
        };
    }
    
    onNodeSelect(node) {
        this.selectedNode = node;
        this.showPropertiesPanel(node);
    }
    
    onNodeDelete(nodeId) {
        // Remove node
        this.currentWorkflow.nodes = this.currentWorkflow.nodes.filter(n => n.id !== nodeId);
        
        // Remove related edges
        this.currentWorkflow.edges = this.currentWorkflow.edges.filter(
            e => e.from !== nodeId && e.to !== nodeId
        );
        
        this.canvas.removeNode(nodeId);
        this.hidePropertiesPanel();
        this.autoSave();
        this.saveToHistory();
    }
    
    onConnectionCreate(fromNodeId, toNodeId) {
        // Check if connection already exists
        const exists = this.currentWorkflow.edges.some(
            e => e.from === fromNodeId && e.to === toNodeId
        );
        
        if (!exists && fromNodeId !== toNodeId) {
            this.currentWorkflow.edges.push({
                from: fromNodeId,
                to: toNodeId,
                label: ''
            });
            this.autoSave();
            this.saveToHistory();
        }
    }
    
    // ============ Properties Panel ============
    
    showPropertiesPanel(node) {
        const panel = document.getElementById('propertiesPanel');
        const content = document.getElementById('propertiesContent');
        
        // Build properties form based on node type
        content.innerHTML = this.buildPropertiesForm(node);
        
        // Bind form events
        this.bindPropertyFormEvents(node);
        
        panel.classList.add('open');
    }
    
    hidePropertiesPanel() {
        const panel = document.getElementById('propertiesPanel');
        panel.classList.remove('open');
        this.selectedNode = null;
        this.canvas.deselectAll();
    }
    
    buildPropertiesForm(node) {
        let html = `
            <div class="form-group">
                <label class="form-label">节点名称</label>
                <input type="text" class="form-input" id="propName" value="${node.name}">
            </div>
        `;
        
        // Add specific config fields based on node type
        if (node.type === 'trigger') {
            if (node.subtype === 'schedule') {
                html += `
                    <div class="form-group">
                        <label class="form-label">Cron 表达式</label>
                        <input type="text" class="form-input" id="propCron" value="${node.config.cron || ''}">
                        <p class="form-hint">格式: 分 时 日 月 周 (例如: 0 8 * * *)</p>
                    </div>
                    <div class="form-group">
                        <label class="form-label">时区</label>
                        <select class="form-select" id="propTimezone">
                            <option value="Asia/Shanghai" ${node.config.timezone === 'Asia/Shanghai' ? 'selected' : ''}>中国 (Asia/Shanghai)</option>
                            <option value="UTC" ${node.config.timezone === 'UTC' ? 'selected' : ''}>UTC</option>
                            <option value="America/New_York" ${node.config.timezone === 'America/New_York' ? 'selected' : ''}>美国东部</option>
                        </select>
                    </div>
                `;
            } else if (node.subtype === 'event') {
                html += `
                    <div class="form-group">
                        <label class="form-label">事件名称</label>
                        <input type="text" class="form-input" id="propEvent" value="${node.config.event || ''}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">事件来源</label>
                        <select class="form-select" id="propSource">
                            <option value="any" ${node.config.source === 'any' ? 'selected' : ''}>任意来源</option>
                            <option value="user" ${node.config.source === 'user' ? 'selected' : ''}>用户</option>
                            <option value="system" ${node.config.source === 'system' ? 'selected' : ''}>系统</option>
                        </select>
                    </div>
                `;
            } else if (node.subtype === 'webhook') {
                html += `
                    <div class="form-group">
                        <label class="form-label">路径</label>
                        <input type="text" class="form-input" id="propPath" value="${node.config.path || ''}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">HTTP 方法</label>
                        <select class="form-select" id="propMethod">
                            <option value="POST" ${node.config.method === 'POST' ? 'selected' : ''}>POST</option>
                            <option value="GET" ${node.config.method === 'GET' ? 'selected' : ''}>GET</option>
                        </select>
                    </div>
                `;
            }
        } else if (node.type === 'action') {
            if (node.subtype === 'send_message') {
                html += `
                    <div class="form-group">
                        <label class="form-label">渠道</label>
                        <input type="text" class="form-input" id="propChannel" value="${node.config.channel || ''}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">消息模板</label>
                        <textarea class="form-textarea" id="propTemplate">${node.config.template || ''}</textarea>
                        <p class="form-hint">使用 {{variable}} 引用变量</p>
                    </div>
                `;
            } else if (node.subtype === 'call_skill') {
                html += `
                    <div class="form-group">
                        <label class="form-label">技能名称</label>
                        <input type="text" class="form-input" id="propSkill" value="${node.config.skill || ''}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">参数 (JSON)</label>
                        <textarea class="form-textarea" id="propParams">${JSON.stringify(node.config.params || {}, null, 2)}</textarea>
                    </div>
                `;
            } else if (node.subtype === 'api') {
                html += `
                    <div class="form-group">
                        <label class="form-label">API URL</label>
                        <input type="text" class="form-input" id="propUrl" value="${node.config.url || ''}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">HTTP 方法</label>
                        <select class="form-select" id="propApiMethod">
                            <option value="GET" ${node.config.method === 'GET' ? 'selected' : ''}>GET</option>
                            <option value="POST" ${node.config.method === 'POST' ? 'selected' : ''}>POST</option>
                            <option value="PUT" ${node.config.method === 'PUT' ? 'selected' : ''}>PUT</option>
                            <option value="DELETE" ${node.config.method === 'DELETE' ? 'selected' : ''}>DELETE</option>
                        </select>
                    </div>
                `;
            }
        } else if (node.type === 'condition') {
            if (node.subtype === 'if') {
                html += `
                    <div class="form-group">
                        <label class="form-label">字段</label>
                        <input type="text" class="form-input" id="propField" value="${node.config.field || ''}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">运算符</label>
                        <select class="form-select" id="propOperator">
                            <option value="eq" ${node.config.operator === 'eq' ? 'selected' : ''}>等于</option>
                            <option value="ne" ${node.config.operator === 'ne' ? 'selected' : ''}>不等于</option>
                            <option value="gt" ${node.config.operator === 'gt' ? 'selected' : ''}>大于</option>
                            <option value="lt" ${node.config.operator === 'lt' ? 'selected' : ''}>小于</option>
                            <option value="in" ${node.config.operator === 'in' ? 'selected' : ''}>包含</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">值</label>
                        <input type="text" class="form-input" id="propValue" value="${node.config.value || ''}">
                    </div>
                `;
            } else if (node.subtype === 'delay') {
                html += `
                    <div class="form-group">
                        <label class="form-label">等待秒数</label>
                        <input type="number" class="form-input" id="propSeconds" value="${node.config.seconds || 5}">
                    </div>
                `;
            }
        } else if (node.type === 'transform') {
            if (node.subtype === 'assign') {
                html += `
                    <div class="form-group">
                        <label class="form-label">变量名</label>
                        <input type="text" class="form-input" id="propVariable" value="${node.config.variable || ''}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">值</label>
                        <input type="text" class="form-input" id="propAssignValue" value="${node.config.value || ''}">
                    </div>
                `;
            } else if (node.subtype === 'format') {
                html += `
                    <div class="form-group">
                        <label class="form-label">输入</label>
                        <input type="text" class="form-input" id="propInput" value="${node.config.input || ''}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">输出格式</label>
                        <select class="form-select" id="propOutputFormat">
                            <option value="text" ${node.config.outputFormat === 'text' ? 'selected' : ''}>文本</option>
                            <option value="json" ${node.config.outputFormat === 'json' ? 'selected' : ''}>JSON</option>
                            <option value="xml" ${node.config.outputFormat === 'xml' ? 'selected' : ''}>XML</option>
                        </select>
                    </div>
                `;
            }
        }
        
        return html;
    }
    
    bindPropertyFormEvents(node) {
        // Name change
        const nameInput = document.getElementById('propName');
        if (nameInput) {
            nameInput.addEventListener('change', (e) => {
                node.name = e.target.value;
                this.canvas.updateNode(node);
                this.autoSave();
            });
        }
        
        // Config changes - update node config on blur
        const configFields = document.querySelectorAll('#propertiesContent input, #propertiesContent select, #propertiesContent textarea');
        configFields.forEach(field => {
            field.addEventListener('change', () => this.updateNodeConfig(node));
        });
    }
    
    updateNodeConfig(node) {
        // Read all config fields and update
        const config = {};
        
        if (node.type === 'trigger') {
            if (node.subtype === 'schedule') {
                config.cron = document.getElementById('propCron')?.value || '';
                config.timezone = document.getElementById('propTimezone')?.value || 'UTC';
            } else if (node.subtype === 'event') {
                config.event = document.getElementById('propEvent')?.value || '';
                config.source = document.getElementById('propSource')?.value || 'any';
            } else if (node.subtype === 'webhook') {
                config.path = document.getElementById('propPath')?.value || '';
                config.method = document.getElementById('propMethod')?.value || 'POST';
            }
        } else if (node.type === 'action') {
            if (node.subtype === 'send_message') {
                config.channel = document.getElementById('propChannel')?.value || '';
                config.template = document.getElementById('propTemplate')?.value || '';
            } else if (node.subtype === 'call_skill') {
                config.skill = document.getElementById('propSkill')?.value || '';
                try {
                    config.params = JSON.parse(document.getElementById('propParams')?.value || '{}');
                } catch {
                    config.params = {};
                }
            } else if (node.subtype === 'api') {
                config.url = document.getElementById('propUrl')?.value || '';
                config.method = document.getElementById('propApiMethod')?.value || 'GET';
            }
        } else if (node.type === 'condition') {
            if (node.subtype === 'if') {
                config.field = document.getElementById('propField')?.value || '';
                config.operator = document.getElementById('propOperator')?.value || 'eq';
                config.value = document.getElementById('propValue')?.value || '';
            } else if (node.subtype === 'delay') {
                config.seconds = parseInt(document.getElementById('propSeconds')?.value) || 5;
            }
        } else if (node.type === 'transform') {
            if (node.subtype === 'assign') {
                config.variable = document.getElementById('propVariable')?.value || '';
                config.value = document.getElementById('propAssignValue')?.value || '';
            } else if (node.subtype === 'format') {
                config.input = document.getElementById('propInput')?.value || '';
                config.outputFormat = document.getElementById('propOutputFormat')?.value || 'text';
            }
        }
        
        node.config = { ...node.config, ...config };
        this.autoSave();
    }
    
    // ============ Context Menu ============
    
    bindContextMenu() {
        const menu = document.getElementById('contextMenu');
        
        document.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            
            // Check if clicked on a node
            const nodeElement = e.target.closest('.workflow-node');
            
            menu.style.left = e.clientX + 'px';
            menu.style.top = e.clientY + 'px';
            menu.classList.add('visible');
            
            // Update menu items based on context
            const deleteItem = menu.querySelector('[data-action="delete"]');
            if (nodeElement) {
                deleteItem.style.display = 'flex';
            } else {
                deleteItem.style.display = 'none';
            }
        });
        
        document.addEventListener('click', () => {
            menu.classList.remove('visible');
        });
        
        // Menu item clicks
        menu.querySelectorAll('.context-menu-item').forEach(item => {
            item.addEventListener('click', () => {
                const action = item.dataset.action;
                
                if (action === 'copy' && this.selectedNode) {
                    this.copyNode();
                } else if (action === 'paste') {
                    this.pasteNode();
                } else if (action === 'delete' && this.selectedNode) {
                    this.canvas.deleteNode(this.selectedNode.id);
                }
            });
        });
    }
    
    copyNode() {
        if (this.selectedNode) {
            this.clipboard = JSON.parse(JSON.stringify(this.selectedNode));
            this.showToast('节点已复制', 'success');
        }
    }
    
    pasteNode() {
        if (this.clipboard) {
            const newNode = this.addNode(
                this.clipboard.type,
                this.clipboard.subtype,
                this.clipboard.x + 40,
                this.clipboard.y + 40
            );
            // Copy config
            newNode.config = JSON.parse(JSON.stringify(this.clipboard.config));
            this.canvas.updateNode(newNode);
            this.showToast('节点已粘贴', 'success');
        }
    }
    
    // ============ Keyboard Shortcuts ============
    
    bindKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + S: Save
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                this.saveWorkflow();
            }
            
            // Ctrl/Cmd + C: Copy
            if ((e.ctrlKey || e.metaKey) && e.key === 'c' && this.selectedNode) {
                e.preventDefault();
                this.copyNode();
            }
            
            // Ctrl/Cmd + V: Paste
            if ((e.ctrlKey || e.metaKey) && e.key === 'v') {
                e.preventDefault();
                this.pasteNode();
            }
            
            // Ctrl/Cmd + Z: Undo
            if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
                e.preventDefault();
                this.undo();
            }
            
            // Ctrl/Cmd + Shift + Z: Redo
            if ((e.ctrlKey || e.metaKey) && e.key === 'z' && e.shiftKey) {
                e.preventDefault();
                this.redo();
            }
            
            // Delete/Backspace: Delete selected node
            if ((e.key === 'Delete' || e.key === 'Backspace') && this.selectedNode) {
                if (document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
                    e.preventDefault();
                    this.canvas.deleteNode(this.selectedNode.id);
                }
            }
            
            // Escape: Deselect
            if (e.key === 'Escape') {
                this.hidePropertiesPanel();
                this.hideAllModals();
            }
        });
    }
    
    // ============ Modal Events ============
    
    bindModalEvents() {
        // Close buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => {
                this.hideAllModals();
            });
        });
        
        // Click outside modal
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideAllModals();
                }
            });
        });
        
        // Template selection
        document.getElementById('templateGrid').addEventListener('click', (e) => {
            const card = e.target.closest('.template-card');
            if (card) {
                this.loadTemplate(card.dataset.template);
                this.hideAllModals();
            }
        });
    }
    
    showModal(modalId) {
        document.getElementById(modalId).classList.add('visible');
    }
    
    hideAllModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.remove('visible');
        });
    }
    
    // ============ File Events ============
    
    bindFileEvents() {
        document.getElementById('fileImport').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.importWorkflow(file);
            }
            e.target.value = '';
        });
    }
    
    // ============ Workflow Operations ============
    
    saveWorkflow() {
        this.currentWorkflow.name = document.getElementById('workflowName').value;
        this.storage.saveCurrent(this.currentWorkflow);
        this.showToast('工作流已保存', 'success');
    }
    
    autoSave() {
        this.storage.saveCurrent(this.currentWorkflow);
    }
    
    exportWorkflow() {
        const data = JSON.stringify(this.currentWorkflow, null, 2);
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `${this.currentWorkflow.name || 'workflow'}.json`;
        a.click();
        
        URL.revokeObjectURL(url);
        this.showToast('工作流已导出', 'success');
    }
    
    importWorkflow(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = JSON.parse(e.target.result);
                
                if (data.name && data.nodes) {
                    this.currentWorkflow = data;
                    this.currentWorkflow.id = this.generateId();
                    document.getElementById('workflowName').value = data.name;
                    this.renderWorkflow();
                    this.autoSave();
                    this.showToast('工作流已导入', 'success');
                } else {
                    this.showToast('无效的工作流文件', 'error');
                }
            } catch (err) {
                this.showToast('解析文件失败', 'error');
            }
        };
        reader.readAsText(file);
    }
    
    runWorkflow() {
        this.showToast('正在运行工作流...', 'warning');
        
        // Simulate execution
        setTimeout(() => {
            this.showToast('工作流执行完成', 'success');
        }, 1500);
    }
    
    // ============ History (Undo/Redo) ============
    
    saveToHistory() {
        // Remove any redo states
        this.history = this.history.slice(0, this.historyIndex + 1);
        
        // Add current state
        this.history.push(JSON.stringify(this.currentWorkflow));
        this.historyIndex++;
        
        // Limit history size
        if (this.history.length > this.maxHistory) {
            this.history.shift();
            this.historyIndex--;
        }
    }
    
    undo() {
        if (this.historyIndex > 0) {
            this.historyIndex--;
            this.currentWorkflow = JSON.parse(this.history[this.historyIndex]);
            this.renderWorkflow();
            this.showToast('已撤销', 'success');
        }
    }
    
    redo() {
        if (this.historyIndex < this.history.length - 1) {
            this.historyIndex++;
            this.currentWorkflow = JSON.parse(this.history[this.historyIndex]);
            this.renderWorkflow();
            this.showToast('已重做', 'success');
        }
    }
    
    // ============ Templates ============
    
    loadTemplates() {
        const templates = [
            {
                id: 'daily_briefing',
                name: '每日简报',
                description: '每天早上自动获取天气和日程，生成个性化简报',
                nodes: 6
            },
            {
                id: 'weather_reminder',
                name: '天气提醒',
                description: '根据天气情况自动发送提醒，支持雨具和穿衣建议',
                nodes: 9
            },
            {
                id: 'weekly_summary',
                name: '周报摘要',
                description: '每周一生成工作周报，包含任务、会议和代码提交统计',
                nodes: 7
            },
            {
                id: 'welcome_flow',
                name: '欢迎流程',
                description: '新用户欢迎和引导流程，支持多语言',
                nodes: 10
            }
        ];
        
        const grid = document.getElementById('templateGrid');
        grid.innerHTML = templates.map(t => `
            <div class="template-card" data-template="${t.id}">
                <h4>${t.name}</h4>
                <p>${t.description}</p>
                <div class="template-meta">
                    <span>📦 ${t.nodes} 个节点</span>
                </div>
            </div>
        `).join('');
    }
    
    loadTemplate(templateId) {
        // Map template IDs to YAML files
        const templateMap = {
            'daily_briefing': '../workflows/daily_briefing.yaml',
            'weather_reminder': '../workflows/weather_reminder.yaml',
            'weekly_summary': '../workflows/weekly_summary.yaml',
            'welcome_flow': '../workflows/welcome_flow.yaml'
        };
        
        const url = templateMap[templateId];
        if (url) {
            // In a real app, fetch and parse the YAML
            // For now, just show a message
            this.showToast(`模板 "${templateId}" 已加载`, 'success');
        }
    }
    
    // ============ Render ============
    
    renderWorkflow() {
        this.canvas.clear();
        
        // Render nodes
        this.currentWorkflow.nodes.forEach(node => {
            this.canvas.addNode(node);
        });
        
        // Render edges
        this.currentWorkflow.edges.forEach(edge => {
            this.canvas.addConnection(edge.from, edge.to);
        });
    }
    
    // ============ Toast Notifications ============
    
    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        
        const icons = {
            success: '✓',
            error: '✗',
            warning: '⚠',
            info: 'ℹ'
        };
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || icons.info}</span>
            <span class="toast-message">${message}</span>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.editor = new WorkflowEditor();
});
