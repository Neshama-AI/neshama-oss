/**
 * Workflow Storage Module
 * Handles local storage for workflows
 */

class WorkflowStorage {
    constructor() {
        this.storageKey = 'neshama_workflow_current';
        this.listKey = 'neshama_workflow_list';
    }
    
    saveCurrent(workflow) {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(workflow));
            this.addToList(workflow.id, workflow.name);
            return true;
        } catch (e) {
            console.error('Failed to save workflow:', e);
            return false;
        }
    }
    
    loadCurrent() {
        try {
            const data = localStorage.getItem(this.storageKey);
            return data ? JSON.parse(data) : null;
        } catch (e) {
            console.error('Failed to load workflow:', e);
            return null;
        }
    }
    
    load(workflowId) {
        try {
            const data = localStorage.getItem(`neshama_workflow_${workflowId}`);
            return data ? JSON.parse(data) : null;
        } catch (e) {
            console.error('Failed to load workflow:', e);
            return null;
        }
    }
    
    save(workflowId, workflow) {
        try {
            localStorage.setItem(`neshama_workflow_${workflowId}`, JSON.stringify(workflow));
            this.addToList(workflowId, workflow.name);
            return true;
        } catch (e) {
            console.error('Failed to save workflow:', e);
            return false;
        }
    }
    
    delete(workflowId) {
        try {
            localStorage.removeItem(`neshama_workflow_${workflowId}`);
            this.removeFromList(workflowId);
            return true;
        } catch (e) {
            console.error('Failed to delete workflow:', e);
            return false;
        }
    }
    
    addToList(id, name) {
        const list = this.getList();
        
        // Remove if exists
        const existing = list.findIndex(item => item.id === id);
        if (existing !== -1) {
            list.splice(existing, 1);
        }
        
        // Add to beginning
        list.unshift({
            id,
            name,
            updatedAt: new Date().toISOString()
        });
        
        // Keep only last 50
        if (list.length > 50) {
            list.pop();
        }
        
        localStorage.setItem(this.listKey, JSON.stringify(list));
    }
    
    removeFromList(id) {
        const list = this.getList().filter(item => item.id !== id);
        localStorage.setItem(this.listKey, JSON.stringify(list));
    }
    
    getList() {
        try {
            const data = localStorage.getItem(this.listKey);
            return data ? JSON.parse(data) : [];
        } catch (e) {
            return [];
        }
    }
    
    exportToFile(workflow) {
        const data = JSON.stringify(workflow, null, 2);
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `${workflow.name || 'workflow'}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    importFromFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = (e) => {
                try {
                    const data = JSON.parse(e.target.result);
                    resolve(data);
                } catch (err) {
                    reject(new Error('Invalid JSON file'));
                }
            };
            
            reader.onerror = () => reject(new Error('Failed to read file'));
            reader.readAsText(file);
        });
    }
}
