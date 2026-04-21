/**
 * Action Node Module
 * Handles action node configurations
 */

class ActionNode {
    static getConfig(type) {
        const configs = {
            send_message: {
                name: '发送消息',
                description: '向指定渠道发送消息',
                icon: '💬',
                color: 'action',
                fields: [
                    {
                        name: 'channel',
                        label: '目标渠道',
                        type: 'text',
                        default: 'default',
                        placeholder: 'default, email, sms, wechat...',
                        hint: '消息发送的目标渠道'
                    },
                    {
                        name: 'template',
                        label: '消息模板',
                        type: 'textarea',
                        default: '',
                        placeholder: '你好，{{user_name}}！今天是{{date}}。',
                        hint: '支持 {{variable}} 变量插值'
                    },
                    {
                        name: 'priority',
                        label: '优先级',
                        type: 'select',
                        default: 'normal',
                        options: [
                            { value: 'low', label: '低' },
                            { value: 'normal', label: '普通' },
                            { value: 'high', label: '高' },
                            { value: 'urgent', label: '紧急' }
                        ]
                    }
                ]
            },
            call_skill: {
                name: '调用技能',
                description: '调用已安装的 AI 技能',
                icon: '🎯',
                color: 'action',
                fields: [
                    {
                        name: 'skill',
                        label: '技能名称',
                        type: 'text',
                        default: '',
                        placeholder: '例如: weather, translator, calculator',
                        hint: '选择要调用的技能'
                    },
                    {
                        name: 'params',
                        label: '技能参数',
                        type: 'textarea',
                        default: '{}',
                        placeholder: '{"key": "value"}',
                        hint: '传递给技能的参数 (JSON 格式)'
                    },
                    {
                        name: 'output_var',
                        label: '输出变量名',
                        type: 'text',
                        default: 'skill_result',
                        placeholder: 'result',
                        hint: '存储技能返回结果的变量名'
                    }
                ]
            },
            get_info: {
                name: '获取信息',
                description: '从外部来源获取信息',
                icon: '🔍',
                color: 'action',
                fields: [
                    {
                        name: 'source',
                        label: '信息来源',
                        type: 'select',
                        default: 'weather',
                        options: [
                            { value: 'weather', label: '天气' },
                            { value: 'news', label: '新闻' },
                            { value: 'stock', label: '股票' },
                            { value: 'calendar', label: '日历' },
                            { value: 'custom', label: '自定义 API' }
                        ]
                    },
                    {
                        name: 'location',
                        label: '位置 (天气用)',
                        type: 'text',
                        default: '',
                        placeholder: '北京',
                        hint: '获取天气的城市'
                    },
                    {
                        name: 'output_var',
                        label: '输出变量名',
                        type: 'text',
                        default: 'info_result',
                        placeholder: 'result',
                        hint: '存储获取结果的变量名'
                    }
                ]
            },
            generate: {
                name: '生成内容',
                description: '使用 AI 生成内容',
                icon: '✨',
                color: 'action',
                fields: [
                    {
                        name: 'prompt',
                        label: '生成提示词',
                        type: 'textarea',
                        default: '',
                        placeholder: '生成一段关于{{topic}}的简介...',
                        hint: 'AI 内容生成的提示词'
                    },
                    {
                        name: 'model',
                        label: 'AI 模型',
                        type: 'select',
                        default: 'default',
                        options: [
                            { value: 'default', label: '默认模型' },
                            { value: 'gpt-4', label: 'GPT-4' },
                            { value: 'claude-3', label: 'Claude 3' },
                            { value: 'gemini', label: 'Gemini Pro' }
                        ]
                    },
                    {
                        name: 'max_tokens',
                        label: '最大生成长度',
                        type: 'number',
                        default: 1000,
                        hint: '生成内容的最大 token 数'
                    },
                    {
                        name: 'output_var',
                        label: '输出变量名',
                        type: 'text',
                        default: 'generated_content',
                        placeholder: 'content',
                        hint: '存储生成结果的变量名'
                    }
                ]
            },
            api: {
                name: '调用 API',
                description: '向外部 HTTP API 发送请求',
                icon: '🌐',
                color: 'action',
                fields: [
                    {
                        name: 'url',
                        label: 'API 地址',
                        type: 'text',
                        default: '',
                        placeholder: 'https://api.example.com/endpoint',
                        hint: '完整的 API 请求地址'
                    },
                    {
                        name: 'method',
                        label: 'HTTP 方法',
                        type: 'select',
                        default: 'GET',
                        options: [
                            { value: 'GET', label: 'GET' },
                            { value: 'POST', label: 'POST' },
                            { value: 'PUT', label: 'PUT' },
                            { value: 'DELETE', label: 'DELETE' },
                            { value: 'PATCH', label: 'PATCH' }
                        ]
                    },
                    {
                        name: 'headers',
                        label: '请求头',
                        type: 'textarea',
                        default: '{"Content-Type": "application/json"}',
                        placeholder: '{"key": "value"}',
                        hint: 'HTTP 请求头 (JSON 格式)'
                    },
                    {
                        name: 'body',
                        label: '请求体',
                        type: 'textarea',
                        default: '',
                        placeholder: '{"key": "value"}',
                        hint: 'POST/PUT 请求体 (JSON 格式)'
                    },
                    {
                        name: 'output_var',
                        label: '输出变量名',
                        type: 'text',
                        default: 'api_response',
                        placeholder: 'response',
                        hint: '存储 API 响应的变量名'
                    }
                ]
            }
        };
        
        return configs[type] || configs.send_message;
    }
    
    static renderConfigForm(node) {
        const config = this.getConfig(node.subtype);
        let html = '';
        
        config.fields.forEach(field => {
            html += `<div class="form-group">`;
            html += `<label class="form-label">${field.label}</label>`;
            
            if (field.type === 'text') {
                html += `<input type="text" class="form-input" 
                    id="action_${field.name}" 
                    value="${node.config[field.name] || field.default}"
                    placeholder="${field.placeholder || ''}">`;
            } else if (field.type === 'number') {
                html += `<input type="number" class="form-input" 
                    id="action_${field.name}" 
                    value="${node.config[field.name] || field.default}">`;
            } else if (field.type === 'select') {
                html += `<select class="form-select" id="action_${field.name}">`;
                field.options.forEach(opt => {
                    const selected = (node.config[field.name] || field.default) === opt.value ? 'selected' : '';
                    html += `<option value="${opt.value}" ${selected}>${opt.label}</option>`;
                });
                html += `</select>`;
            } else if (field.type === 'textarea') {
                html += `<textarea class="form-textarea" 
                    id="action_${field.name}" 
                    placeholder="${field.placeholder || ''}">${node.config[field.name] || field.default}</textarea>`;
            }
            
            if (field.hint) {
                html += `<p class="form-hint">${field.hint}</p>`;
            }
            
            html += `</div>`;
        });
        
        return html;
    }
    
    static getConfigFromForm() {
        const config = {};
        
        // Get all form fields starting with action_
        const fields = document.querySelectorAll('[id^="action_"]');
        fields.forEach(field => {
            const key = field.id.replace('action_', '');
            config[key] = field.type === 'number' ? parseInt(field.value) : field.value;
        });
        
        return config;
    }
    
    static validateConfig(node) {
        const errors = [];
        
        switch (node.subtype) {
            case 'send_message':
                if (!node.config.channel) {
                    errors.push('目标渠道不能为空');
                }
                break;
                
            case 'call_skill':
                if (!node.config.skill) {
                    errors.push('技能名称不能为空');
                }
                break;
                
            case 'api':
                if (!node.config.url) {
                    errors.push('API 地址不能为空');
                } else if (!this.isValidUrl(node.config.url)) {
                    errors.push('API 地址格式无效');
                }
                break;
                
            case 'generate':
                if (!node.config.prompt) {
                    errors.push('生成提示词不能为空');
                }
                break;
        }
        
        return errors;
    }
    
    static isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }
    
    static describeAction(node) {
        const descriptions = {
            send_message: `发送消息到 ${node.config.channel || '默认'} 渠道`,
            call_skill: `调用技能: ${node.config.skill || '未指定'}`,
            get_info: `获取 ${node.config.source || '信息'}`,
            generate: `使用 AI 生成内容`,
            api: `调用 API: ${node.config.method || 'GET'} ${node.config.url || ''}`
        };
        
        return descriptions[node.subtype] || '未配置的动作';
    }
}

// Make it globally accessible
window.ActionNode = ActionNode;
