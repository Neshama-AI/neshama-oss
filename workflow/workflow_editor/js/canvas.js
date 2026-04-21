/**
 * Canvas Module
 * Handles workflow canvas rendering and interaction
 */

class Canvas {
    constructor(options = {}) {
        this.container = document.getElementById('canvas');
        this.nodesLayer = document.getElementById('nodesLayer');
        this.connectionsLayer = document.getElementById('connectionsLayer');
        
        this.scale = 1;
        this.offsetX = 0;
        this.offsetY = 0;
        
        this.nodes = new Map();
        this.connections = [];
        
        this.selectedNode = null;
        this.draggingNode = null;
        this.draggingCanvas = false;
        this.connecting = false;
        this.connectingFromNode = null;
        
        this.onNodeSelect = options.onNodeSelect || (() => {});
        this.onNodeDelete = options.onNodeDelete || (() => {});
        this.onConnectionCreate = options.onConnectionCreate || (() => {});
        this.onCanvasChange = options.onCanvasChange || (() => {});
        
        this.lastMouseX = 0;
        this.lastMouseY = 0;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.updateTransform();
        this.updateMiniMap();
    }
    
    bindEvents() {
        // Mouse events for panning
        this.container.addEventListener('mousedown', (e) => this.onMouseDown(e));
        document.addEventListener('mousemove', (e) => this.onMouseMove(e));
        document.addEventListener('mouseup', (e) => this.onMouseUp(e));
        
        // Wheel for zooming
        this.container.addEventListener('wheel', (e) => this.onWheel(e));
        
        // Double click for editing
        this.container.addEventListener('dblclick', (e) => this.onDoubleClick(e));
    }
    
    onMouseDown(e) {
        // Check if clicking on node
        const nodeElement = e.target.closest('.workflow-node');
        
        if (nodeElement) {
            const nodeId = nodeElement.dataset.id;
            
            // Check if clicking on port
            const portElement = e.target.closest('.node-port');
            
            if (portElement) {
                this.startConnecting(nodeId, portElement.classList.contains('output'));
                return;
            }
            
            // Select and start dragging node
            this.selectNode(nodeId);
            this.startDraggingNode(nodeId, e);
            return;
        }
        
        // Check if clicking on connection
        const connectionElement = e.target.closest('.connection-path');
        if (connectionElement) {
            this.selectConnection(connectionElement);
            return;
        }
        
        // Deselect and start panning
        this.deselectAll();
        this.startPanning(e);
    }
    
    onMouseMove(e) {
        if (this.draggingNode) {
            this.updateDraggingNode(e);
        } else if (this.draggingCanvas) {
            this.updatePanning(e);
        } else if (this.connecting) {
            this.updateConnectingLine(e);
        }
    }
    
    onMouseUp(e) {
        if (this.draggingNode) {
            this.stopDraggingNode();
        }
        
        if (this.draggingCanvas) {
            this.stopPanning();
        }
        
        if (this.connecting) {
            // Check if we're over a node
            const nodeElement = e.target.closest('.workflow-node');
            if (nodeElement) {
                const targetNodeId = nodeElement.dataset.id;
                if (targetNodeId !== this.connectingFromNode) {
                    this.completeConnection(targetNodeId);
                }
            }
            this.cancelConnecting();
        }
    }
    
    onWheel(e) {
        e.preventDefault();
        
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        const newScale = Math.max(0.25, Math.min(2, this.scale + delta));
        
        // Zoom towards mouse position
        const rect = this.container.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        
        const scaleChange = newScale - this.scale;
        
        this.offsetX -= (mouseX - this.offsetX) * (scaleChange / this.scale);
        this.offsetY -= (mouseY - this.offsetY) * (scaleChange / this.scale);
        
        this.scale = newScale;
        this.updateTransform();
        this.updateZoomDisplay();
    }
    
    onDoubleClick(e) {
        const nodeElement = e.target.closest('.workflow-node');
        if (nodeElement) {
            const nodeId = nodeElement.dataset.id;
            this.onNodeSelect(this.nodes.get(nodeId));
        }
    }
    
    // ============ Node Operations ============
    
    addNode(nodeData) {
        const nodeId = nodeData.id;
        
        // Create node element
        const nodeEl = document.createElement('div');
        nodeEl.className = `workflow-node ${nodeData.type}`;
        nodeEl.dataset.id = nodeId;
        nodeEl.style.left = nodeData.x + 'px';
        nodeEl.style.top = nodeData.y + 'px';
        
        const iconMap = {
            trigger: {
                schedule: '⏰',
                event: '⚡',
                webhook: '🪝'
            },
            action: {
                send_message: '💬',
                call_skill: '🎯',
                get_info: '🔍',
                generate: '✨',
                api: '🌐'
            },
            condition: {
                if: '❓',
                loop: '🔄',
                delay: '⏱️'
            },
            transform: {
                assign: '📝',
                format: '🔄',
                extract: '🎯'
            }
        };
        
        const icon = iconMap[nodeData.type]?.[nodeData.subtype] || '📦';
        
        nodeEl.innerHTML = `
            <div class="node-header">
                <div class="node-icon-wrapper">${icon}</div>
                <span class="node-title">${nodeData.name}</span>
                <button class="node-delete" title="删除">×</button>
            </div>
            <div class="node-body">
                <p class="node-description">${nodeData.description || ''}</p>
                <div class="node-ports">
                    <div class="node-port input" title="输入"></div>
                    <div class="node-port output" title="输出"></div>
                </div>
            </div>
        `;
        
        this.nodesLayer.appendChild(nodeEl);
        this.nodes.set(nodeId, { ...nodeData, element: nodeEl });
        
        // Bind node events
        nodeEl.querySelector('.node-delete').addEventListener('click', (e) => {
            e.stopPropagation();
            this.deleteNode(nodeId);
        });
        
        return nodeEl;
    }
    
    updateNode(nodeData) {
        const node = this.nodes.get(nodeData.id);
        if (node) {
            node.name = nodeData.name;
            node.config = nodeData.config;
            node.element.querySelector('.node-title').textContent = nodeData.name;
        }
    }
    
    removeNode(nodeId) {
        const node = this.nodes.get(nodeId);
        if (node) {
            node.element.remove();
            this.nodes.delete(nodeId);
            
            // Remove related connections
            this.connections = this.connections.filter(conn => {
                if (conn.from === nodeId || conn.to === nodeId) {
                    conn.element?.remove();
                    return false;
                }
                return true;
            });
        }
    }
    
    deleteNode(nodeId) {
        this.removeNode(nodeId);
        this.onNodeDelete(nodeId);
    }
    
    selectNode(nodeId) {
        this.deselectAll();
        const node = this.nodes.get(nodeId);
        if (node) {
            node.element.classList.add('selected');
            this.selectedNode = node;
            this.onNodeSelect(node);
        }
    }
    
    deselectAll() {
        this.nodes.forEach(node => {
            node.element.classList.remove('selected');
        });
        this.selectedNode = null;
        
        // Deselect connections
        this.connectionsLayer.querySelectorAll('.connection-path').forEach(el => {
            el.classList.remove('selected');
        });
    }
    
    // ============ Drag Operations ============
    
    startDraggingNode(nodeId, e) {
        const node = this.nodes.get(nodeId);
        if (!node) return;
        
        this.draggingNode = nodeId;
        this.dragOffset = {
            x: e.clientX - node.x * this.scale - this.offsetX,
            y: e.clientY - node.y * this.scale - this.offsetY
        };
        
        this.container.classList.add('dragging-node');
    }
    
    updateDraggingNode(e) {
        const node = this.nodes.get(this.draggingNode);
        if (!node) return;
        
        const rect = this.container.getBoundingClientRect();
        const mouseX = (e.clientX - rect.left - this.offsetX) / this.scale;
        const mouseY = (e.clientY - rect.top - this.offsetY) / this.scale;
        
        // Snap to grid (20px)
        node.x = Math.round((mouseX - this.dragOffset.x / this.scale) / 20) * 20;
        node.y = Math.round((mouseY - this.dragOffset.y / this.scale) / 20) * 20;
        
        node.element.style.left = node.x + 'px';
        node.element.style.top = node.y + 'px';
        
        // Update connections
        this.updateConnectionsForNode(this.draggingNode);
    }
    
    stopDraggingNode() {
        if (this.draggingNode) {
            const node = this.nodes.get(this.draggingNode);
            if (node) {
                this.onCanvasChange();
            }
        }
        
        this.draggingNode = null;
        this.container.classList.remove('dragging-node');
    }
    
    // ============ Pan Operations ============
    
    startPanning(e) {
        this.draggingCanvas = true;
        this.lastMouseX = e.clientX;
        this.lastMouseY = e.clientY;
    }
    
    updatePanning(e) {
        const dx = e.clientX - this.lastMouseX;
        const dy = e.clientY - this.lastMouseY;
        
        this.offsetX += dx;
        this.offsetY += dy;
        
        this.lastMouseX = e.clientX;
        this.lastMouseY = e.clientY;
        
        this.updateTransform();
    }
    
    stopPanning() {
        this.draggingCanvas = false;
        this.onCanvasChange();
    }
    
    // ============ Connection Operations ============
    
    startConnecting(nodeId, isOutput) {
        this.connecting = true;
        this.connectingFromNode = nodeId;
        this.connectingIsOutput = isOutput;
        this.container.classList.add('connecting');
        
        // Create temp line
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        line.classList.add('temp-connection');
        this.tempLine = line;
        this.connectionsLayer.appendChild(line);
    }
    
    updateConnectingLine(e) {
        if (!this.tempLine) return;
        
        const fromNode = this.nodes.get(this.connectingFromNode);
        if (!fromNode) return;
        
        const rect = this.container.getBoundingClientRect();
        
        // Get port position
        const portEl = fromNode.element.querySelector('.node-port.output');
        const portRect = portEl.getBoundingClientRect();
        
        const startX = (portRect.left + portRect.width / 2 - rect.left - this.offsetX) / this.scale;
        const startY = (portRect.top + portRect.height / 2 - rect.top - this.offsetY) / this.scale;
        
        const endX = (e.clientX - rect.left - this.offsetX) / this.scale;
        const endY = (e.clientY - rect.top - this.offsetY) / this.scale;
        
        const path = this.createBezierPath(startX, startY, endX, endY);
        this.tempLine.setAttribute('d', path);
    }
    
    completeConnection(toNodeId) {
        if (this.connectingIsOutput) {
            this.onConnectionCreate(this.connectingFromNode, toNodeId);
            this.addConnection(this.connectingFromNode, toNodeId);
        } else {
            this.onConnectionCreate(toNodeId, this.connectingFromNode);
            this.addConnection(toNodeId, this.connectingFromNode);
        }
    }
    
    cancelConnecting() {
        this.connecting = false;
        this.connectingFromNode = null;
        this.container.classList.remove('connecting');
        
        if (this.tempLine) {
            this.tempLine.remove();
            this.tempLine = null;
        }
    }
    
    addConnection(fromId, toId) {
        const fromNode = this.nodes.get(fromId);
        const toNode = this.nodes.get(toId);
        
        if (!fromNode || !toNode) return;
        
        // Create connection element
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.classList.add('connection-path');
        
        this.connectionsLayer.appendChild(path);
        
        const connection = {
            from: fromId,
            to: toId,
            element: path
        };
        
        this.connections.push(connection);
        this.updateConnectionsForNode(fromId);
        
        // Mark ports as connected
        fromNode.element.querySelector('.node-port.output')?.classList.add('connected');
        toNode.element.querySelector('.node-port.input')?.classList.add('connected');
        
        return connection;
    }
    
    updateConnectionsForNode(nodeId) {
        const node = this.nodes.get(nodeId);
        if (!node) return;
        
        // Update outgoing connections
        this.connections.forEach(conn => {
            if (conn.from === nodeId) {
                const toNode = this.nodes.get(conn.to);
                if (toNode) {
                    const path = this.calculateConnectionPath(node, toNode);
                    conn.element.setAttribute('d', path);
                }
            }
            
            // Update incoming connections
            if (conn.to === nodeId) {
                const fromNode = this.nodes.get(conn.from);
                if (fromNode) {
                    const path = this.calculateConnectionPath(fromNode, node);
                    conn.element.setAttribute('d', path);
                }
            }
        });
    }
    
    calculateConnectionPath(fromNode, toNode) {
        const fromPort = fromNode.element.querySelector('.node-port.output');
        const toPort = toNode.element.querySelector('.node-port.input');
        
        if (!fromPort || !toPort) return '';
        
        const fromRect = fromPort.getBoundingClientRect();
        const toRect = toPort.getBoundingClientRect();
        const canvasRect = this.container.getBoundingClientRect();
        
        const startX = (fromRect.left + fromRect.width / 2 - canvasRect.left - this.offsetX) / this.scale;
        const startY = (fromRect.top + fromRect.height / 2 - canvasRect.top - this.offsetY) / this.scale;
        
        const endX = (toRect.left + toRect.width / 2 - canvasRect.left - this.offsetX) / this.scale;
        const endY = (toRect.top + toRect.height / 2 - canvasRect.top - this.offsetY) / this.scale;
        
        return this.createBezierPath(startX, startY, endX, endY);
    }
    
    createBezierPath(startX, startY, endX, endY) {
        const dx = endX - startX;
        const controlOffset = Math.min(Math.abs(dx) / 2, 100);
        
        const cp1x = startX + controlOffset;
        const cp1y = startY;
        const cp2x = endX - controlOffset;
        const cp2y = endY;
        
        return `M ${startX} ${startY} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${endX} ${endY}`;
    }
    
    selectConnection(connectionElement) {
        this.deselectAll();
        connectionElement.classList.add('selected');
    }
    
    // ============ Transform & Zoom ============
    
    updateTransform() {
        this.nodesLayer.style.transform = `translate(${this.offsetX}px, ${this.offsetY}px) scale(${this.scale})`;
        this.connectionsLayer.style.transform = `translate(${this.offsetX}px, ${this.offsetY}px) scale(${this.scale})`;
        this.container.style.backgroundPosition = `${this.offsetX}px ${this.offsetY}px`;
        this.container.style.backgroundSize = `${20 * this.scale}px ${20 * this.scale}px`;
        
        this.updateMiniMap();
    }
    
    updateZoomDisplay() {
        document.getElementById('zoomLevel').textContent = Math.round(this.scale * 100) + '%';
    }
    
    zoomIn() {
        this.scale = Math.min(2, this.scale + 0.1);
        this.updateTransform();
        this.updateZoomDisplay();
    }
    
    zoomOut() {
        this.scale = Math.max(0.25, this.scale - 0.1);
        this.updateTransform();
        this.updateZoomDisplay();
    }
    
    zoomReset() {
        this.scale = 1;
        this.offsetX = 0;
        this.offsetY = 0;
        this.updateTransform();
        this.updateZoomDisplay();
    }
    
    fitView() {
        if (this.nodes.size === 0) {
            this.zoomReset();
            return;
        }
        
        // Calculate bounds
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        
        this.nodes.forEach(node => {
            minX = Math.min(minX, node.x);
            minY = Math.min(minY, node.y);
            maxX = Math.max(maxX, node.x + 180);
            maxY = Math.max(maxY, node.y + 80);
        });
        
        const padding = 50;
        const contentWidth = maxX - minX + padding * 2;
        const contentHeight = maxY - minY + padding * 2;
        
        const containerRect = this.container.getBoundingClientRect();
        const scaleX = containerRect.width / contentWidth;
        const scaleY = containerRect.height / contentHeight;
        
        this.scale = Math.min(scaleX, scaleY, 1);
        this.scale = Math.max(0.25, Math.min(1, this.scale));
        
        this.offsetX = -minX * this.scale + padding * this.scale + (containerRect.width - contentWidth * this.scale) / 2;
        this.offsetY = -minY * this.scale + padding * this.scale + (containerRect.height - contentHeight * this.scale) / 2;
        
        this.updateTransform();
        this.updateZoomDisplay();
    }
    
    // ============ Mini Map ============
    
    updateMiniMap() {
        const miniMap = document.getElementById('miniMap');
        const viewport = document.getElementById('miniMapViewport');
        
        const containerRect = this.container.getBoundingClientRect();
        const mapWidth = 160;
        const mapHeight = 120;
        
        if (this.nodes.size === 0) {
            viewport.style.display = 'none';
            return;
        }
        
        viewport.style.display = 'block';
        
        // Calculate node positions in mini map
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        
        this.nodes.forEach(node => {
            minX = Math.min(minX, node.x);
            minY = Math.min(minY, node.y);
            maxX = Math.max(maxX, node.x + 180);
            maxY = Math.max(maxY, node.y + 80);
        });
        
        const contentWidth = maxX - minX;
        const contentHeight = maxY - minY;
        
        const scale = Math.min(mapWidth / contentWidth, mapHeight / contentHeight, 0.2);
        
        const vpWidth = containerRect.width * scale / this.scale;
        const vpHeight = containerRect.height * scale / this.scale;
        const vpX = (-this.offsetX / this.scale - minX) * scale;
        const vpY = (-this.offsetY / this.scale - minY) * scale;
        
        viewport.style.width = Math.max(20, vpWidth) + 'px';
        viewport.style.height = Math.max(15, vpHeight) + 'px';
        viewport.style.left = Math.max(0, Math.min(mapWidth - vpWidth, vpX)) + 'px';
        viewport.style.top = Math.max(0, Math.min(mapHeight - vpHeight, vpY)) + 'px';
    }
    
    // ============ Utility ============
    
    clear() {
        this.nodesLayer.innerHTML = '';
        this.connectionsLayer.querySelectorAll('.connection-path').forEach(el => el.remove());
        this.connections = [];
        this.nodes.clear();
    }
}
