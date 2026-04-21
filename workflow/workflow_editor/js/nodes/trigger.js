/**
 * Trigger Node Module
 * Handles trigger node configurations
 */

class TriggerNode {
    static getConfig(type) {
        const configs = {
            schedule: {
                name: '定时触发',
                description: '按照 cron 表达式定时执行工作流',
                icon: '⏰',
                color: 'schedule',
                fields: [
                    {
                        name: 'cron',
                        label: 'Cron 表达式',
                        type: 'text',
                        default: '0 8 * * *',
                        placeholder: '分 时 日 月 周',
                        hint: '例如: 0 8 * * * 表示每天早上8点'
                    },
                    {
                        name: 'timezone',
                        label: '时区',
                        type: 'select',
                        default: 'Asia/Shanghai',
                        options: [
                            { value: 'Asia/Shanghai', label: '中国 (Asia/Shanghai)' },
                            { value: 'Asia/Tokyo', label: '日本 (Asia/Tokyo)' },
                            { value: 'America/New_York', label: '美国东部 (America/New_York)' },
                            { value: 'Europe/London', label: '英国 (Europe/London)' },
                            { value: 'UTC', label: 'UTC' }
                        ]
                    }
                ]
            },
            event: {
                name: '事件触发',
                description: '当特定事件发生时触发工作流',
                icon: '⚡',
                color: 'event',
                fields: [
                    {
                        name: 'event',
                        label: '事件名称',
                        type: 'text',
                        default: '',
                        placeholder: '例如: user.login, order.created',
                        hint: '指定触发的事件类型'
                    },
                    {
                        name: 'source',
                        label: '事件来源',
                        type: 'select',
                        default: 'any',
                        options: [
                            { value: 'any', label: '任意来源' },
                            { value: 'user', label: '用户操作' },
                            { value: 'system', label: '系统事件' },
                            { value: 'api', label: 'API 调用' }
                        ]
                    },
                    {
                        name: 'filter',
                        label: '过滤条件 (可选)',
                        type: 'textarea',
                        default: '',
                        placeholder: '{"key": "value"}',
                        hint: 'JSON 格式的事件过滤条件'
                    }
                ]
            },
            webhook: {
                name: 'Webhook 触发',
                description: '接收 HTTP 请求触发工作流',
                icon: '🪝',
                color: 'webhook',
                fields: [
                    {
                        name: 'path',
                        label: 'Webhook 路径',
                        type: 'text',
                        default: '/webhook/trigger',
                        placeholder: '/webhook/mytrigger',
                        hint: 'HTTP 请求路径'
                    },
                    {
                        name: 'method',
                        label: 'HTTP 方法',
                        type: 'select',
                        default: 'POST',
                        options: [
                            { value: 'POST', label: 'POST' },
                            { value: 'GET', label: 'GET' },
                            { value: 'PUT', label: 'PUT' }
                        ]
                    },
                    {
                        name: 'auth',
                        label: '认证方式',
                        type: 'select',
                        default: 'none',
                        options: [
                            { value: 'none', label: '无' },
                            { value: 'header', label: '请求头认证' },
                            { value: 'bearer', label: 'Bearer Token' }
                        ]
                    }
                ]
            }
        };
        
        return configs[type] || configs.schedule;
    }
    
    static renderConfigForm(node) {
        const config = this.getConfig(node.subtype);
        let html = '';
        
        config.fields.forEach(field => {
            html += `<div class="form-group">`;
            html += `<label class="form-label">${field.label}</label>`;
            
            if (field.type === 'text') {
                html += `<input type="text" class="form-input" 
                    id="trigger_${field.name}" 
                    value="${node.config[field.name] || field.default}"
                    placeholder="${field.placeholder || ''}">`;
            } else if (field.type === 'select') {
                html += `<select class="form-select" id="trigger_${field.name}">`;
                field.options.forEach(opt => {
                    const selected = (node.config[field.name] || field.default) === opt.value ? 'selected' : '';
                    html += `<option value="${opt.value}" ${selected}>${opt.label}</option>`;
                });
                html += `</select>`;
            } else if (field.type === 'textarea') {
                html += `<textarea class="form-textarea" 
                    id="trigger_${field.name}" 
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
        return {
            cron: document.getElementById('trigger_cron')?.value || '',
            timezone: document.getElementById('trigger_timezone')?.value || 'UTC',
            event: document.getElementById('trigger_event')?.value || '',
            source: document.getElementById('trigger_source')?.value || 'any',
            filter: document.getElementById('trigger_filter')?.value || '',
            path: document.getElementById('trigger_path')?.value || '',
            method: document.getElementById('trigger_method')?.value || 'POST',
            auth: document.getElementById('trigger_auth')?.value || 'none'
        };
    }
    
    static validateConfig(node) {
        const errors = [];
        
        if (node.subtype === 'schedule') {
            if (!node.config.cron) {
                errors.push('Cron 表达式不能为空');
            } else if (!this.validateCron(node.config.cron)) {
                errors.push('Cron 表达式格式无效');
            }
        } else if (node.subtype === 'event') {
            if (!node.config.event) {
                errors.push('事件名称不能为空');
            }
        } else if (node.subtype === 'webhook') {
            if (!node.config.path) {
                errors.push('Webhook 路径不能为空');
            }
        }
        
        return errors;
    }
    
    static validateCron(cron) {
        // Basic cron validation
        const parts = cron.split(/\s+/);
        if (parts.length !== 5) return false;
        
        // Simplified validation - just check if all parts are non-empty
        return parts.every(part => part !== '' && /^[0-9*,/-]+$/.test(part));
    }
    
    static describeSchedule(cron, timezone) {
        const parts = cron.split(/\s+/);
        if (parts.length !== 5) return '无效的 Cron 表达式';
        
        const [minute, hour, day, month, weekday] = parts;
        
        const weekdayNames = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
        const monthNames = ['', '1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
        
        let desc = [];
        
        // Time
        if (minute === '*' && hour === '*') {
            desc.push('每分钟');
        } else if (minute === '0' && hour === '*') {
            desc.push('每小时整点');
        } else if (minute !== '*' && hour !== '*') {
            desc.push(`${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`);
        } else if (hour !== '*') {
            desc.push(`${hour}点`);
        }
        
        // Day of week
        if (weekday !== '*') {
            const dayIndex = parseInt(weekday);
            if (!isNaN(dayIndex) && dayIndex >= 0 && dayIndex <= 6) {
                desc.push(weekdayNames[dayIndex]);
            }
        }
        
        // Day of month
        if (day !== '*') {
            desc.push(`每月${day}日`);
        }
        
        // Month
        if (month !== '*') {
            const monthIndex = parseInt(month);
            if (!isNaN(monthIndex) && monthIndex >= 1 && monthIndex <= 12) {
                desc.push(monthNames[monthIndex]);
            }
        }
        
        return desc.join(' ') || '未配置的定时任务';
    }
}

// Make it globally accessible
window.TriggerNode = TriggerNode;
