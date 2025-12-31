// 模板类型管理功能

let currentAddingLevel = 1; // 当前正在添加的层级（1/2/3）
let templateTypesHierarchy = {}; // 存储类型层级结构

// 加载模板类型列表
async function loadTemplateTypes() {
    // 检查是否已登录
    const token = typeof getToken === 'function' ? getToken() : null;
    if (!token) {
        // 未登录时使用默认数据
        templateTypesHierarchy = {
            '财务部': {
                '财务报表': ['日报', '周报', '月报'],
                '预算报表': ['年度预算', '季度预算']
            },
            '人事部': {
                '人事合同': ['劳动合同', '保密协议'],
                '员工档案': ['基本信息', '绩效考核']
            }
        };
        updateTypeSelectors();
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/templates/types`, {
            headers: typeof getAuthHeaders === 'function' ? getAuthHeaders() : {}
        });
        
        if (response.status === 401) {
            // 未授权，使用默认数据
            templateTypesHierarchy = {
                '财务部': {
                    '财务报表': ['日报', '周报', '月报'],
                    '预算报表': ['年度预算', '季度预算']
                },
                '人事部': {
                    '人事合同': ['劳动合同', '保密协议'],
                    '员工档案': ['基本信息', '绩效考核']
                }
            };
            updateTypeSelectors();
            return;
        }
        
        if (response.ok) {
            const data = await response.json();
            templateTypesHierarchy = data.types || {};
            updateTypeSelectors();
        } else {
            // 非200状态码，使用默认数据
            console.warn('加载模板类型失败，使用默认数据:', response.status);
            templateTypesHierarchy = {
                '财务部': {
                    '财务报表': ['日报', '周报', '月报'],
                    '预算报表': ['年度预算', '季度预算']
                },
                '人事部': {
                    '人事合同': ['劳动合同', '保密协议'],
                    '员工档案': ['基本信息', '绩效考核']
                }
            };
            updateTypeSelectors();
        }
    } catch (error) {
        console.error('加载模板类型错误:', error);
        // 初始化默认示例数据
        templateTypesHierarchy = {
            '财务部': {
                '财务报表': ['日报', '周报', '月报'],
                '预算报表': ['年度预算', '季度预算']
            },
            '人事部': {
                '人事合同': ['劳动合同', '保密协议'],
                '员工档案': ['基本信息', '绩效考核']
            }
        };
        updateTypeSelectors();
    }
}

// 更新类型选择器
function updateTypeSelectors() {
    const level1Select = document.getElementById('templateTypeLevel1');
    const level2Select = document.getElementById('templateTypeLevel2');
    const level3Select = document.getElementById('templateTypeLevel3');
    
    if (!level1Select) return;
    
    // 更新一级选择器
    level1Select.innerHTML = '<option value="">选择一级类型</option>';
    Object.keys(templateTypesHierarchy).forEach(key => {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = key;
        level1Select.appendChild(option);
    });
}

// 初始化模板类型选择器事件
function initTemplateTypeSelectors() {
    const level1Select = document.getElementById('templateTypeLevel1');
    const level2Select = document.getElementById('templateTypeLevel2');
    const level3Select = document.getElementById('templateTypeLevel3');
    
    if (!level1Select || !level2Select || !level3Select) return;
    
    // 一级选择改变时，更新二级选择器
    level1Select.addEventListener('change', function() {
        const level1Value = this.value;
        level2Select.innerHTML = '<option value="">选择二级类型</option>';
        level2Select.disabled = !level1Value;
        level3Select.innerHTML = '<option value="">选择三级类型（可选）</option>';
        level3Select.disabled = true;
        
        if (level1Value && templateTypesHierarchy[level1Value]) {
            Object.keys(templateTypesHierarchy[level1Value]).forEach(key => {
                const option = document.createElement('option');
                option.value = key;
                option.textContent = key;
                level2Select.appendChild(option);
            });
            level2Select.disabled = false;
        }
    });
    
    // 二级选择改变时，更新三级选择器
    level2Select.addEventListener('change', function() {
        const level1Value = level1Select.value;
        const level2Value = this.value;
        level3Select.innerHTML = '<option value="">选择三级类型（可选）</option>';
        level3Select.disabled = !level1Value || !level2Value;
        
        if (level1Value && level2Value && 
            templateTypesHierarchy[level1Value] && 
            templateTypesHierarchy[level1Value][level2Value]) {
            const level3Types = templateTypesHierarchy[level1Value][level2Value];
            if (Array.isArray(level3Types)) {
                level3Types.forEach(type => {
                    const option = document.createElement('option');
                    option.value = type;
                    option.textContent = type;
                    level3Select.appendChild(option);
                });
                level3Select.disabled = false;
            }
        }
    });
    
    // 添加类型按钮事件
    const addBtn1 = document.getElementById('addTypeLevel1Btn');
    const addBtn2 = document.getElementById('addTypeLevel2Btn');
    const addBtn3 = document.getElementById('addTypeLevel3Btn');
    
    if (addBtn1) {
        addBtn1.addEventListener('click', () => showTemplateTypeModal(1));
    }
    if (addBtn2) {
        addBtn2.addEventListener('click', () => {
            if (!level1Select.value) {
                alert('请先选择一级类型');
                return;
            }
            showTemplateTypeModal(2);
        });
    }
    if (addBtn3) {
        addBtn3.addEventListener('click', () => {
            if (!level1Select.value || !level2Select.value) {
                alert('请先选择一级和二级类型');
                return;
            }
            showTemplateTypeModal(3);
        });
    }
}

// 显示添加类型对话框
function showTemplateTypeModal(level) {
    currentAddingLevel = level;
    const modal = document.getElementById('templateTypeModal');
    const title = document.getElementById('templateTypeModalTitle');
    const label = document.getElementById('templateTypeModalLabel');
    const input = document.getElementById('templateTypeInput');
    
    if (!modal) return;
    
    const levelText = ['', '一级', '二级', '三级'][level];
    title.textContent = `添加${levelText}类型`;
    label.textContent = `${levelText}类型名称：`;
    input.value = '';
    input.placeholder = `请输入${levelText}类型名称，例如：${level === 1 ? '财务部' : level === 2 ? '财务报表' : '日报'}`;
    
    modal.style.display = 'block';
}

// 关闭添加类型对话框
function closeTemplateTypeModal() {
    const modal = document.getElementById('templateTypeModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// 保存模板类型
async function saveTemplateType() {
    const input = document.getElementById('templateTypeInput');
    const typeName = input.value.trim();
    
    if (!typeName) {
        alert('请输入类型名称');
        return;
    }
    
    try {
        const level1Select = document.getElementById('templateTypeLevel1');
        const level2Select = document.getElementById('templateTypeLevel2');
        
        let requestBody = {
            level: currentAddingLevel,
            name: typeName
        };
        
        if (currentAddingLevel === 2) {
            requestBody.parent_level1 = level1Select.value;
        } else if (currentAddingLevel === 3) {
            requestBody.parent_level1 = level1Select.value;
            requestBody.parent_level2 = level2Select.value;
        }
        
        const response = await fetch(`${API_BASE_URL}/api/templates/types`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        if (response.status === 401) {
            alert('登录已过期，请重新登录');
            removeToken();
            window.location.reload();
            return;
        }
        
        if (response.ok) {
            alert('类型添加成功');
            closeTemplateTypeModal();
            await loadTemplateTypes();
            
            // 自动选择新添加的类型
            if (currentAddingLevel === 1) {
                level1Select.value = typeName;
                level1Select.dispatchEvent(new Event('change'));
            } else if (currentAddingLevel === 2) {
                level2Select.value = typeName;
                level2Select.dispatchEvent(new Event('change'));
            } else if (currentAddingLevel === 3) {
                const level3Select = document.getElementById('templateTypeLevel3');
                if (level3Select) {
                    level3Select.value = typeName;
                }
            }
        } else {
            const error = await response.json().catch(() => ({ detail: '未知错误' }));
            alert('添加失败：' + (error.detail || '未知错误'));
        }
    } catch (error) {
        console.error('保存模板类型错误:', error);
        alert('添加失败：' + error.message);
    }
}

// 导出全局函数
window.closeTemplateTypeModal = closeTemplateTypeModal;
window.saveTemplateType = saveTemplateType;

