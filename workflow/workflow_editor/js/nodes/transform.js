/**
 * Transform Node Module
 * Handles transform node configurations
 */

class TransformNode {
    static getConfig(type) {
        const configs = {
            assign: {
                name: '变量赋值',
                description: '设置或修改变量的值',
                icon: '📝',
                color: 'transform',
                fields: [
                    {
                        name: 'variable',
                        label: '变量名',
                        type: 'text',
                        default: '',
                        placeholder: 'my_variable',
                        hint: '要赋值的变量名称'
                    },
                    {
                        name: 'value',
                        label: '值',
                        type: 'textarea',
                        default: '',
                        placeholder: '{{other_var}} or 123 or "text"',
                        hint: '变量的值，支持 {{variable}} 插值'
                    },
                    {
                        name: 'mode',
                        label: '赋值模式',
                        type: 'select',
                        default: 'set',
                        options: [
                            { value: 'set', label: '设置 (覆盖)' },
                            { value: 'append', label: '追加' },
                            { value: 'prepend', label: '前缀' }
                        ]
                    }
                ]
            },
            format: {
                name: '格式转换',
                description: '转换数据的格式',
                icon: '🔄',
                color: 'transform',
                fields: [
                    {
                        name: 'input',
                        label: '输入变量',
                        type: 'text',
                        default: '',
                        placeholder: 'data',
                        hint: '要转换的数据变量'
                    },
                    {
                        name: 'inputFormat',
                        label: '输入格式',
                        type: 'select',
                        default: 'json',
                        options: [
                            { value: 'json', label: 'JSON' },
                            { value: 'text', label: '纯文本' },
                            { value: 'xml', label: 'XML' },
                            { value: 'csv', label: 'CSV' }
                        ]
                    },
                    {
                        name: 'outputFormat',
                        label: '输出格式',
                        type: 'select',
                        default: 'text',
                        options: [
                            { value: 'text', label: '纯文本' },
                            { value: 'json', label: 'JSON' },
                            { value: 'xml', label: 'XML' },
                            { value: 'csv', label: 'CSV' }
                        ]
                    },
                    {
                        name: 'template',
                        label: '格式化模板',
                        type: 'textarea',
                        default: '',
                        placeholder: '{{field1}}, {{field2}}',
                        hint: '输出模板，{{field}} 引用输入字段'
                    },
                    {
                        name: 'output_var',
                        label: '输出变量名',
                        type: 'text',
                        default: 'formatted_data',
                        placeholder: 'result',
                        hint: '存储转换结果的变量名'
                    }
                ]
            },
            extract: {
                name: '数据提取',
                description: '从复杂数据中提取特定字段',
                icon: '🎯',
                color: 'transform',
                fields: [
                    {
                        name: 'source',
                        label: '源数据',
                        type: 'text',
                        default: '',
                        placeholder: 'api_response',
                        hint: '包含要提取数据的变量'
                    },
                    {
                        name: 'path',
                        label: '提取路径',
                        type: 'text',
                        default: '',
                        placeholder: 'data.items[0].name',
                        hint: 'JSON path 或字段名'
                    },
                    {
                        name: 'default_value',
                        label: '默认值',
                        type: 'text',
                        default: '',
                        placeholder: 'N/A',
                        hint: '提取失败时使用的默认值'
                    },
                    {
                        name: 'output_var',
                        label: '输出变量名',
                        type: 'text',
                        default: 'extracted_value',
                        placeholder: 'value',
                        hint: '存储提取结果的变量名'
                    }
                ]
            }
        };
        
        return configs[type] || configs.assign;
    }
    
    static renderConfigForm(node) {
        const config = this.getConfig(node.subtype);
        let html = '';
        
        config.fields.forEach(field => {
            html += `<div class="form-group">`;
            html += `<label class="form-label">${field.label}</label>`;
            
            if (field.type === 'text') {
                html += `<input type="text" class="form-input" 
                    id="transform_${field.name}" 
                    value="${node.config[field.name] || field.default}"
                    placeholder="${field.placeholder || ''}">`;
            } else if (field.type === 'select') {
                html += `<select class="form-select" id="transform_${field.name}">`;
                field.options.forEach(opt => {
                    const selected = (node.config[field.name] || field.default) === opt.value ? 'selected' : '';
                    html += `<option value="${opt.value}" ${selected}>${opt.label}</option>`;
                });
                html += `</select>`;
            } else if (field.type === 'textarea') {
                html += `<textarea class="form-textarea" 
                    id="transform_${field.name}" 
                    placeholder="${field.placeholder || ''}">${node.config[field.name] || field.default}</textarea>`;
            }
            
            if (field.hint) {
                html += `<p class="form-hint">${field.hint}</p>`;
            }
            
            html += `</div>`;
        });
        
        // Add transform preview
        html += `
            <div class="form-group">
                <label class="form-label">转换预览</label>
                <div class="transform-preview">
                    ${this.describeTransform(node.config)}
                </div>
            </div>
        `;
        
        return html;
    }
    
    static getConfigFromForm() {
        const config = {};
        
        // Get all form fields starting with transform_
        const fields = document.querySelectorAll('[id^="transform_"]');
        fields.forEach(field => {
            const key = field.id.replace('transform_', '');
            config[key] = field.value;
        });
        
        return config;
    }
    
    static validateConfig(node) {
        const errors = [];
        
        switch (node.subtype) {
            case 'assign':
                if (!node.config.variable) {
                    errors.push('变量名不能为空');
                }
                break;
                
            case 'format':
                if (!node.config.input) {
                    errors.push('输入变量不能为空');
                }
                break;
                
            case 'extract':
                if (!node.config.source) {
                    errors.push('源数据不能为空');
                }
                if (!node.config.path) {
                    errors.push('提取路径不能为空');
                }
                break;
        }
        
        return errors;
    }
    
    static describeTransform(config) {
        switch (config.mode || 'set') {
            case 'assign':
                return `<span class="var">{{${config.variable || 'var'}}}</span> = <span class="value">${config.value || '""'}</span>`;
            case 'format':
                return `转换 <span class="var">${config.input || 'data'}</span> 从 ${config.inputFormat} 到 ${config.outputFormat}`;
            case 'extract':
                return `从 <span class="var">${config.source || 'source'}</span> 提取 <span class="path">${config.path || 'path'}</span>`;
            default:
                return '转换未配置';
        }
    }
    
    static executeTransform(node, context) {
        const config = node.config;
        
        switch (node.subtype) {
            case 'assign':
                return this.executeAssign(config, context);
            case 'format':
                return this.executeFormat(config, context);
            case 'extract':
                return this.executeExtract(config, context);
            default:
                return context;
        }
    }
    
    static executeAssign(config, context) {
        const value = this.resolveVariables(config.value, context);
        
        switch (config.mode) {
            case 'set':
                context[config.variable] = value;
                break;
            case 'append':
                context[config.variable] = (context[config.variable] || '') + value;
                break;
            case 'prepend':
                context[config.variable] = value + (context[config.variable] || '');
                break;
        }
        
        return context;
    }
    
    static executeFormat(config, context) {
        const inputData = this.getNestedValue(context, config.input);
        const template = config.template || '';
        
        // Simple template replacement
        let output = template;
        
        if (typeof inputData === 'object' && inputData !== null) {
            Object.keys(inputData).forEach(key => {
                output = output.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), inputData[key]);
            });
        } else {
            output = output.replace(/\{\{.*?\}\}/g, inputData);
        }
        
        context[config.output_var || 'formatted_data'] = output;
        return context;
    }
    
    static executeExtract(config, context) {
        const sourceData = this.getNestedValue(context, config.source);
        
        if (sourceData === undefined) {
            context[config.output_var || 'extracted_value'] = config.default_value || null;
            return context;
        }
        
        // Parse JSON path
        let result = sourceData;
        const pathParts = config.path.split(/\.|\[|\]/).filter(p => p);
        
        for (const part of pathParts) {
            if (result === undefined || result === null) break;
            
            // Check if it's an array index
            const arrayMatch = part.match(/^(\w+)\[(\d+)\]$/);
            if (arrayMatch) {
                const key = arrayMatch[1];
                const index = parseInt(arrayMatch[2]);
                result = result[key]?.[index];
            } else {
                result = result[part];
            }
        }
        
        context[config.output_var || 'extracted_value'] = result !== undefined ? result : config.default_value;
        return context;
    }
    
    static resolveVariables(template, context) {
        if (typeof template !== 'string') return template;
        
        return template.replace(/\{\{([^}]+)\}\}/g, (match, path) => {
            const value = this.getNestedValue(context, path.trim());
            return value !== undefined ? value : match;
        });
    }
    
    static getNestedValue(obj, path) {
        if (!path) return undefined;
        return path.split('.').reduce((current, key) => 
            current && current[key] !== undefined ? current[key] : undefined, obj);
    }
}

// Make it globally accessible
window.TransformNode = TransformNode;
