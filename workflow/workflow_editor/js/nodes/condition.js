/**
 * Condition Node Module
 * Handles condition node configurations
 */

class ConditionNode {
    static getConfig(type) {
        const configs = {
            if: {
                name: 'IF 分支',
                description: '根据条件判断执行不同的分支',
                icon: '❓',
                color: 'condition',
                outputPorts: [
                    { id: 'true', label: '是' },
                    { id: 'false', label: '否' }
                ],
                fields: [
                    {
                        name: 'field',
                        label: '字段',
                        type: 'text',
                        default: '',
                        placeholder: 'weather.condition',
                        hint: '要检查的字段路径'
                    },
                    {
                        name: 'operator',
                        label: '运算符',
                        type: 'select',
                        default: 'eq',
                        options: [
                            { value: 'eq', label: '等于 (==)' },
                            { value: 'ne', label: '不等于 (!=)' },
                            { value: 'gt', label: '大于 (>)' },
                            { value: 'gte', label: '大于等于 (>=)' },
                            { value: 'lt', label: '小于 (<)' },
                            { value: 'lte', label: '小于等于 (<=)' },
                            { value: 'in', label: '包含于' },
                            { value: 'not_in', label: '不包含于' },
                            { value: 'contains', label: '包含' },
                            { value: 'starts_with', label: '开头是' },
                            { value: 'ends_with', label: '结尾是' },
                            { value: 'is_empty', label: '为空' },
                            { value: 'is_not_empty', label: '不为空' }
                        ]
                    },
                    {
                        name: 'value',
                        label: '值',
                        type: 'text',
                        default: '',
                        placeholder: 'rain',
                        hint: '比较的值'
                    }
                ]
            },
            loop: {
                name: '循环',
                description: '重复执行一组节点',
                icon: '🔄',
                color: 'condition',
                fields: [
                    {
                        name: 'type',
                        label: '循环类型',
                        type: 'select',
                        default: 'times',
                        options: [
                            { value: 'times', label: '固定次数' },
                            { value: 'items', label: '遍历列表' },
                            { value: 'while', label: '条件为真时' }
                        ]
                    },
                    {
                        name: 'times',
                        label: '重复次数',
                        type: 'number',
                        default: 3,
                        hint: '循环执行的次数'
                    },
                    {
                        name: 'items_var',
                        label: '列表变量',
                        type: 'text',
                        default: '',
                        placeholder: 'items',
                        hint: '要遍历的列表变量名'
                    },
                    {
                        name: 'condition',
                        label: '循环条件',
                        type: 'text',
                        default: '',
                        placeholder: 'i < 10',
                        hint: 'while 循环的条件表达式'
                    },
                    {
                        name: 'loop_var',
                        label: '循环变量名',
                        type: 'text',
                        default: 'item',
                        placeholder: 'item',
                        hint: '当前遍历项的变量名'
                    }
                ]
            },
            delay: {
                name: '延时',
                description: '等待指定时间后继续执行',
                icon: '⏱️',
                color: 'condition',
                fields: [
                    {
                        name: 'duration',
                        label: '延迟时间',
                        type: 'number',
                        default: 5,
                        hint: '延迟的秒数'
                    },
                    {
                        name: 'unit',
                        label: '时间单位',
                        type: 'select',
                        default: 'seconds',
                        options: [
                            { value: 'seconds', label: '秒' },
                            { value: 'minutes', label: '分钟' },
                            { value: 'hours', label: '小时' }
                        ]
                    }
                ]
            }
        };
        
        return configs[type] || configs.if;
    }
    
    static renderConfigForm(node) {
        const config = this.getConfig(node.subtype);
        let html = '';
        
        config.fields.forEach(field => {
            // Skip fields based on loop type
            if (node.subtype === 'loop') {
                const loopType = document.getElementById('condition_type')?.value || node.config.type || 'times';
                if (field.name === 'times' && loopType !== 'times') return;
                if (field.name === 'items_var' && loopType !== 'items') return;
                if (field.name === 'condition' && loopType !== 'while') return;
            }
            
            html += `<div class="form-group">`;
            html += `<label class="form-label">${field.label}</label>`;
            
            if (field.type === 'text') {
                html += `<input type="text" class="form-input" 
                    id="condition_${field.name}" 
                    value="${node.config[field.name] || field.default}"
                    placeholder="${field.placeholder || ''}">`;
            } else if (field.type === 'number') {
                html += `<input type="number" class="form-input" 
                    id="condition_${field.name}" 
                    value="${node.config[field.name] || field.default}">`;
            } else if (field.type === 'select') {
                html += `<select class="form-select" id="condition_${field.name}">`;
                field.options.forEach(opt => {
                    const selected = (node.config[field.name] || field.default) === opt.value ? 'selected' : '';
                    html += `<option value="${opt.value}" ${selected}>${opt.label}</option>`;
                });
                html += `</select>`;
            }
            
            if (field.hint) {
                html += `<p class="form-hint">${field.hint}</p>`;
            }
            
            html += `</div>`;
        });
        
        // Add condition preview
        if (node.subtype === 'if') {
            html += `
                <div class="form-group">
                    <label class="form-label">条件预览</label>
                    <div class="condition-preview">
                        ${this.describeCondition(node.config)}
                    </div>
                </div>
            `;
        }
        
        return html;
    }
    
    static getConfigFromForm() {
        const config = {};
        
        // Get all form fields starting with condition_
        const fields = document.querySelectorAll('[id^="condition_"]');
        fields.forEach(field => {
            const key = field.id.replace('condition_', '');
            config[key] = field.type === 'number' ? parseInt(field.value) : field.value;
        });
        
        return config;
    }
    
    static validateConfig(node) {
        const errors = [];
        
        if (node.subtype === 'if') {
            if (!node.config.field) {
                errors.push('要检查的字段不能为空');
            }
            if (!node.config.operator) {
                errors.push('请选择运算符');
            }
            // Value can be empty for is_empty/is_not_empty
            if (!['is_empty', 'is_not_empty'].includes(node.config.operator) && 
                (node.config.value === undefined || node.config.value === '')) {
                errors.push('比较的值不能为空');
            }
        }
        
        if (node.subtype === 'loop') {
            if (node.config.type === 'times') {
                if (!node.config.times || node.config.times < 1) {
                    errors.push('循环次数必须大于 0');
                }
            } else if (node.config.type === 'items') {
                if (!node.config.items_var) {
                    errors.push('列表变量名不能为空');
                }
            } else if (node.config.type === 'while') {
                if (!node.config.condition) {
                    errors.push('循环条件不能为空');
                }
            }
        }
        
        if (node.subtype === 'delay') {
            if (!node.config.duration || node.config.duration < 0) {
                errors.push('延迟时间必须大于等于 0');
            }
        }
        
        return errors;
    }
    
    static describeCondition(config) {
        if (!config.field) return '条件未配置';
        
        const operatorLabels = {
            'eq': '等于',
            'ne': '不等于',
            'gt': '大于',
            'gte': '大于等于',
            'lt': '小于',
            'lte': '小于等于',
            'in': '包含于',
            'not_in': '不包含于',
            'contains': '包含',
            'starts_with': '开头是',
            'ends_with': '结尾是',
            'is_empty': '为空',
            'is_not_empty': '不为空'
        };
        
        const op = operatorLabels[config.operator] || config.operator;
        
        if (['is_empty', 'is_not_empty'].includes(config.operator)) {
            return `<span class="code">${config.field}</span> ${op}`;
        }
        
        return `<span class="code">${config.field}</span> ${op} <span class="value">${config.value}</span>`;
    }
    
    static evaluateCondition(config, context) {
        const fieldValue = this.getNestedValue(context, config.field);
        const compareValue = config.value;
        
        switch (config.operator) {
            case 'eq':
                return fieldValue == compareValue;
            case 'ne':
                return fieldValue != compareValue;
            case 'gt':
                return Number(fieldValue) > Number(compareValue);
            case 'gte':
                return Number(fieldValue) >= Number(compareValue);
            case 'lt':
                return Number(fieldValue) < Number(compareValue);
            case 'lte':
                return Number(fieldValue) <= Number(compareValue);
            case 'in':
                const inValues = Array.isArray(compareValue) ? compareValue : compareValue.split(',');
                return inValues.includes(fieldValue);
            case 'not_in':
                const notInValues = Array.isArray(compareValue) ? compareValue : compareValue.split(',');
                return !notInValues.includes(fieldValue);
            case 'contains':
                return String(fieldValue).includes(compareValue);
            case 'starts_with':
                return String(fieldValue).startsWith(compareValue);
            case 'ends_with':
                return String(fieldValue).endsWith(compareValue);
            case 'is_empty':
                return !fieldValue || fieldValue === '' || fieldValue === null;
            case 'is_not_empty':
                return fieldValue && fieldValue !== '' && fieldValue !== null;
            default:
                return false;
        }
    }
    
    static getNestedValue(obj, path) {
        if (!path) return undefined;
        return path.split('.').reduce((current, key) => 
            current && current[key] !== undefined ? current[key] : undefined, obj);
    }
}

// Make it globally accessible
window.ConditionNode = ConditionNode;
