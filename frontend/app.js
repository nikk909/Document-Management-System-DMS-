// API 基础 URL
const API_BASE_URL = 'http://localhost:8000';

// Token 管理
function getToken() {
    return localStorage.getItem('auth_token');
}

function setToken(token) {
    localStorage.setItem('auth_token', token);
}

function removeToken() {
    localStorage.removeItem('auth_token');
}

function getAuthHeaders(includeContentType = true) {
    const token = getToken();
    const headers = {};
    if (includeContentType) {
        headers['Content-Type'] = 'application/json';
    }
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

// 全局状态
let currentPage = 1;
let pageSize = 10;
let totalFiles = 0;
let selectedFileId = null;
let currentTab = 'fileManagement';
let currentUser = null;

// 模板管理状态
let templateCurrentPage = 1;
let selectedTemplateId = null;

// 文档生成状态
let currentGenerationStep = 1;
let selectedTemplateForGeneration = null;
let uploadedDataFile = null;
let selectedDataFileId = null; // 从文件列表选择的文件ID

// 访问日志状态
let logCurrentPage = 1;

// 用户管理状态
let userCurrentPage = 1;
let totalUsers = 0;

// 生成的文档状态
let generatedCurrentPage = 1;
let selectedGeneratedDocId = null;

// 图片管理状态
let imageCurrentPage = 1;
let imagePageSize = 20;

// ==================== 工具函数 ====================
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', function() {
    initLogin();
    initMainPage();
    initTabNavigation();
    // 延迟加载数据，避免在未登录时触发401错误
    setTimeout(() => {
        const token = getToken();
        if (token) {
            loadCategories();
            loadTemplates();
        }
    }, 2000);
    initImageManagement();
});

// ==================== 登录功能 ====================

function initLogin() {
    // 检查是否已登录（延迟检查，静默模式，避免后端未启动时频繁弹窗）
    setTimeout(() => {
        checkLoginStatus(true); // 静默模式，不弹窗
    }, 1000);
    
    const loginForm = document.getElementById('loginForm');
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        
        if (!username || !password) {
            alert('请输入用户名和密码');
            return;
        }
        
        // 显示加载状态
        const submitBtn = loginForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = '登录中...';
        
        try {
            console.log('开始登录请求，URL:', `${API_BASE_URL}/api/auth/login`);
            const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password })
            });
            
            console.log('收到响应，状态码:', response.status, '状态文本:', response.statusText);
            
            // 检查响应是否成功
            if (!response.ok) {
                // 尝试解析错误响应
                let errorMessage = '登录失败';
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
                } catch (e) {
                    errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                }
                alert('登录失败：' + errorMessage);
                return;
            }
            
            // 解析成功响应
            let data;
            try {
                const text = await response.text();
                console.log('响应内容:', text);
                data = JSON.parse(text);
            } catch (e) {
                console.error('解析响应JSON失败:', e);
                alert('登录失败：服务器返回了无效的响应格式');
                return;
            }
            
            if (data.success) {
                // 保存 token 和用户信息
                setToken(data.token);
                currentUser = data.user;
                console.log('登录成功，用户:', data.user);
                
                // 切换到主界面
                document.getElementById('loginPage').style.display = 'none';
                document.getElementById('mainPage').style.display = 'flex';
                document.getElementById('usernameDisplay').textContent = data.user.display_name || data.user.username;
                
                // 如果是管理员，显示用户管理标签页
                if (data.user.role === 'admin') {
                    const userManagementTabBtn = document.getElementById('userManagementTabBtn');
                    if (userManagementTabBtn) {
                        userManagementTabBtn.style.display = 'inline-block';
                    }
                }
                
                // 清空登录表单
                loginForm.reset();
                
                // 延迟加载数据，避免立即触发401检查
                setTimeout(() => {
                    loadFiles();
                    loadCategories();
                }, 500);
            } else {
                alert('登录失败：' + (data.detail || data.message || '用户名或密码错误'));
            }
        } catch (error) {
            console.error('登录错误:', error);
            console.error('错误详情:', error.message, error.stack);
            let errorMsg = '登录失败：网络错误';
            if (error.message) {
                errorMsg += ' - ' + error.message;
            }
            errorMsg += '\n\n请检查：\n1. 后端服务是否在 http://localhost:8000 运行\n2. 浏览器控制台是否有更多错误信息';
            alert(errorMsg);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });
}

async function checkLoginStatus(silent = false) {
    const token = getToken();
    if (!token) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
            method: 'GET',
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const userData = await response.json();
            currentUser = userData;
            document.getElementById('loginPage').style.display = 'none';
            document.getElementById('mainPage').style.display = 'flex';
            document.getElementById('usernameDisplay').textContent = userData.display_name || userData.username;
            
            // 如果是管理员，显示用户管理标签页
            if (userData.role === 'admin') {
                const userManagementTabBtn = document.getElementById('userManagementTabBtn');
                if (userManagementTabBtn) {
                    userManagementTabBtn.style.display = 'inline-block';
                }
            }
            
            loadFiles();
        } else {
            // Token 无效，静默清除（不弹窗，因为可能是首次访问或自动检查）
            removeToken();
            if (!silent) {
                // 只在非静默模式下才弹窗
                console.log('登录已过期，请重新登录');
            }
        }
    } catch (error) {
        // 网络错误时，不清除token，可能是后端未启动
        if (!silent) {
            console.error('检查登录状态错误（可能是后端未启动）:', error);
        }
        // 不调用 removeToken()，避免清除有效的token
    }
}

function logout() {
    removeToken();
    currentUser = null;
    document.getElementById('loginPage').style.display = 'flex';
    document.getElementById('mainPage').style.display = 'none';
    document.getElementById('loginForm').reset();
}

// ==================== 标签页导航 ====================

function initTabNavigation() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabName = this.dataset.tab;
            if (!tabName) {
                console.error('标签按钮缺少 data-tab 属性');
                return;
            }
            console.log('切换到标签页:', tabName);
            try {
                switchTab(tabName);
            } catch (error) {
                console.error('切换标签页错误:', error);
                alert('切换标签页失败：' + error.message);
            }
        });
    });
    
    // 检查所有必需的标签页是否存在
    const requiredTabs = ['fileManagement', 'templateManagement', 'documentGeneration', 'generatedDocuments', 'accessLog'];
    requiredTabs.forEach(tabName => {
        const tabElement = document.getElementById(tabName + 'Tab');
        if (!tabElement) {
            console.error(`标签页元素 ${tabName}Tab 未找到`);
        }
    });
}

function switchTab(tabName) {
    currentTab = tabName;
    
    // 更新标签按钮状态
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tabName) {
            btn.classList.add('active');
        }
    });
    
    // 更新标签页内容
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    const targetTab = document.getElementById(tabName + 'Tab');
    if (targetTab) {
        targetTab.classList.add('active');
    } else {
        console.error(`标签页 ${tabName}Tab 未找到`);
        alert(`无法找到标签页：${tabName}`);
        return;
    }
    
    // 根据标签页加载数据
    switch(tabName) {
        case 'fileManagement':
            loadFiles();
            break;
        case 'templateManagement':
            loadTemplates();
            break;
        case 'imageManagement':
            loadImages();
            break;
        case 'documentGeneration':
            initDocumentGeneration();
            break;
        case 'generatedDocuments':
            loadGeneratedDocuments();
            break;
        case 'accessLog':
            loadAccessLogs();
            break;
        case 'categoryManagement':
            loadCategoryManagement();
            break;
        case 'userManagement':
            loadUsers(1);
            break;
    }
}

// ==================== 主界面初始化 ====================

function initMainPage() {
    // 筛选按钮
    // 文件管理筛选（类似模板管理，自动筛选）
    const categoryFilter = document.getElementById('categoryFilter');
    const keywordSearch = document.getElementById('keywordSearch');
    
    if (categoryFilter) {
        categoryFilter.addEventListener('change', () => {
            currentPage = 1;
            loadFiles();
        });
    }
    
    if (keywordSearch) {
        let searchTimeout;
        keywordSearch.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentPage = 1;
                loadFiles();
            }, 500);
        });
    }
    
    // 重置按钮（移除，因为现在是自动筛选）
    // 注意：resetBtn 和 batchOperationBtn 已在HTML中移除，所以不再需要绑定事件
    
    // 一键清空文件列表按钮
    const clearFilesBtn = document.getElementById('clearFilesBtn');
    if (clearFilesBtn) {
        clearFilesBtn.addEventListener('click', async function() {
        if (confirm('⚠️ 警告：确定要清空所有文件吗？\n\n此操作将：\n- 删除MySQL中的所有文件记录\n- 删除MinIO中的所有文件\n\n此操作不可恢复！')) {
            try {
                const response = await fetch(`${API_BASE_URL}/api/files/clear-all`, {
                    method: 'DELETE',
                    headers: getAuthHeaders()
                });
                
                // 处理401认证错误
                if (response.status === 401) {
                    console.error('认证失败，请重新登录');
                    removeToken();
                    // 只在主界面已显示时才弹窗，避免登录过程中弹窗
                    const mainPage = document.getElementById('mainPage');
                    if (mainPage && mainPage.style.display !== 'none') {
                    alert('登录已过期，请重新登录');
                    window.location.reload();
                    }
                    return;
                }
                
                if (!response.ok) {
                    let errorMessage = '清空失败';
                    try {
                        const errorData = await response.json();
                        errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
                    } catch (e) {
                        // 如果响应不是JSON，使用状态文本
                        errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                    }
                    throw new Error(errorMessage);
                }
                
                const data = await response.json();
                alert(`✅ ${data.message}\n\n已删除 ${data.deleted_mysql} 条MySQL记录，${data.deleted_minio} 个MinIO文件`);
                
                // 清空前端显示
                const fileList = document.getElementById('fileList');
                fileList.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">列表已清空</div>';
                const pagination = document.getElementById('pagination');
                pagination.innerHTML = '';
                selectedFileId = null;
                document.getElementById('fileDetailPanel').style.display = 'none';
                totalFiles = 0;
            } catch (error) {
                console.error('清空文件错误:', error);
                // 确保错误消息是字符串
                let errorMessage = '未知错误';
                if (error instanceof Error) {
                    errorMessage = error.message;
                } else if (typeof error === 'string') {
                    errorMessage = error;
                } else if (error && error.detail) {
                    errorMessage = error.detail;
                } else if (error && error.message) {
                    errorMessage = error.message;
                } else {
                    errorMessage = JSON.stringify(error);
                }
                alert('❌ 清空失败：' + errorMessage);
            }
        }
        });
    }
    
    // 刷新页面按钮（单击刷新页面）
    const refreshBtn = document.getElementById('refreshFilesBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // 简单刷新页面，不再调用重启API
            // 如果需要重启后端，请手动重启或使用其他方式
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<span class="refresh-icon">⏳</span>';
            
            // 立即刷新页面
            window.location.reload(true);
        });
    } else {
        console.error('刷新按钮未找到！');
    }
    
    // 退出重登按钮
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            if (confirm('确定要退出登录吗？')) {
                logout();
            }
        });
    }
    
    // 一键清空所有数据按钮
    const clearAllDataBtn = document.getElementById('clearAllDataBtn');
    if (clearAllDataBtn) {
        clearAllDataBtn.addEventListener('click', async function() {
        if (confirm('⚠️ 警告：确定要清空所有数据吗？\n\n此操作将删除：\n- 所有文件（MySQL记录 + MinIO文件）\n- 所有模板（MySQL记录 + MinIO文件）\n- 所有生成的文档（MySQL记录 + MinIO文件）\n- 所有访问日志（MySQL记录 + MinIO文件）\n\n注意：\n- MinIO桶不会被删除\n- 用户表不会被删除\n\n此操作不可恢复！')) {
            if (!confirm('⚠️ 再次确认：您确定要清空所有数据吗？\n\n这将删除系统中的所有文件、模板、生成的文档和日志！')) {
                return;
            }
            
            try {
                const response = await fetch(`${API_BASE_URL}/api/system/clear-all`, {
                    method: 'DELETE',
                    headers: getAuthHeaders()
                });
                
                // 处理401认证错误
                if (response.status === 401) {
                    console.error('认证失败，请重新登录');
                    removeToken();
                    // 只在主界面已显示时才弹窗，避免登录过程中弹窗
                    const mainPage = document.getElementById('mainPage');
                    if (mainPage && mainPage.style.display !== 'none') {
                    alert('登录已过期，请重新登录');
                    window.location.reload();
                    }
                    return;
                }
                
                if (!response.ok) {
                    let errorMessage = '清空失败';
                    try {
                        const errorData = await response.json();
                        errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
                    } catch (e) {
                        // 如果响应不是JSON，使用状态文本
                        errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                    }
                    throw new Error(errorMessage);
                }
                
                const data = await response.json();
                
                // 显示详细结果
                let message = `✅ ${data.message}\n\n详细统计：\n`;
                message += `文件：MySQL ${data.stats.documents.mysql} 条，MinIO ${data.stats.documents.minio} 个\n`;
                message += `模板：MySQL ${data.stats.templates.mysql} 条，MinIO ${data.stats.templates.minio} 个\n`;
                message += `生成的文档：MySQL ${data.stats.generated_documents.mysql} 条，MinIO ${data.stats.generated_documents.minio} 个\n`;
                message += `访问日志：MySQL ${data.stats.access_logs.mysql} 条，MinIO ${data.stats.access_logs.minio} 个\n`;
                message += `\n总计：MySQL ${data.total.mysql} 条，MinIO ${data.total.minio} 个`;
                
                alert(message);
                
                // 清空前端显示
                // 清空文件列表
                const fileList = document.getElementById('fileList');
                if (fileList) {
                    fileList.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">列表已清空</div>';
                }
                const pagination = document.getElementById('pagination');
                if (pagination) {
                    pagination.innerHTML = '';
                }
                
                // 清空模板列表
                const templateList = document.getElementById('templateList');
                if (templateList) {
                    templateList.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">列表已清空</div>';
                }
                const templatePagination = document.getElementById('templatePagination');
                if (templatePagination) {
                    templatePagination.innerHTML = '';
                }
                
                // 清空生成的文档列表
                const generatedDocumentList = document.getElementById('generatedDocumentList');
                if (generatedDocumentList) {
                    generatedDocumentList.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">列表已清空</div>';
                }
                const generatedPagination = document.getElementById('generatedPagination');
                if (generatedPagination) {
                    generatedPagination.innerHTML = '';
                }
                
                // 清空访问日志列表
                const logList = document.getElementById('logList');
                if (logList) {
                    logList.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">列表已清空</div>';
                }
                const logPagination = document.getElementById('logPagination');
                if (logPagination) {
                    logPagination.innerHTML = '';
                }
                
                // 重置选中状态
                selectedFileId = null;
                selectedTemplateId = null;
                selectedGeneratedDocId = null;
                
                // 隐藏详情面板
                const fileDetailPanel = document.getElementById('fileDetailPanel');
                if (fileDetailPanel) {
                    fileDetailPanel.style.display = 'none';
                }
                const templateDetailSection = document.getElementById('templateDetailSection');
                if (templateDetailSection) {
                    templateDetailSection.style.display = 'none';
                }
                const generatedDetailPanel = document.getElementById('generatedDetailPanel');
                if (generatedDetailPanel) {
                    generatedDetailPanel.style.display = 'none';
                }
                
                // 重置计数
                totalFiles = 0;
                
                // 刷新当前标签页的数据
                if (currentTab === 'fileManagement') {
                    loadFiles();
                } else if (currentTab === 'templateManagement') {
                    loadTemplates();
                } else if (currentTab === 'generatedDocuments') {
                    loadGeneratedDocuments();
                } else if (currentTab === 'accessLog') {
                    loadAccessLogs();
                }
            } catch (error) {
                console.error('清空所有数据错误:', error);
                // 确保错误消息是字符串
                let errorMessage = '未知错误';
                if (error instanceof Error) {
                    errorMessage = error.message;
                } else if (typeof error === 'string') {
                    errorMessage = error;
                } else if (error && error.detail) {
                    errorMessage = error.detail;
                } else if (error && error.message) {
                    errorMessage = error.message;
                } else {
                    errorMessage = JSON.stringify(error);
                }
                alert('❌ 清空失败：' + errorMessage);
            }
        }
        });
    }
    
    // 文件上传
    initFileUpload();
}

// ==================== 文件列表 ====================

async function loadFiles() {
    const keyword = document.getElementById('keywordSearch')?.value || '';
    const category = document.getElementById('categoryFilter')?.value || '';
    
    try {
        let url = `${API_BASE_URL}/api/files?page=${currentPage}&page_size=${pageSize}`;
        if (keyword) url += `&keyword=${encodeURIComponent(keyword)}`;
        if (category) url += `&category=${encodeURIComponent(category)}`;
        
        const response = await fetch(url, {
            headers: getAuthHeaders(),
            cache: 'no-cache' // 禁用缓存，强制从服务器获取最新数据
        });
        
        // 处理401认证错误
        if (response.status === 401) {
            console.error('认证失败，请重新登录');
            removeToken();
            // 只在主界面已显示时才弹窗，避免登录过程中弹窗
            const mainPage = document.getElementById('mainPage');
            if (mainPage && mainPage.style.display !== 'none') {
            alert('登录已过期，请重新登录');
            window.location.reload();
            }
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('文件列表响应:', data);
        console.log('文件数量:', data.files?.length || 0, '总数:', data.total || 0);
        
        totalFiles = data.total || 0;
        renderFileList(data.files || []);
        renderPagination();
    } catch (error) {
        console.error('加载文件列表错误:', error);
        // 显示空列表
        renderFileList([]);
        totalFiles = 0;
        renderPagination();
    }
}

function renderFileList(files) {
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '';
    
    if (files.length === 0) {
        fileList.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">暂无文件</div>';
        return;
    }
    
    files.forEach(file => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.dataset.fileId = file.id;
        
        const uploader = file.uploader || file.created_by || '系统';
        const archivedTag = file.is_archived ? '<span class="file-tag" style="background-color: #ffc107;">已归档</span>' : '';
        
        fileItem.innerHTML = `
            <div class="file-name">${file.filename} ${archivedTag}</div>
            <div class="file-tags">
                <span class="file-tag">版本: ${file.version}</span>
                <span class="file-tag">上传: ${file.upload_time}</span>
                ${file.category ? `<span class="file-tag">${file.category}</span>` : ''}
                ${file.tags && file.tags.length > 0 ? file.tags.map(tag => `<span class="file-tag">${tag}</span>`).join('') : ''}
            </div>
            <div class="file-uploader">上传人: ${uploader}</div>
            <div class="file-actions">
                <button class="btn btn-small btn-primary" onclick="event.stopPropagation(); handleFileAction(${file.id}, 'download')" style="margin-right: 5px;">下载</button>
                <button class="btn btn-small btn-secondary" onclick="event.stopPropagation(); handleFileAction(${file.id}, 'rename')" style="margin-right: 5px;">重命名</button>
                <button class="btn btn-small btn-secondary" onclick="event.stopPropagation(); handleFileAction(${file.id}, 'changeCategory')" style="margin-right: 5px;">更改分类</button>
                <button class="btn btn-small btn-danger" onclick="event.stopPropagation(); handleFileAction(${file.id}, 'delete')">删除</button>
            </div>
        `;
        
        fileItem.addEventListener('click', function(e) {
            if (e.target.closest('.file-actions') || e.target.closest('.file-action-menu')) {
                return;
            }
            document.querySelectorAll('.file-item').forEach(item => {
                item.classList.remove('selected');
            });
            fileItem.classList.add('selected');
            selectedFileId = file.id;
            showFileDetail(file);
        });
        
        fileList.appendChild(fileItem);
    });
}

// 显示文件详情
async function showFileDetail(file) {
    const detailPanel = document.getElementById('fileDetailPanel');
    const detailContent = document.getElementById('fileDetailContent');
    
    detailPanel.style.display = 'block';
    detailContent.innerHTML = '<div style="text-align: center; padding: 20px;">加载中...</div>';
    
    // 从API获取完整详情
    try {
        const response = await fetch(`${API_BASE_URL}/api/files/${file.id}`, {
            headers: getAuthHeaders()
        });
        
        // 处理401认证错误
        if (response.status === 401) {
            console.error('认证失败，请重新登录');
            removeToken();
            alert('登录已过期，请重新登录');
            window.location.reload();
            return;
        }
        
        if (response.ok) {
            const fileDetail = await response.json();
            detailContent.innerHTML = `
                <div class="detail-item">
                    <strong>文件名：</strong>
                    <span>${fileDetail.filename}</span>
                </div>
                <div class="detail-item">
                    <strong>版本：</strong>
                    <span>${fileDetail.version}</span>
                </div>
                <div class="detail-item">
                    <strong>分类：</strong>
                    <span>${fileDetail.category || '-'}</span>
                </div>
                <div class="detail-item">
                    <strong>标签：</strong>
                    <span>${fileDetail.tags ? fileDetail.tags.join(', ') : '-'}</span>
                </div>
                <div class="detail-item">
                    <strong>上传人：</strong>
                    <span>${fileDetail.uploader || '系统'}</span>
                </div>
                <div class="detail-item">
                    <strong>上传时间：</strong>
                    <span>${fileDetail.upload_time}</span>
                </div>
                <div class="detail-item">
                    <strong>归档状态：</strong>
                    <span>${fileDetail.is_archived ? '已归档（只读）' : '未归档'}</span>
                </div>
                <div class="detail-item">
                    <strong>描述：</strong>
                    <span>${fileDetail.description || '-'}</span>
                </div>
                <div class="detail-item">
                    <strong>存储位置：</strong>
                    <div style="margin-top: 5px; font-size: 12px;">
                        <div>MinIO: ${fileDetail.minio_path || '-'}</div>
                        <div>MySQL ID: ${fileDetail.db_id || '-'}</div>
                    </div>
                </div>
            `;
        } else {
            // 使用传入的文件信息
            detailContent.innerHTML = `
                <div class="detail-item">
                    <strong>文件名：</strong>
                    <span>${file.filename}</span>
                </div>
                <div class="detail-item">
                    <strong>版本：</strong>
                    <span>${file.version}</span>
                </div>
                <div class="detail-item">
                    <strong>分类：</strong>
                    <span>${file.category || '-'}</span>
                </div>
                <div class="detail-item">
                    <strong>标签：</strong>
                    <span>${file.tags ? file.tags.join(', ') : '-'}</span>
                </div>
                <div class="detail-item">
                    <strong>上传人：</strong>
                    <span>${file.uploader || '系统'}</span>
                </div>
                <div class="detail-item">
                    <strong>上传时间：</strong>
                    <span>${file.upload_time}</span>
                </div>
            `;
        }
    } catch (error) {
        console.error('获取文件详情错误:', error);
        detailContent.innerHTML = '<div style="color: red;">加载详情失败</div>';
    }
}

// 切换文件操作菜单
function toggleFileActions(fileId) {
    document.querySelectorAll('.file-action-menu').forEach(menu => {
        if (menu.id !== `fileActionMenu_${fileId}`) {
            menu.classList.remove('show');
        }
    });
    
    const menu = document.getElementById(`fileActionMenu_${fileId}`);
    if (menu) {
        menu.classList.toggle('show');
    }
}

// 处理文件操作
async function handleFileAction(fileId, action) {
    try {
        if (action === 'rename') {
            // 重命名文件
            const file = await getFileDetail(fileId);
            if (!file) {
                alert('获取文件信息失败');
                return;
            }
            
            // 显示重命名对话框
            const newFilename = prompt('请输入新的文件名（当前：' + file.filename + '）：', file.filename);
            if (newFilename === null || newFilename.trim() === '') {
                return; // 用户取消或输入为空
            }
            
            // 调用重命名API
            try {
                const formData = new FormData();
                formData.append('new_filename', newFilename.trim());
                
                const response = await fetch(`${API_BASE_URL}/api/files/${fileId}/rename`, {
                    method: 'POST',
                    headers: getAuthHeaders(false),
                    body: formData
                });
                
                // 处理401认证错误
                if (response.status === 401) {
                    alert('登录已过期，请重新登录');
                    removeToken();
                    window.location.reload();
                    return;
                }
                
                if (response.ok) {
                    const data = await response.json();
                    alert(data.message || '重命名成功');
                    loadFiles();
                    // 如果当前文件被选中，刷新详情
                    if (selectedFileId === fileId) {
                        const updatedFile = await getFileDetail(fileId);
                        if (updatedFile) {
                            showFileDetail(updatedFile);
                        }
                    }
                } else {
                    const error = await response.json().catch(() => ({ detail: '未知错误' }));
                    alert('重命名失败：' + (error.detail || '未知错误'));
                }
            } catch (error) {
                console.error('重命名错误:', error);
                alert('重命名失败：' + error.message);
            }
        } else if (action === 'download') {
            // 下载文件
            const fileDetail = await getFileDetail(fileId);
            const response = await fetch(`${API_BASE_URL}/api/files/${fileId}/download`, {
                headers: getAuthHeaders()
            });
            
            // 处理401认证错误
            if (response.status === 401) {
                alert('登录已过期，请重新登录');
                removeToken();
                window.location.reload();
                return;
            }
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = fileDetail ? fileDetail.filename : `file_${fileId}`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                alert('文件下载成功');
            } else {
                const errorText = await response.text().catch(() => '');
                let errorMessage = '未知错误';
                try {
                    const error = JSON.parse(errorText);
                    errorMessage = error.detail || error.message || error.error || '下载失败';
                } catch (e) {
                    errorMessage = errorText || '下载失败，请检查文件是否存在';
                }
                console.error('下载失败详情:', errorText);
                alert('下载失败：' + errorMessage);
            }
        } else if (action === 'changeCategory') {
            // 更改文件分类
            const file = await getFileDetail(fileId);
            if (!file) {
                alert('获取文件信息失败');
                return;
            }
            
            // 获取分类列表
            let categories = [];
            try {
                const categoriesResponse = await fetch(`${API_BASE_URL}/api/categories`, {
                    headers: getAuthHeaders()
                });
                if (categoriesResponse.ok) {
                    const categoriesData = await categoriesResponse.json();
                    categories = categoriesData.categories || [];
                }
            } catch (error) {
                console.error('获取分类列表错误:', error);
            }
            
            // 构建分类选择对话框
            let categoryOptions = categories.map(cat => `<option value="${cat}" ${cat === file.category ? 'selected' : ''}>${cat}</option>`).join('');
            if (categoryOptions) {
                categoryOptions = '<option value="">-- 请选择分类 --</option>' + categoryOptions;
            } else {
                categoryOptions = '<option value="">-- 暂无分类 --</option>';
            }
            
            // 创建对话框
            const dialog = document.createElement('div');
            dialog.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10000; display: flex; align-items: center; justify-content: center;';
            dialog.innerHTML = `
                <div style="background: white; padding: 20px; border-radius: 8px; min-width: 300px; max-width: 500px;">
                    <h3 style="margin-top: 0;">更改文件分类</h3>
                    <p>当前分类：<strong>${file.category || '未分类'}</strong></p>
                    <div style="margin: 15px 0;">
                        <label style="display: block; margin-bottom: 5px;">选择新分类：</label>
                        <select id="newCategorySelect" class="form-input" style="width: 100%; padding: 8px;">
                            ${categoryOptions}
                        </select>
                    </div>
                    <div style="text-align: right; margin-top: 20px;">
                        <button id="cancelCategoryBtn" class="btn btn-secondary" style="margin-right: 10px;">取消</button>
                        <button id="confirmCategoryBtn" class="btn btn-primary">确定</button>
                    </div>
                </div>
            `;
            document.body.appendChild(dialog);
            
            // 绑定事件
            const cancelBtn = dialog.querySelector('#cancelCategoryBtn');
            const confirmBtn = dialog.querySelector('#confirmCategoryBtn');
            const categorySelect = dialog.querySelector('#newCategorySelect');
            
            const closeDialog = () => {
                document.body.removeChild(dialog);
            };
            
            cancelBtn.addEventListener('click', closeDialog);
            
            confirmBtn.addEventListener('click', async function() {
                const selectedCategory = categorySelect.value;
                
                if (!selectedCategory) {
                    alert('请选择分类');
                    return;
                }
                
                const finalCategory = selectedCategory;
                
                try {
                    const formData = new FormData();
                    formData.append('category', finalCategory);
                    
                    const response = await fetch(`${API_BASE_URL}/api/files/${fileId}/edit`, {
                        method: 'POST',
                        headers: getAuthHeaders(false),
                        body: formData
                    });
                    
                    // 处理401认证错误
                    if (response.status === 401) {
                        alert('登录已过期，请重新登录');
                        removeToken();
                        window.location.reload();
                        closeDialog();
                        return;
                    }
                    
                    if (response.ok) {
                        const data = await response.json();
                        alert(data.message || '分类更改成功');
                        closeDialog();
                        loadFiles();
                        // 如果当前文件被选中，刷新详情
                        if (selectedFileId === fileId) {
                            const updatedFile = await getFileDetail(fileId);
                            if (updatedFile) {
                                showFileDetail(updatedFile);
                            }
                        }
                    } else {
                        const error = await response.json().catch(() => ({ detail: '未知错误' }));
                        alert('更改分类失败：' + (error.detail || '未知错误'));
                    }
                } catch (error) {
                    console.error('更改分类错误:', error);
                    alert('更改分类失败：' + error.message);
                }
            });
            
            // 点击背景关闭对话框
            dialog.addEventListener('click', function(e) {
                if (e.target === dialog) {
                    closeDialog();
                }
            });
        } else if (action === 'delete') {
            // 删除文件
            if (!confirm('⚠️ 警告：确定要删除这个文件吗？\n\n此操作将：\n- 删除MySQL中的文件记录\n- 删除MinIO中的文件\n\n此操作不可恢复！')) {
                return;
            }
            
            try {
                const response = await fetch(`${API_BASE_URL}/api/files/${fileId}`, {
                    method: 'DELETE',
                    headers: getAuthHeaders()
                });
                
                // 处理401认证错误
                if (response.status === 401) {
                    alert('登录已过期，请重新登录');
                    removeToken();
                    window.location.reload();
                    return;
                }
                
                if (response.ok) {
                    const data = await response.json();
                    alert('✅ ' + data.message);
                    // 清空选中状态
                    selectedFileId = null;
                    const fileDetailPanel = document.getElementById('fileDetailPanel');
                    if (fileDetailPanel) {
                        fileDetailPanel.style.display = 'none';
                    }
                    // 刷新文件列表
                    loadFiles();
                } else {
                    const error = await response.json().catch(() => ({ detail: '未知错误' }));
                    alert('❌ 删除失败：' + (error.detail || '未知错误'));
                }
            } catch (error) {
                console.error('删除文件错误:', error);
                alert('❌ 删除失败：' + error.message);
            }
        } else {
            alert('不支持的操作：' + action);
        }
    } catch (error) {
        console.error('操作失败:', error);
        alert('操作失败：' + error.message);
    }
    
    document.querySelectorAll('.file-action-menu').forEach(menu => {
        menu.classList.remove('show');
    });
}

// 获取文件详情
async function getFileDetail(fileId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/files/${fileId}`, {
            headers: getAuthHeaders()
        });
        
        // 处理401认证错误
        if (response.status === 401) {
            console.error('认证失败，请重新登录');
            removeToken();
            window.location.reload();
            return null;
        }
        
        if (response.ok) {
            return await response.json();
        }
        return null;
    } catch (error) {
        console.error('获取文件详情错误:', error);
        return null;
    }
}

// 显示文件历史版本
function showFileHistory(fileId, versions) {
    let html = '<h4>文件历史版本</h4><ul style="list-style: none; padding: 0;">';
    versions.forEach(v => {
        html += `<li style="padding: 10px; border-bottom: 1px solid #ddd;">
            <strong>${v.version}</strong> - ${v.created_at}
            <br><small>${v.change_log || '无变更说明'}</small>
        </li>`;
    });
    html += '</ul>';
    alert(html.replace(/<[^>]*>/g, '')); // 简化显示
}


// 点击页面其他地方时关闭所有菜单
document.addEventListener('click', function(e) {
    if (!e.target.closest('.file-actions') && !e.target.closest('.file-action-menu')) {
        document.querySelectorAll('.file-action-menu').forEach(menu => {
            menu.classList.remove('show');
        });
    }
});

function renderPagination() {
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';
    
    const totalPages = Math.ceil(totalFiles / pageSize);
    if (totalPages <= 1) return;
    
    const prevBtn = document.createElement('button');
    prevBtn.textContent = '«';
    prevBtn.disabled = currentPage === 1;
    prevBtn.addEventListener('click', function() {
        if (currentPage > 1) {
            currentPage--;
            loadFiles();
        }
    });
    pagination.appendChild(prevBtn);
    
    const maxButtons = 10;
    let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);
    
    if (endPage - startPage < maxButtons - 1) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }
    
    if (startPage > 1) {
        const firstBtn = document.createElement('button');
        firstBtn.textContent = '1';
        firstBtn.addEventListener('click', function() {
            currentPage = 1;
            loadFiles();
        });
        pagination.appendChild(firstBtn);
        
        if (startPage > 2) {
            const ellipsis = document.createElement('span');
            ellipsis.textContent = '...';
            ellipsis.style.padding = '0 10px';
            pagination.appendChild(ellipsis);
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.textContent = i;
        pageBtn.className = i === currentPage ? 'active' : '';
        pageBtn.addEventListener('click', function() {
            currentPage = i;
            loadFiles();
        });
        pagination.appendChild(pageBtn);
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            const ellipsis = document.createElement('span');
            ellipsis.textContent = '...';
            ellipsis.style.padding = '0 10px';
            pagination.appendChild(ellipsis);
        }
        
        const lastBtn = document.createElement('button');
        lastBtn.textContent = totalPages;
        lastBtn.addEventListener('click', function() {
            currentPage = totalPages;
            loadFiles();
        });
        pagination.appendChild(lastBtn);
    }
    
    const nextBtn = document.createElement('button');
    nextBtn.textContent = '»';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.addEventListener('click', function() {
        if (currentPage < totalPages) {
            currentPage++;
            loadFiles();
        }
    });
    pagination.appendChild(nextBtn);
}

// ==================== 分类和标签 ====================

async function loadCategories() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/categories`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();
        
        // 更新筛选栏的分类选择器
        const filterSelect = document.getElementById('categoryFilter');
        if (filterSelect) {
            // 保留"全部"选项，清空其他选项
            filterSelect.innerHTML = '<option value="">全部</option>';
            data.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                filterSelect.appendChild(option);
            });
        }
        
        // 更新上传区域的分类选择器
        const uploadSelect = document.getElementById('uploadCategory');
        if (uploadSelect) {
            // 保留"请选择分类"选项，清空其他选项
            uploadSelect.innerHTML = '<option value="">请选择分类</option>';
            data.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                uploadSelect.appendChild(option);
            });
        }
        
        // 更新模板分类过滤器（左上角）
        const templateCategoryFilter = document.getElementById('templateCategoryFilter');
        if (templateCategoryFilter) {
            const currentValue = templateCategoryFilter.value; // 保存当前选中的值
            templateCategoryFilter.innerHTML = '<option value="">全部分类</option>';
            data.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                templateCategoryFilter.appendChild(option);
            });
            // 恢复之前选中的值
            if (currentValue) {
                templateCategoryFilter.value = currentValue;
            }
        }
        
        // 更新模板上传分类选择器（右下角）
        const templateUploadCategory = document.getElementById('templateUploadCategory');
        if (templateUploadCategory) {
            const currentValue = templateUploadCategory.value; // 保存当前选中的值
            templateUploadCategory.innerHTML = '<option value="">请选择分类</option>';
            data.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                templateUploadCategory.appendChild(option);
            });
            // 恢复之前选中的值
            if (currentValue) {
                templateUploadCategory.value = currentValue;
            }
        }
    } catch (error) {
        console.error('加载分类错误:', error);
        // 使用默认分类作为fallback（只包含未分类）
        const categories = ["未分类"];
        
        const filterSelect = document.getElementById('categoryFilter');
        if (filterSelect) {
            filterSelect.innerHTML = '<option value="">全部</option>';
            categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                filterSelect.appendChild(option);
            });
        }
        
        const uploadSelect = document.getElementById('uploadCategory');
        if (uploadSelect) {
            uploadSelect.innerHTML = '<option value="">请选择分类</option>';
            categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                uploadSelect.appendChild(option);
            });
        }
    }
}

async function loadTags() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/files/tags`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();
        
        const select = document.getElementById('tagFilter');
        data.tags.forEach(tag => {
            const option = document.createElement('option');
            option.value = tag;
            option.textContent = tag;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('加载标签错误:', error);
        // 不加载模拟数据，保持空列表
    }
}

// ==================== 文件上传 ====================

function initFileUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const addCategoryBtn = document.getElementById('addCategoryBtn');
    const uploadCategory = document.getElementById('uploadCategory');
    const newCategoryInput = document.getElementById('newCategoryInput');
    
    uploadArea.addEventListener('click', function() {
        fileInput.click();
    });
    
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            uploadFiles(e.target.files);
        }
    });
    
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            uploadFiles(e.dataTransfer.files);
        }
    });
    
    // 文件上传不再需要分类选择，分类管理已独立
}

async function uploadFiles(files) {
    // 获取选择的分类
    const uploadCategory = document.getElementById('uploadCategory');
    const selectedCategory = uploadCategory ? uploadCategory.value : '';
    
    for (let file of files) {
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            // 使用用户选择的分类，如果没有选择则使用默认分类
            if (selectedCategory) {
                formData.append('category', selectedCategory);
            } else {
                formData.append('category', 'documents');
            }
            
            const response = await fetch(`${API_BASE_URL}/api/files/upload`, {
                method: 'POST',
                headers: getAuthHeaders(false), // 文件上传不需要设置 Content-Type，浏览器会自动设置
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '上传失败');
            }
            
            const data = await response.json();
            console.log('上传响应:', data);
            
            if (data.success) {
                document.getElementById('uploadInfo').style.display = 'block';
                document.getElementById('minioBucket').textContent = data.minio_bucket || '-';
                document.getElementById('minioPath').textContent = data.minio_path || '-';
                document.getElementById('mysqlTable').textContent = data.mysql_info?.table || '-';
                document.getElementById('mysqlDatabase').textContent = data.mysql_info?.database || '-';
                document.getElementById('mysqlId').textContent = data.mysql_info?.record_id || '-';
                
                // 刷新分类列表（确保新分类同步）
                await loadCategories();
                
                // 清空文件输入，但保留分类选择
                const fileInput = document.getElementById('fileInput');
                if (fileInput) {
                    fileInput.value = '';
                }
                
                // 重置到第一页并刷新文件列表
                currentPage = 1;
                await loadFiles();
                console.log('文件列表已刷新');
                alert('上传成功：' + file.name);
            } else {
                alert('上传失败：' + data.message);
            }
        } catch (error) {
            console.error('上传错误:', error);
            alert('上传失败：' + error.message);
        }
    }
    
    document.getElementById('fileInput').value = '';
}

// ==================== 模板管理 ====================

async function loadTemplates() {
    const category = document.getElementById('templateCategoryFilter')?.value || '';
    const search = document.getElementById('templateSearch')?.value || '';
    
    try {
        // 使用 group_by_name=true 来按模板名称分组
        let url = `${API_BASE_URL}/api/templates?page=${templateCurrentPage}&page_size=${pageSize}&group_by_name=true`;
        if (category) url += `&category=${category}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        
        const response = await fetch(url, {
            headers: getAuthHeaders(),
            cache: 'no-cache', // 禁用缓存，强制从服务器获取最新数据
            method: 'GET'
        });
        
        // 处理401认证错误
        if (response.status === 401) {
            console.error('认证失败，请重新登录');
            removeToken();
            alert('登录已过期，请重新登录');
            window.location.reload();
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('模板列表响应:', data);
        console.log('模板数量:', data.templates?.length || 0, '总数:', data.total || 0);
        
        // 确保只显示实际返回的模板数量
        if (data.templates && data.templates.length !== data.total) {
            console.warn(`模板数量不一致: 返回${data.templates.length}个, 总数${data.total}`);
        }
        
        renderTemplateList(data.templates || []);
        renderTemplatePagination(data.total || 0);
    } catch (error) {
        console.error('加载模板列表错误:', error);
        // 显示空列表
        renderTemplateList([]);
        renderTemplatePagination(0);
    }
}

function renderTemplateList(templates) {
    const templateList = document.getElementById('templateList');
    templateList.innerHTML = '';
    
    if (templates.length === 0) {
        templateList.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">暂无模板</div>';
        return;
    }
    
    templates.forEach(template => {
        const templateItem = document.createElement('div');
        templateItem.className = 'file-item';
        templateItem.dataset.templateId = template.id;
        templateItem.dataset.templateName = template.name;
        // 存储模板的格式映射信息
        if (template.template_ids && template.available_formats) {
            templateItem.dataset.templateIds = JSON.stringify(template.template_ids);
            templateItem.dataset.availableFormats = JSON.stringify(template.available_formats);
        }
        
        // 显示可用格式
        const formatBadges = template.available_formats && template.available_formats.length > 0
            ? template.available_formats.map(f => {
                const formatLower = f.toLowerCase();
                const tagClass = formatLower === 'html' ? 'tag-html' : formatLower === 'word' ? 'tag-word' : formatLower === 'pdf' ? 'tag-pdf' : '';
                return `<span class="file-tag ${tagClass}" data-format="${formatLower}">${f.toUpperCase()}</span>`;
            }).join('')
            : `<span class="file-tag tag-${(template.format_type || '未知').toLowerCase()}">${template.format_type || '未知'}</span>`;
        
        // 生成格式选择复选框
        const availableFormats = template.available_formats || [template.format_type || 'word'];
        // 使用后端返回的format_to_id映射，如果没有则根据template_ids建立映射
        let formatToIdMap = template.format_to_id || {};
        if (Object.keys(formatToIdMap).length === 0 && template.template_ids && template.available_formats && template.template_ids.length === template.available_formats.length) {
            template.available_formats.forEach((format, index) => {
                formatToIdMap[format] = template.template_ids[index];
            });
        } else if (Object.keys(formatToIdMap).length === 0) {
            // 如果没有映射，使用主模板ID
            availableFormats.forEach(format => {
                formatToIdMap[format] = template.id;
            });
        }
        
        const formatCheckboxes = availableFormats.map(format => {
            const formatUpper = format.toUpperCase();
            const formatId = formatToIdMap[format] || template.id;
            return `
                <label style="display: inline-flex; align-items: center; margin-right: 15px; cursor: pointer;" onclick="event.stopPropagation();">
                    <input type="checkbox" 
                           class="template-format-checkbox" 
                           data-template-id="${formatId}" 
                           data-format="${format}" 
                           data-template-name="${template.name}"
                           ${availableFormats.length === 1 ? 'checked' : ''}
                           style="margin-right: 5px;">
                    <span>${formatUpper}</span>
                </label>
            `;
        }).join('');
        
        templateItem.innerHTML = `
            <div class="file-name">${template.name}</div>
            <div class="file-tags">
                <span class="file-tag">版本: ${template.version}</span>
                <span class="file-tag">${template.category}</span>
                ${formatBadges}
            </div>
            <div class="file-uploader">说明: ${template.description || '-'}</div>
            <div class="template-format-selector" style="margin: 10px 0; padding: 10px; background-color: #f5f5f5; border-radius: 5px;">
                <strong style="display: block; margin-bottom: 5px;">选择格式（可多选）：</strong>
                <div class="format-checkboxes">
                    ${formatCheckboxes}
                </div>
            </div>
            <div class="file-actions">
                <button class="btn btn-small btn-primary" onclick="event.stopPropagation(); handleTemplateAction(${template.id}, 'download')" style="margin-right: 5px;">下载</button>
                <button class="btn btn-small btn-info" onclick="event.stopPropagation(); handleTemplateAction(${template.id}, 'update')" style="margin-right: 5px; background-color: #17a2b8;">更新</button>
                <button class="btn btn-small btn-secondary" onclick="event.stopPropagation(); handleTemplateAction(${template.id}, 'rename')" style="margin-right: 5px;">重命名</button>
                <button class="btn btn-small btn-secondary" onclick="event.stopPropagation(); handleTemplateAction(${template.id}, 'changeCategory')" style="margin-right: 5px;">更改分类</button>
                <button class="btn btn-small btn-danger" onclick="event.stopPropagation(); handleTemplateAction(${template.id}, 'delete')">删除</button>
            </div>
        `;
        
        templateItem.addEventListener('click', function(e) {
            if (e.target.closest('.file-actions') || e.target.closest('.file-action-menu')) {
                return;
            }
            document.querySelectorAll('.file-item').forEach(item => {
                item.classList.remove('selected');
            });
            templateItem.classList.add('selected');
            selectedTemplateId = template.id;
            showTemplateDetail(template);
        });
        
        templateList.appendChild(templateItem);
    });
}

async function showTemplateDetail(template) {
    const detailSection = document.getElementById('templateDetailSection');
    const detailContent = document.getElementById('templateDetailContent');
    const uploadSection = document.getElementById('templateUploadSection');
    
    // 同时显示上传区域和详情区域，或者让用户可以切换
    // 保持上传区域可见，详情区域显示在下方
    if (uploadSection) {
        uploadSection.style.display = 'block';
    }
    if (detailSection) {
        detailSection.style.display = 'block';
    }
    
    // 如果传入的是ID，需要先获取详情
    let templateDetail = template;
    if (typeof template === 'number' || (template && !template.name)) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/templates/${template.id || template}`, {
                headers: getAuthHeaders()
            });
            if (response.ok) {
                templateDetail = await response.json();
            }
        } catch (error) {
            console.error('获取模板详情错误:', error);
        }
    }
    
    const formatBadges = templateDetail.available_formats && templateDetail.available_formats.length > 0
        ? templateDetail.available_formats.map(f => {
            const formatLower = f.toLowerCase();
            const tagClass = formatLower === 'html' ? 'tag-html' : formatLower === 'word' ? 'tag-word' : formatLower === 'pdf' ? 'tag-pdf' : '';
            return `<span class="file-tag ${tagClass}" data-format="${formatLower}" style="margin: 2px;">${f.toUpperCase()}</span>`;
        }).join('')
        : `<span class="file-tag tag-${(templateDetail.format_type || '未知').toLowerCase()}">${templateDetail.format_type || '未知'}</span>`;
    
    detailContent.innerHTML = `
        <div class="detail-item">
            <strong>模板名称：</strong>
            <span>${templateDetail.name || templateDetail.template_name || '-'}</span>
        </div>
        <div class="detail-item">
            <strong>分类：</strong>
            <span>${templateDetail.category || '-'}</span>
        </div>
        <div class="detail-item">
            <strong>版本：</strong>
            <span>${templateDetail.version || '-'}</span>
        </div>
        <div class="detail-item">
            <strong>格式类型：</strong>
            <span>${templateDetail.format_type || '-'}</span>
        </div>
        <div class="detail-item">
            <strong>可用格式：</strong>
            <div style="margin-top: 5px;">
                ${formatBadges}
            </div>
        </div>
        <div class="detail-item">
            <strong>文件名：</strong>
            <span>${templateDetail.filename || '-'}</span>
        </div>
        <div class="detail-item">
            <strong>文件大小：</strong>
            <span>${templateDetail.file_size ? (templateDetail.file_size / 1024).toFixed(2) + ' KB' : '-'}</span>
        </div>
        <div class="detail-item">
            <strong>创建时间：</strong>
            <span>${templateDetail.created_at || '-'}</span>
        </div>
        <div class="detail-item">
            <strong>创建人：</strong>
            <span>${templateDetail.created_by || '系统'}</span>
        </div>
        <div class="detail-item">
            <strong>说明：</strong>
            <span>${templateDetail.description || templateDetail.change_log || '-'}</span>
        </div>
    `;
    
    // 显示版本历史（异步加载）
    const versionHistory = document.getElementById('versionHistory');
    const versionHistoryList = document.getElementById('versionHistoryList');
    if (versionHistory) {
        versionHistory.style.display = 'block';
        versionHistoryList.innerHTML = '<div style="text-align: center; padding: 10px;">加载中...</div>';
        
        // 异步加载版本历史
        fetch(`${API_BASE_URL}/api/templates/${templateDetail.id || template.id}/versions`, {
            headers: getAuthHeaders()
        })
        .then(response => response.json())
        .then(data => {
            if (data.versions && data.versions.length > 0) {
                versionHistoryList.innerHTML = data.versions.map(v => {
                    const latestTag = v.is_latest ? ' <span style="color: green;">(当前)</span>' : '';
                    return `<div class="version-item" onclick="viewVersion(${templateDetail.id || template.id}, '${v.version}')">${v.version}${latestTag} - ${v.format_type || ''} - ${v.created_at} - ${v.change_log || '无变更说明'}</div>`;
                }).join('');
            } else {
                versionHistoryList.innerHTML = '<div style="text-align: center; padding: 10px; color: #999;">暂无版本历史</div>';
            }
        })
        .catch(error => {
            console.error('加载版本历史错误:', error);
            versionHistoryList.innerHTML = '<div style="text-align: center; padding: 10px; color: #999;">加载失败</div>';
        });
    }
}

function toggleTemplateActions(templateId) {
    document.querySelectorAll('.file-action-menu').forEach(menu => {
        if (menu.id !== `templateActionMenu_${templateId}`) {
            menu.classList.remove('show');
        }
    });
    
    const menu = document.getElementById(`templateActionMenu_${templateId}`);
    if (menu) {
        menu.classList.toggle('show');
    }
}

// 获取选中的格式对应的模板ID
function getSelectedFormatTemplateIds(templateId) {
    const templateItem = document.querySelector(`[data-template-id="${templateId}"]`);
    if (!templateItem) {
        return [{ id: templateId, format: 'word' }]; // 默认返回主模板ID
    }
    
    const checkboxes = templateItem.querySelectorAll('.template-format-checkbox:checked');
    if (checkboxes.length === 0) {
        // 如果没有选中任何格式，返回所有格式
        const allCheckboxes = templateItem.querySelectorAll('.template-format-checkbox');
        return Array.from(allCheckboxes).map(cb => ({
            id: parseInt(cb.dataset.templateId),
            format: cb.dataset.format,
            name: cb.dataset.templateName
        }));
    }
    
    return Array.from(checkboxes).map(cb => ({
        id: parseInt(cb.dataset.templateId),
        format: cb.dataset.format,
        name: cb.dataset.templateName
    }));
}

async function handleTemplateAction(templateId, action) {
    try {
        if (action === 'download') {
            // 获取选中的格式
            const selectedFormats = getSelectedFormatTemplateIds(templateId);
            
            if (selectedFormats.length === 0) {
                alert('请至少选择一个格式');
                return;
            }
            // 批量下载选中的格式
            let successCount = 0;
            let failCount = 0;
            
            for (const formatInfo of selectedFormats) {
                try {
                    const response = await fetch(`${API_BASE_URL}/api/templates/${formatInfo.id}/download`, {
                headers: getAuthHeaders()
            });
            
            // 处理401认证错误
            if (response.status === 401) {
                alert('登录已过期，请重新登录');
                removeToken();
                window.location.reload();
                return;
            }
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                
                // 从响应头获取文件名
                const contentDisposition = response.headers.get('Content-Disposition');
                        let filename = `${formatInfo.name || 'template'}_${formatInfo.format.toUpperCase()}`;
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename="(.+)"/);
                    if (filenameMatch) {
                                const originalFilename = filenameMatch[1];
                                const ext = originalFilename.substring(originalFilename.lastIndexOf('.'));
                                filename = `${formatInfo.name || 'template'}_${formatInfo.format.toUpperCase()}${ext}`;
                    }
                }
                
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                        successCount++;
                        
                        // 多个文件下载时，添加延迟避免浏览器阻止
                        if (selectedFormats.length > 1) {
                            await new Promise(resolve => setTimeout(resolve, 500));
                        }
            } else {
                const error = await response.json().catch(() => ({ detail: '未知错误' }));
                        console.error(`下载 ${formatInfo.format} 格式失败:`, error);
                        failCount++;
                    }
                } catch (error) {
                    console.error(`下载 ${formatInfo.format} 格式错误:`, error);
                    failCount++;
                }
            }
            
            if (successCount > 0) {
                alert(`下载完成！成功 ${successCount} 个${failCount > 0 ? `，失败 ${failCount} 个` : ''}`);
            } else {
                alert('所有格式下载失败');
            }
        } else if (action === 'versions') {
            // 查看版本历史（显示所有选中格式的版本历史）
            if (selectedFormats.length === 0) {
                alert('请至少选择一个格式');
                return;
            }
            
            // 获取第一个选中格式的版本历史（可以后续扩展为显示所有格式）
            const firstFormat = selectedFormats[0];
            const response = await fetch(`${API_BASE_URL}/api/templates/${firstFormat.id}/versions`, {
                headers: getAuthHeaders()
            });
            if (response.ok) {
                const data = await response.json();
                showTemplateVersions(firstFormat.id, data.versions, selectedFormats);
            } else {
                alert('获取版本历史失败');
            }
        } else if (action === 'rename') {
            // 重命名模板
            const selectedFormats = getSelectedFormatTemplateIds(templateId);
            if (selectedFormats.length === 0) {
                alert('请至少选择一个格式');
                return;
            }
            
            const firstFormat = selectedFormats[0];
            const response = await fetch(`${API_BASE_URL}/api/templates/${firstFormat.id}`, {
                headers: getAuthHeaders()
            });
            
            if (!response.ok) {
                alert('获取模板信息失败');
                return;
            }
            
            const template = await response.json();
            const newName = prompt('请输入新的模板名称（当前：' + template.name + '）：', template.name);
            if (newName === null || !newName.trim()) {
                return;
            }
            
            // 批量重命名所有格式
            let successCount = 0;
            let failCount = 0;
            
            for (const formatInfo of selectedFormats) {
                try {
                    const formData = new FormData();
                    formData.append('template_name', newName.trim());
                    
                    const editResponse = await fetch(`${API_BASE_URL}/api/templates/${formatInfo.id}/edit`, {
                        method: 'POST',
                        headers: getAuthHeaders(false),
                        body: formData
                    });
                    
                    if (editResponse.ok) {
                        successCount++;
                    } else {
                        failCount++;
                    }
                } catch (error) {
                    console.error(`重命名 ${formatInfo.format} 格式错误:`, error);
                    failCount++;
                }
            }
            
            if (successCount > 0) {
                alert(`重命名完成！成功 ${successCount} 个${failCount > 0 ? `，失败 ${failCount} 个` : ''}`);
                loadTemplates();
            } else {
                alert('所有格式重命名失败');
            }
        } else if (action === 'changeCategory') {
            // 更改模板分类
            const selectedFormats = getSelectedFormatTemplateIds(templateId);
            if (selectedFormats.length === 0) {
                alert('请至少选择一个格式');
                return;
            }
            
            const firstFormat = selectedFormats[0];
            const response = await fetch(`${API_BASE_URL}/api/templates/${firstFormat.id}`, {
                headers: getAuthHeaders()
            });
            
            if (!response.ok) {
                alert('获取模板信息失败');
                return;
            }
            
            const template = await response.json();
            
            // 获取分类列表
            let categories = [];
            try {
                const categoriesResponse = await fetch(`${API_BASE_URL}/api/categories`, {
                    headers: getAuthHeaders()
                });
                if (categoriesResponse.ok) {
                    const categoriesData = await categoriesResponse.json();
                    categories = categoriesData.categories || [];
                }
            } catch (error) {
                console.error('获取分类列表错误:', error);
            }
            
            // 构建分类选择对话框
            let categoryOptions = categories.map(cat => `<option value="${cat}" ${cat === template.category ? 'selected' : ''}>${cat}</option>`).join('');
            if (categoryOptions) {
                categoryOptions = '<option value="">-- 请选择分类 --</option>' + categoryOptions;
            } else {
                categoryOptions = '<option value="">-- 暂无分类 --</option>';
            }
            
            // 创建对话框
            const dialog = document.createElement('div');
            dialog.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10000; display: flex; align-items: center; justify-content: center;';
            dialog.innerHTML = `
                <div style="background: white; padding: 20px; border-radius: 8px; min-width: 300px; max-width: 500px;">
                    <h3 style="margin-top: 0;">更改模板分类</h3>
                    <p>当前分类：<strong>${template.category || '未分类'}</strong></p>
                    <div style="margin: 15px 0;">
                        <label style="display: block; margin-bottom: 5px;">选择新分类：</label>
                        <select id="newTemplateCategorySelect" class="form-input" style="width: 100%; padding: 8px;">
                            ${categoryOptions}
                        </select>
                    </div>
                    <div style="text-align: right; margin-top: 20px;">
                        <button id="cancelTemplateCategoryBtn" class="btn btn-secondary" style="margin-right: 10px;">取消</button>
                        <button id="confirmTemplateCategoryBtn" class="btn btn-primary">确定</button>
                    </div>
                </div>
            `;
            document.body.appendChild(dialog);
            
            // 绑定事件
            const cancelBtn = dialog.querySelector('#cancelTemplateCategoryBtn');
            const confirmBtn = dialog.querySelector('#confirmTemplateCategoryBtn');
            const categorySelect = dialog.querySelector('#newTemplateCategorySelect');
            
            const closeDialog = () => {
                document.body.removeChild(dialog);
            };
            
            cancelBtn.addEventListener('click', closeDialog);
            
            confirmBtn.addEventListener('click', async function() {
                const selectedCategory = categorySelect.value;
                
                if (!selectedCategory) {
                    alert('请选择分类');
                    return;
                }
                
                // 批量更新所有格式的分类
                let successCount = 0;
                let failCount = 0;
                
                for (const formatInfo of selectedFormats) {
                    try {
                        const formData = new FormData();
                        formData.append('category', selectedCategory);
                        
                        const response = await fetch(`${API_BASE_URL}/api/templates/${formatInfo.id}/edit`, {
                            method: 'POST',
                            headers: getAuthHeaders(false),
                            body: formData
                        });
                        
                        if (response.ok) {
                            successCount++;
                        } else {
                            failCount++;
                        }
                    } catch (error) {
                        console.error(`更改分类 ${formatInfo.format} 格式错误:`, error);
                        failCount++;
                    }
                }
                
                if (successCount > 0) {
                    alert(`分类更改完成！成功 ${successCount} 个${failCount > 0 ? `，失败 ${failCount} 个` : ''}`);
                    closeDialog();
                    loadTemplates();
                } else {
                    alert('所有格式更改分类失败');
                }
            });
            
            // 点击背景关闭对话框
            dialog.addEventListener('click', function(e) {
                if (e.target === dialog) {
                    closeDialog();
                }
            });
        } else if (action === 'update') {
            // 更新模板（上传新版本或回退到历史版本）
            const selectedFormats = getSelectedFormatTemplateIds(templateId);
            if (selectedFormats.length === 0) {
                alert('请至少选择一个格式');
                return;
            }
            
            const firstFormat = selectedFormats[0];
            
            // 获取模板版本历史
            const versionsResponse = await fetch(`${API_BASE_URL}/api/templates/${firstFormat.id}/versions`, {
                headers: getAuthHeaders()
            });
            
            let versions = [];
            if (versionsResponse.ok) {
                const versionsData = await versionsResponse.json();
                versions = versionsData.versions || [];
            }
            
            // 创建更新对话框
            const dialog = document.createElement('div');
            dialog.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10000; display: flex; align-items: center; justify-content: center;';
            
            const versionOptions = versions.map(v => 
                `<option value="${v.version}" ${v.is_latest ? 'disabled' : ''}>版本 ${v.version} - ${v.created_at}${v.is_latest ? ' (当前)' : ''}</option>`
            ).join('');
            
            dialog.innerHTML = `
                <div style="background: white; padding: 20px; border-radius: 8px; min-width: 400px; max-width: 600px;">
                    <h3 style="margin-top: 0;">更新模板</h3>
                    <p>模板：<strong>${firstFormat.name}</strong> (${selectedFormats.map(f => f.format.toUpperCase()).join(', ')})</p>
                    
                    <div style="margin: 20px 0;">
                        <h4 style="margin-bottom: 10px;">选项1：上传新版本</h4>
                        <input type="file" id="newTemplateVersionFile" accept=".docx,.html,.pdf" style="width: 100%;">
                        <input type="text" id="newVersionChangeLog" placeholder="变更说明（可选）" style="width: 100%; margin-top: 10px; padding: 8px;">
                    </div>
                    
                    ${versions.length > 1 ? `
                    <div style="margin: 20px 0; padding-top: 20px; border-top: 1px solid #ddd;">
                        <h4 style="margin-bottom: 10px;">选项2：回退到历史版本</h4>
                        <select id="rollbackVersionSelect" style="width: 100%; padding: 8px;">
                            <option value="">-- 选择要回退的版本 --</option>
                            ${versionOptions}
                        </select>
                    </div>
                    ` : ''}
                    
                    <div style="text-align: right; margin-top: 20px;">
                        <button id="cancelUpdateBtn" class="btn btn-secondary" style="margin-right: 10px;">取消</button>
                        <button id="uploadNewVersionBtn" class="btn btn-primary" style="margin-right: 10px;">上传新版本</button>
                        ${versions.length > 1 ? '<button id="rollbackVersionBtn" class="btn btn-warning" style="background-color: #ffc107;">回退版本</button>' : ''}
                    </div>
                </div>
            `;
            document.body.appendChild(dialog);
            
            const closeDialog = () => {
                document.body.removeChild(dialog);
            };
            
            dialog.querySelector('#cancelUpdateBtn').addEventListener('click', closeDialog);
            
            // 上传新版本
            dialog.querySelector('#uploadNewVersionBtn').addEventListener('click', async function() {
                const fileInput = dialog.querySelector('#newTemplateVersionFile');
                const changeLog = dialog.querySelector('#newVersionChangeLog').value.trim();
                
                if (!fileInput.files || fileInput.files.length === 0) {
                    alert('请选择要上传的模板文件');
                    return;
                }
                
                const file = fileInput.files[0];
                
                // 检查文件格式
                const ext = file.name.split('.').pop().toLowerCase();
                let formatType = ext === 'docx' ? 'word' : ext;
                
                try {
                    const formData = new FormData();
                    formData.append('file', file);
                    formData.append('template_name', firstFormat.name);
                    formData.append('category', '未分类');
                    formData.append('description', changeLog || '新版本上传');
                    
                    const response = await fetch(`${API_BASE_URL}/api/templates/upload`, {
                        method: 'POST',
                        headers: getAuthHeaders(false),
                        body: formData
                    });
                    
                    if (response.ok) {
                        alert('新版本上传成功！');
                        closeDialog();
                        loadTemplates();
                    } else {
                        const error = await response.json().catch(() => ({ detail: '未知错误' }));
                        alert('上传失败：' + (error.detail || '未知错误'));
                    }
                } catch (error) {
                    console.error('上传新版本错误:', error);
                    alert('上传失败：' + error.message);
                }
            });
            
            // 回退版本
            if (versions.length > 1) {
                dialog.querySelector('#rollbackVersionBtn').addEventListener('click', async function() {
                    const versionSelect = dialog.querySelector('#rollbackVersionSelect');
                    const targetVersion = versionSelect.value;
                    
                    if (!targetVersion) {
                        alert('请选择要回退的版本');
                        return;
                    }
                    
                    if (!confirm(`确定要回退到版本 ${targetVersion} 吗？`)) {
                        return;
                    }
                    
                    try {
                        const response = await fetch(`${API_BASE_URL}/api/templates/${firstFormat.id}/rollback`, {
                            method: 'POST',
                            headers: getAuthHeaders(),
                            body: JSON.stringify({ version: parseInt(targetVersion) })
                        });
                        
                        if (response.ok) {
                            alert(`已回退到版本 ${targetVersion}！`);
                            closeDialog();
                            loadTemplates();
                        } else {
                            const error = await response.json().catch(() => ({ detail: '未知错误' }));
                            alert('回退失败：' + (error.detail || '未知错误'));
                        }
                    } catch (error) {
                        console.error('版本回退错误:', error);
                        alert('回退失败：' + error.message);
                    }
                });
            }
            
            // 点击背景关闭对话框
            dialog.addEventListener('click', function(e) {
                if (e.target === dialog) {
                    closeDialog();
                }
            });
        } else if (action === 'delete') {
            // 批量删除选中的格式
            const selectedFormats = getSelectedFormatTemplateIds(templateId);
            if (selectedFormats.length === 0) {
                alert('请至少选择一个格式');
                return;
            }
            
            const formatNames = selectedFormats.map(f => `${f.name || '模板'}_${f.format.toUpperCase()}`).join('、');
            if (confirm(`确定要删除以下格式的模板吗？\n\n${formatNames}\n\n此操作不可恢复！`)) {
                let successCount = 0;
                let failCount = 0;
                
                for (const formatInfo of selectedFormats) {
                    try {
                        const response = await fetch(`${API_BASE_URL}/api/templates/${formatInfo.id}`, {
                            method: 'DELETE',
                            headers: getAuthHeaders()
                        });
                        if (response.ok) {
                            successCount++;
                        } else {
                            const error = await response.json();
                            console.error(`删除 ${formatInfo.format} 格式失败:`, error);
                            failCount++;
                        }
                    } catch (error) {
                        console.error(`删除 ${formatInfo.format} 格式错误:`, error);
                        failCount++;
                    }
                }
                
                if (successCount > 0) {
                    alert(`删除完成！成功 ${successCount} 个${failCount > 0 ? `，失败 ${failCount} 个` : ''}`);
                    loadTemplates();
                } else {
                    alert('所有格式删除失败');
                }
            }
        } else {
            alert('不支持的操作：' + action);
        }
    } catch (error) {
        console.error('操作失败:', error);
        alert('操作失败：' + error.message);
    }
    
    document.querySelectorAll('.file-action-menu').forEach(menu => {
        menu.classList.remove('show');
    });
}

async function viewVersion(templateId, version) {
    // 获取版本历史并显示
    const response = await fetch(`${API_BASE_URL}/api/templates/${templateId}/versions`, {
        headers: getAuthHeaders()
    });
    if (response.ok) {
        const data = await response.json();
        const versionInfo = data.versions.find(v => v.version === version);
        if (versionInfo) {
            alert(`版本 ${version}\n创建时间: ${versionInfo.created_at}\n变更说明: ${versionInfo.change_log || '无'}`);
        }
    }
}

function showTemplateVersions(templateId, versions, selectedFormats = null) {
    let html = '<h4>模板版本历史</h4>';
    
    if (selectedFormats && selectedFormats.length > 1) {
        html += `<p style="color: #666; font-size: 12px;">显示格式: ${selectedFormats.map(f => f.format.toUpperCase()).join(', ')}</p>`;
    }
    
    html += '<ul style="list-style: none; padding: 0;">';
    versions.forEach(v => {
        const latestTag = v.is_latest ? ' <span style="color: green;">(当前版本)</span>' : '';
        html += `<li style="padding: 10px; border-bottom: 1px solid #ddd;">
            <strong>${v.version}</strong>${latestTag} - ${v.format_type || ''} - ${v.created_at}
            <br><small>${v.change_log || '无变更说明'}</small>
        </li>`;
    });
    html += '</ul>';
    alert(html.replace(/<[^>]*>/g, '')); // 简化显示
}

function renderTemplatePagination(total) {
    const pagination = document.getElementById('templatePagination');
    pagination.innerHTML = '';
    
    const totalPages = Math.ceil(total / pageSize);
    if (totalPages <= 1) return;
    
    // 简化的翻页（与文件列表类似）
    for (let i = 1; i <= totalPages; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.textContent = i;
        pageBtn.className = i === templateCurrentPage ? 'active' : '';
        pageBtn.addEventListener('click', function() {
            templateCurrentPage = i;
            loadTemplates();
        });
        pagination.appendChild(pageBtn);
    }
}

// 模板上传（拖拽上传模式，类似文件上传）
function initTemplateUpload() {
    const uploadArea = document.getElementById('templateUploadArea');
    const fileInput = document.getElementById('templateFileInput');
    const uploadSection = document.getElementById('templateUploadSection');
    const categorySelect = document.getElementById('templateUploadCategory');
    
    if (uploadSection) {
        uploadSection.style.display = 'block';
    }
    
    // 加载分类列表到模板上传选择器
    if (categorySelect) {
        loadCategories().then(() => {
            // 更新模板上传分类选择器
            const uploadSelect = document.getElementById('templateUploadCategory');
            if (uploadSelect) {
                uploadSelect.innerHTML = '<option value="">请选择分类</option>';
                fetch(`${API_BASE_URL}/api/categories`, {
                    headers: getAuthHeaders()
                })
                .then(response => response.json())
                .then(data => {
                    data.categories.forEach(category => {
                        const option = document.createElement('option');
                        option.value = category;
                        option.textContent = category;
                        uploadSelect.appendChild(option);
                    });
                })
                .catch(error => {
                    console.error('加载分类列表错误:', error);
                });
            }
        });
    }
    
    if (uploadArea && fileInput) {
        uploadArea.addEventListener('click', function() {
            fileInput.click();
        });
        
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', async function(e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                await uploadTemplates(Array.from(e.dataTransfer.files));
            }
        });
    }
    
    if (fileInput) {
        fileInput.addEventListener('change', async function(e) {
            if (e.target.files.length > 0) {
                await uploadTemplates(Array.from(e.target.files));
            }
        });
    }
}

// 上传模板文件
async function uploadTemplates(files) {
    const categorySelect = document.getElementById('templateUploadCategory');
    const category = categorySelect ? categorySelect.value : '';
    
    if (!category) {
        alert('请先选择分类');
        return;
    }
    
    for (let file of files) {
        // 检查文件类型
        const fileName = file.name.toLowerCase();
        if (!fileName.endsWith('.docx') && !fileName.endsWith('.pdf') && 
            !fileName.endsWith('.html') && !fileName.endsWith('.htm')) {
            alert(`文件 ${file.name} 格式不支持，仅支持 Word/PDF/HTML 格式`);
            continue;
        }
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            // 使用文件名（去掉扩展名）作为模板名称
            const templateName = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
            formData.append('template_name', templateName);
            formData.append('category', category);
            
            const response = await fetch(`${API_BASE_URL}/api/templates/upload`, {
                method: 'POST',
                headers: getAuthHeaders(false),
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '上传失败');
            }
            
            const data = await response.json();
            if (data.success) {
                console.log(`模板上传成功：${templateName}`);
            } else {
                alert(`模板 ${templateName} 上传失败：${data.message}`);
            }
        } catch (error) {
            console.error(`上传模板 ${file.name} 错误:`, error);
            alert(`模板 ${file.name} 上传失败：${error.message}`);
        }
    }
    
    // 清空文件输入
    const fileInput = document.getElementById('templateFileInput');
    if (fileInput) {
        fileInput.value = '';
    }
    
    // 刷新模板列表
    loadTemplates();
    // 刷新分类列表
    loadCategories();
}

// ==================== 分类管理 ====================

// 加载分类管理页面
async function loadCategoryManagement() {
    await loadCategories();
    // 渲染分类列表
    renderCategoryList();
}

// 渲染分类列表
async function renderCategoryList() {
    const categoryList = document.getElementById('categoryList');
    if (!categoryList) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/categories`, {
            headers: getAuthHeaders()
        });
        
        if (response.status === 401) {
            alert('登录已过期，请重新登录');
            removeToken();
            window.location.reload();
            return;
        }
        
        if (!response.ok) {
            throw new Error('获取分类列表失败');
        }
        
        const data = await response.json();
        const categories = data.categories || [];
        
        categoryList.innerHTML = '';
        
        if (categories.length === 0) {
            categoryList.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">暂无分类</div>';
            return;
        }
        
        categories.forEach(category => {
            const categoryItem = document.createElement('div');
            categoryItem.className = 'file-item';
            categoryItem.style.cssText = 'padding: 15px; margin-bottom: 10px; border: 1px solid #ddd; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;';
            categoryItem.innerHTML = `
                <div style="flex: 1;">
                    <h4 style="margin: 0 0 5px 0;">${escapeHtml(category)}</h4>
                </div>
                <div style="display: flex; gap: 5px;">
                    <button class="btn btn-small btn-danger" onclick="deleteCategory('${escapeHtml(category)}')">删除</button>
                </div>
            `;
            categoryList.appendChild(categoryItem);
        });
    } catch (error) {
        console.error('加载分类列表错误:', error);
        categoryList.innerHTML = '<div style="text-align: center; padding: 20px; color: #dc3545;">加载失败：' + error.message + '</div>';
    }
}

// 添加分类
async function addCategory() {
    const newCategory = prompt('请输入新分类名称：');
    if (!newCategory || !newCategory.trim()) {
        return;
    }
    
    const categoryName = newCategory.trim();
    
    // 验证分类名称
    if (categoryName.length > 50) {
        alert('分类名称不能超过50个字符');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/categories`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ category: categoryName })
        });
        
        if (response.status === 401) {
            alert('登录已过期，请重新登录');
            removeToken();
            window.location.reload();
            return;
        }
        
        if (response.ok) {
            const data = await response.json();
            alert('分类添加成功：' + data.category);
            // 刷新所有分类列表
            await loadCategoryManagement();
            await loadCategories(); // 同步文件管理和模板管理的分类选择器
        } else {
            const error = await response.json().catch(() => ({ detail: '未知错误' }));
            alert('添加分类失败：' + (error.detail || '未知错误'));
        }
    } catch (error) {
        console.error('添加分类错误:', error);
        alert('添加分类失败：' + error.message);
    }
}

// 删除分类
async function deleteCategory(category) {
    if (!confirm(`确定要删除分类 "${category}" 吗？\n\n注意：删除分类不会删除该分类下的文件，这些文件的分类将变为空。`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/categories/${encodeURIComponent(category)}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        if (response.status === 401) {
            alert('登录已过期，请重新登录');
            removeToken();
            window.location.reload();
            return;
        }
        
        if (response.ok) {
            const data = await response.json();
            alert('分类删除成功：' + data.category);
            // 刷新所有分类列表
            await loadCategoryManagement();
            await loadCategories(); // 同步文件管理和模板管理的分类选择器
            loadFiles(); // 刷新文件列表
            loadTemplates(); // 刷新模板列表
        } else {
            const error = await response.json().catch(() => ({ detail: '未知错误' }));
            alert('删除分类失败：' + (error.detail || '未知错误'));
        }
    } catch (error) {
        console.error('删除分类错误:', error);
        alert('删除分类失败：' + error.message);
    }
}

// 导出全局函数
window.addCategory = addCategory;
window.deleteCategory = deleteCategory;

// 模板搜索和筛选
document.addEventListener('DOMContentLoaded', function() {
    const templateCategoryFilter = document.getElementById('templateCategoryFilter');
    const templateSearch = document.getElementById('templateSearch');
    
    if (templateCategoryFilter) {
        templateCategoryFilter.addEventListener('change', function() {
            templateCurrentPage = 1;
            loadTemplates();
        });
    }
    
    if (templateSearch) {
        let searchTimeout;
        templateSearch.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(function() {
                templateCurrentPage = 1;
                loadTemplates();
            }, 500);
        });
    }
    
    // 一键清空模板列表按钮
    const clearTemplatesBtn = document.getElementById('clearTemplatesBtn');
    if (clearTemplatesBtn) {
        clearTemplatesBtn.addEventListener('click', function() {
            if (confirm('确定要清空模板列表吗？此操作将清空当前显示的模板列表。')) {
                const templateList = document.getElementById('templateList');
                templateList.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">列表已清空</div>';
                const pagination = document.getElementById('templatePagination');
                pagination.innerHTML = '';
                selectedTemplateId = null;
                document.getElementById('templateDetailSection').style.display = 'none';
                // 确保上传区域始终显示
                const uploadSection = document.getElementById('templateUploadSection');
                if (uploadSection) {
                    uploadSection.style.display = 'block';
                }
                alert('模板列表已清空（占位）');
            }
        });
    }
});

// ==================== 文档生成 ====================

// 更新步骤状态
function updateStepStatus() {
    const step1 = document.getElementById('step1');
    const step2 = document.getElementById('step2');
    const step3 = document.getElementById('step3');
    const step4 = document.getElementById('step4');
    
    const templateSelected = document.getElementById('generationTemplateSelect')?.value;
    const fileSelected = document.getElementById('dataFileSelect')?.value || uploadedDataFile;
    
    // 步骤1：选择模板
    if (templateSelected) {
        step1?.classList.add('active');
    } else {
        step1?.classList.remove('active');
    }
    
    // 步骤2：选择数据文件
    if (fileSelected) {
        step2?.classList.add('active');
    } else {
        step2?.classList.remove('active');
    }
    
    // 步骤3：生成配置（当模板和文件都选择后激活）
    if (templateSelected && fileSelected) {
        step3?.classList.add('active');
    } else {
        step3?.classList.remove('active');
    }
}

// 初始化格式标签切换
function initFormatTags() {
    const formatTags = document.querySelectorAll('.format-tag');
    formatTags.forEach(tag => {
        const checkbox = tag.querySelector('input[type="checkbox"]');
        if (checkbox) {
            // 点击标签时切换复选框状态（使用更可靠的事件处理）
            tag.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                // 切换复选框状态
                    checkbox.checked = !checkbox.checked;
                    // 触发change事件
                const changeEvent = new Event('change', { bubbles: true });
                checkbox.dispatchEvent(changeEvent);
                // 更新样式
                if (checkbox.checked) {
                    tag.classList.add('checked');
                } else {
                    tag.classList.remove('checked');
                }
            });
            
            // 复选框状态变化时更新标签样式
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    tag.classList.add('checked');
                } else {
                    tag.classList.remove('checked');
                }
            });
            
            // 初始化样式
            if (checkbox.checked) {
                tag.classList.add('checked');
            }
        }
    });
}

// 标记文档生成事件是否已初始化
let documentGenerationInitialized = false;

function initDocumentGeneration() {
    // 加载模板列表到下拉框
    loadTemplatesForGeneration();
    
    // 初始化步骤状态
    updateStepStatus();
    
    // 格式标签切换
    initFormatTags();
    
    // 防止重复绑定事件
    if (documentGenerationInitialized) {
        return;
    }
    documentGenerationInitialized = true;
    
    // 模板选择
    const templateSelect = document.getElementById('generationTemplateSelect');
    if (templateSelect) {
        templateSelect.addEventListener('change', function() {
            selectedTemplateForGeneration = this.value;
            updateStepStatus();
            if (this.value) {
                document.getElementById('step1')?.classList.add('active');
                document.getElementById('step2')?.classList.add('active');
            } else {
                document.getElementById('step1')?.classList.remove('active');
            }
        });
    }
    
    // 数据来源切换
    const dataSourceUpload = document.getElementById('dataSourceUpload');
    const dataSourceSelect = document.getElementById('dataSourceSelect');
    const uploadNewFileSection = document.getElementById('uploadNewFileSection');
    const selectFromListSection = document.getElementById('selectFromListSection');
    
    if (dataSourceUpload && dataSourceSelect) {
        dataSourceUpload.addEventListener('change', function() {
            if (this.checked) {
                uploadNewFileSection.style.display = 'block';
                selectFromListSection.style.display = 'none';
                uploadedDataFile = null;
                selectedDataFileId = null;
                document.getElementById('dataPreview').style.display = 'none';
                document.getElementById('step3').classList.remove('active');
            }
        });
        
        dataSourceSelect.addEventListener('change', function() {
            if (this.checked) {
                uploadNewFileSection.style.display = 'none';
                selectFromListSection.style.display = 'block';
                uploadedDataFile = null;
                // 加载文件列表
                loadDataFilesForSelection();
            }
        });
    }
    
    // 数据文件上传
    const dataUploadArea = document.getElementById('dataUploadArea');
    const dataFileInput = document.getElementById('dataFileInput');
    
    if (dataUploadArea) {
        dataUploadArea.addEventListener('click', function() {
            dataFileInput.click();
        });
        
        // 拖放上传
        dataUploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            dataUploadArea.classList.add('dragover');
        });
        
        dataUploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            dataUploadArea.classList.remove('dragover');
        });
        
        dataUploadArea.addEventListener('drop', async function(e) {
            e.preventDefault();
            dataUploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                dataFileInput.files = e.dataTransfer.files;
                uploadedDataFile = e.dataTransfer.files[0];
                selectedDataFileId = null;
                // 激活步骤2（选择数据文件）
                document.getElementById('step2')?.classList.add('active');
                updateStepStatus();
                
                // 自动推荐模板
                await recommendTemplates(uploadedDataFile.name);
            }
        });
    }
    
    if (dataFileInput) {
        dataFileInput.addEventListener('change', async function(e) {
            if (e.target.files.length > 0) {
                uploadedDataFile = e.target.files[0];
                selectedDataFileId = null;
                // 激活步骤2（选择数据文件）
                document.getElementById('step2')?.classList.add('active');
                updateStepStatus();
                
                // 自动推荐模板
                await recommendTemplates(uploadedDataFile.name);
            }
        });
    }
    
    // 从文件列表选择
    const dataFileSelect = document.getElementById('dataFileSelect');
    if (dataFileSelect) {
        dataFileSelect.addEventListener('change', async function() {
            if (this.value) {
                selectedDataFileId = parseInt(this.value);
                uploadedDataFile = null;
                // 获取文件信息
                try {
                    const response = await fetch(`${API_BASE_URL}/api/files/${selectedDataFileId}`, {
                        headers: getAuthHeaders()
                    });
                    if (response.ok) {
                        const fileData = await response.json();
                        const dataPreview = document.getElementById('dataPreview');
                        const dataPreviewContent = document.getElementById('dataPreviewContent');
                        if (dataPreview) dataPreview.style.display = 'block';
                        if (dataPreviewContent) {
                            dataPreviewContent.textContent = `数据文件：${fileData.filename}\n分类：${fileData.category || '-'}\n上传时间：${fileData.upload_time}`;
                        }
                        document.getElementById('step2')?.classList.add('active');
                        updateStepStatus();
                        
                        // 自动推荐模板
                        await recommendTemplates(fileData.filename);
                    }
                } catch (error) {
                    console.error('获取文件信息错误:', error);
                }
            } else {
                selectedDataFileId = null;
                const dataPreview = document.getElementById('dataPreview');
                if (dataPreview) dataPreview.style.display = 'none';
                document.getElementById('step2')?.classList.remove('active');
                updateStepStatus();
            }
        });
    }
    
    // 刷新文件列表按钮
    const refreshDataFileListBtn = document.getElementById('refreshDataFileListBtn');
    if (refreshDataFileListBtn) {
        refreshDataFileListBtn.addEventListener('click', function() {
            loadDataFilesForSelection();
        });
    }
    
    // 脱敏功能（已移除字段配置，使用默认规则）
    
    const genEnableEncryption = document.getElementById('genEnableEncryption');
    if (genEnableEncryption) {
        genEnableEncryption.addEventListener('change', function() {
            const passwordContainer = document.getElementById('pdfPasswordContainer');
            if (passwordContainer) {
                passwordContainer.style.display = this.checked ? 'block' : 'none';
            }
        });
    }
    
    // 水印配置显示/隐藏
    const genEnableWatermark = document.getElementById('genEnableWatermark');
    if (genEnableWatermark) {
        genEnableWatermark.addEventListener('change', function() {
            const watermarkConfig = document.getElementById('watermarkConfig');
            if (watermarkConfig) {
                watermarkConfig.style.display = this.checked ? 'block' : 'none';
                // 如果启用水印且图片列表为空，自动加载图片列表
                if (this.checked) {
                    const select = document.getElementById('watermarkImageSelect');
                    if (select && select.options.length <= 1) {
                        loadWatermarkImages();
                    }
                }
            }
        });
    }
    
    // 生成文档
    const generateDocumentBtn = document.getElementById('generateDocumentBtn');
    if (generateDocumentBtn) {
        generateDocumentBtn.addEventListener('click', function() {
            if (!selectedTemplateForGeneration) {
                alert('请先选择模板');
                return;
            }
            
            // 检查数据文件（直接检查是否选择了文件）
            if (!selectedDataFileId && !uploadedDataFile) {
                alert('请先选择数据文件');
                return;
            }
            
            startGeneration();
        });
    }
    
    // 重置按钮事件
    const resetGenerationBtn = document.getElementById('resetGenerationBtn');
    if (resetGenerationBtn) {
        resetGenerationBtn.addEventListener('click', function() {
            resetGenerationForm();
        });
    }
}

// 重置生成表单
function resetGenerationForm() {
    // 隐藏结果区域
    const resultDiv = document.getElementById('generationResult');
    if (resultDiv) resultDiv.style.display = 'none';
    
    // 隐藏进度条
    const progressDiv = document.getElementById('generationProgress');
    if (progressDiv) progressDiv.style.display = 'none';
    
    // 重置进度条
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    if (progressFill) progressFill.style.width = '0%';
    if (progressText) progressText.textContent = '准备中...';
    
    // 清空结果内容
    const resultContent = document.getElementById('generationResultContent');
    if (resultContent) resultContent.innerHTML = '';
    
    // 重置选中的模板和文件（可选，如果用户想保留则注释掉）
    // selectedTemplateForGeneration = null;
    // selectedDataFileId = null;
    // uploadedDataFile = null;
    
    // 滚动到页面顶部或生成区域顶部
    const generationTab = document.getElementById('documentGenerationTab');
    if (generationTab) {
        generationTab.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

async function loadTemplatesForGeneration() {
    const select = document.getElementById('generationTemplateSelect');
    select.innerHTML = '<option value="">请选择模板</option>';
    
    try {
        // 使用分组模式加载模板
        const response = await fetch(`${API_BASE_URL}/api/templates?page=1&page_size=100&group_by_name=true`, {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const data = await response.json();
            data.templates.forEach(template => {
                const option = document.createElement('option');
                option.value = template.id;
                const formatText = template.available_formats && template.available_formats.length > 0
                    ? ` [${template.available_formats.join(', ').toUpperCase()}]`
                    : '';
                option.textContent = `${template.name} (${template.version})${formatText}`;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('加载模板列表错误:', error);
    }
}

// 自动推荐模板
async function recommendTemplates(dataFilename) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/documents/recommend?data_filename=${encodeURIComponent(dataFilename)}`, {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.recommendations && data.recommendations.length > 0) {
                const select = document.getElementById('generationTemplateSelect');
                const topRecommendation = data.recommendations[0];
                
                // 自动选择推荐的模板
                select.value = topRecommendation.template_id;
                selectedTemplateForGeneration = topRecommendation.template_id;
                updateStepStatus();  // 更新步骤状态
                
                // 显示推荐提示
                const recommendDiv = document.getElementById('templateRecommendation');
                if (recommendDiv) {
                    recommendDiv.style.display = 'block';
                    recommendDiv.innerHTML = `
                        <div style="background-color: #e7f3ff; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                            <strong>💡 自动推荐模板：</strong>${topRecommendation.template_name}
                            <br><small>${topRecommendation.reason}</small>
                            ${topRecommendation.available_formats && topRecommendation.available_formats.length > 0
                                ? `<br><small>可用格式：${topRecommendation.available_formats.join(', ').toUpperCase()}</small>`
                                : ''}
                        </div>
                    `;
                } else {
                    alert(`💡 已自动推荐模板：${topRecommendation.template_name}\n${topRecommendation.reason}`);
                }
            }
        }
    } catch (error) {
        console.error('推荐模板错误:', error);
        // 不显示错误，静默失败
    }
}

// 加载数据文件列表（用于选择）
async function loadDataFilesForSelection() {
    const select = document.getElementById('dataFileSelect');
    if (!select) return;
    
    select.innerHTML = '<option value="">加载中...</option>';
    
    try {
        // 检查是否有token
        const token = getToken();
        if (!token) {
            console.error('未找到认证token，请重新登录');
            select.innerHTML = '<option value="">请先登录</option>';
            return;
        }
        
        // 获取所有文件，只显示JSON和CSV文件
        // 注意：后端限制page_size最大为100，所以需要分批加载
        let allFiles = [];
        let currentPage = 1;
        const pageSize = 100; // 后端限制的最大值
        let hasMore = true;
        
        while (hasMore) {
            const response = await fetch(`${API_BASE_URL}/api/files?page=${currentPage}&page_size=${pageSize}`, {
                headers: getAuthHeaders()
            });
            
            if (!response.ok) {
                if (response.status === 401) {
                    console.error('认证失败，请重新登录');
                    select.innerHTML = '<option value="">认证失败，请重新登录</option>';
                    removeToken();
                    window.location.href = 'index.html';
                    return;
                }
                const errorText = await response.text();
                console.error('加载文件列表失败:', response.status, errorText);
                select.innerHTML = '<option value="">加载失败（' + response.status + '）</option>';
                return;
            }
            
            const data = await response.json();
            const files = data.files || [];
            allFiles = allFiles.concat(files);
            
            // 检查是否还有更多数据
            hasMore = files.length === pageSize && allFiles.length < data.total;
            currentPage++;
            
            // 限制最多加载500个文件，避免无限循环
            if (allFiles.length >= 500) {
                break;
            }
        }
        
        select.innerHTML = '<option value="">请选择文件...</option>';
        
        // 过滤出JSON和CSV文件
        const dataFiles = allFiles.filter(file => {
            const filename = (file.filename || '').toLowerCase();
            return filename.endsWith('.json') || filename.endsWith('.csv');
        });
        
        if (dataFiles.length === 0) {
            select.innerHTML = '<option value="">暂无可用的数据文件（JSON/CSV）</option>';
            return;
        }
        
        dataFiles.forEach(file => {
            const option = document.createElement('option');
            option.value = file.id;
            const uploadTime = file.upload_time || file.created_at || '-';
            option.textContent = `${file.filename} (${file.category || '-'}) - ${uploadTime}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('加载文件列表错误:', error);
        select.innerHTML = '<option value="">加载失败: ' + error.message + '</option>';
    }
}

async function startGeneration() {
    const progressDiv = document.getElementById('generationProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const resultDiv = document.getElementById('generationResult');
    
    progressDiv.style.display = 'block';
    resultDiv.style.display = 'none';
    progressFill.style.width = '0%';
    progressText.textContent = '准备中...';
    
    try {
        const templateId = selectedTemplateForGeneration;
        
        if (!templateId) {
            alert('请选择模板');
            return;
        }
        
        // 获取选中的输出格式（多选）
        const selectedFormats = Array.from(document.querySelectorAll('input[name="outputFormat"]:checked'))
            .map(cb => cb.value);
        
        if (selectedFormats.length === 0) {
            alert('请至少选择一个输出格式');
            return;
        }
        
        // 检查数据文件（直接使用下拉框选择或上传的文件）
        if (!selectedDataFileId && !uploadedDataFile) {
            alert('请选择数据文件');
            return;
        }
        
        // 准备基础数据（所有格式共享）
        let baseFormData = null;
        let dataFile = null;
        let dataFileId = null;
        
        // 确定数据文件来源
        if (selectedDataFileId) {
            // 从文件列表选择的文件
            dataFileId = selectedDataFileId;
        } else if (uploadedDataFile) {
            // 上传的新文件
            dataFile = uploadedDataFile;
        }
        
        // 安全选项
        const enableMasking = document.getElementById('genEnableMasking').checked;
        const enableEncryption = document.getElementById('genEnableEncryption').checked;
        const pdfPassword = enableEncryption ? document.getElementById('genPdfPassword').value : '';
        
        // 批量生成多个格式
        const results = [];
        const totalFormats = selectedFormats.length;
        
        for (let i = 0; i < selectedFormats.length; i++) {
            const format = selectedFormats[i];
            const currentProgress = Math.floor((i / totalFormats) * 100);
            progressFill.style.width = currentProgress + '%';
            progressText.textContent = `正在生成 ${format.toUpperCase()} 格式 (${i + 1}/${totalFormats})...`;
            
            try {
                // 为每个格式构建FormData
                const formData = new FormData();
                formData.append('template_id', templateId);
                formData.append('output_format', format);
                
                // 根据数据来源添加数据文件
                if (dataFileId) {
                    // 从文件列表选择的文件
                    formData.append('data_file_id', dataFileId);
                } else if (dataFile) {
                    // 上传的新文件
                    formData.append('data_file', dataFile);
                }
                
                // 安全选项
        if (enableMasking) formData.append('enable_masking', 'true');
        if (enableEncryption) {
            formData.append('enable_encryption', 'true');
                    if (pdfPassword) formData.append('pdf_password', pdfPassword);
        }
        
        // 水印选项
        const enableWatermark = document.getElementById('genEnableWatermark').checked;
        if (enableWatermark) {
            formData.append('enable_watermark', 'true');
            
            // 水印文本
            const watermarkText = document.getElementById('genWatermarkText')?.value.trim();
            if (watermarkText) {
                formData.append('watermark_text', watermarkText);
            }
            
            // 水印图片ID
            const watermarkImageSelect = document.getElementById('watermarkImageSelect');
            const watermarkImageId = watermarkImageSelect?.value;
            if (watermarkImageId) {
                formData.append('watermark_image_id', watermarkImageId);
            }
        }
        
                // 动态元素选项
                // 表格默认启用（不需要选项）
                const enableChart = document.getElementById('enableChart').checked;
                formData.append('enable_table', 'true');  // 默认启用表格生成
                formData.append('enable_chart', enableChart ? 'true' : 'false');
        
        // 发送请求
        const response = await fetch(`${API_BASE_URL}/api/documents/generate`, {
            method: 'POST',
            headers: getAuthHeaders(false), // 文件上传不需要设置 Content-Type
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
                    results.push({
                        format: format,
                        success: true,
                        data: data
                    });
        } else {
            const errorText = await response.text().catch(() => '');
            let errorMessage = '生成失败';
            let errorLog = null;
            try {
                const errorData = JSON.parse(errorText);
                errorLog = errorData.error_log;
            if (errorData.detail) {
                if (typeof errorData.detail === 'string') {
                    errorMessage = errorData.detail;
                } else if (typeof errorData.detail === 'object') {
                    errorMessage = errorData.detail.detail || errorData.detail.message || '生成失败';
                }
                } else {
                    errorMessage = errorData.message || errorData.error || '生成失败';
            }
            } catch (e) {
                errorMessage = errorText || '生成失败，请查看控制台获取详细信息';
            }
            console.error(`生成 ${format} 格式失败:`, errorText);
                    results.push({
                        format: format,
                        success: false,
                error: errorMessage,
                errorLog: errorLog
                    });
                }
            } catch (error) {
                console.error(`生成 ${format} 格式错误:`, error);
                results.push({
                    format: format,
                    success: false,
                error: error.message || '生成失败：' + (error.toString ? error.toString() : '未知错误')
                });
            }
            }
            
        // 显示结果
        progressFill.style.width = '100%';
        progressText.textContent = '生成完成！';
            resultDiv.style.display = 'block';
        
        // 构建结果HTML
        let resultHtml = '<h4>批量生成结果</h4>';
        const successCount = results.filter(r => r.success).length;
        const failCount = results.filter(r => !r.success).length;
        
        resultHtml += `<p><strong>总计：</strong>成功 ${successCount} 个，失败 ${failCount} 个</p>`;
        resultHtml += '<div style="margin-top: 15px;">';
        
        results.forEach(result => {
            if (result.success) {
                resultHtml += `
                    <div style="padding: 10px; margin-bottom: 10px; background-color: #e8f5e9; border-radius: 5px; border-left: 4px solid #4caf50;">
                        <strong>✅ ${result.format.toUpperCase()} 格式生成成功</strong>
                        <p style="margin: 5px 0;">文件名：${result.data.filename || 'generated_document.' + result.format}</p>
                        <p style="margin: 5px 0;">文档ID：${result.data.document_id || '-'}</p>
                        ${result.data.document_id ? `<a href="${API_BASE_URL}/api/files/${result.data.document_id}/download" class="btn btn-small btn-primary" style="margin-top: 5px; display: inline-block;">下载 ${result.format.toUpperCase()}</a>` : ''}
                    </div>
            `;
            } else {
                // 如果有详细错误信息
                const errorLog = result.errorLog ? `<div style="margin-top: 5px; padding: 5px; background: #fff; border: 1px solid #ddd; font-size: 11px; white-space: pre-wrap; max-height: 100px; overflow-y: auto;">${escapeHtml(result.errorLog)}</div>` : '';
                resultHtml += `
                    <div style="padding: 10px; margin-bottom: 10px; background-color: #ffebee; border-radius: 5px; border-left: 4px solid #f44336;">
                        <strong>❌ ${result.format.toUpperCase()} 格式生成失败</strong>
                        <p style="margin: 5px 0; color: #c62828;">${escapeHtml(result.error)}</p>
                        ${errorLog}
                    </div>
                `;
            }
        });
        
        resultHtml += '</div>';
        document.getElementById('generationResultContent').innerHTML = resultHtml;
            
        // 如果当前在生成的文档标签页，刷新列表
        if (currentTab === 'generatedDocuments') {
            loadGeneratedDocuments();
        }
        
        // 只在所有生成完成后显示一次提示（不使用alert，使用页面内提示）
        // 滚动到结果区域
        resultDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) {
        console.error('生成文档错误:', error);
        progressText.textContent = '生成失败';
            resultDiv.style.display = 'block';
            document.getElementById('generationResultContent').innerHTML = `
                <div style="color: #d32f2f; padding: 15px; background-color: #ffebee; border-radius: 5px;">
                <h4 style="margin-top: 0; color: #c62828;">❌ 批量生成失败</h4>
                <p style="margin: 10px 0;"><strong>错误信息：</strong>${escapeHtml(error.message || '未知错误')}</p>
                </div>
            `;
    }
}

function addMaskingField() {
    const list = document.getElementById('maskingFieldsList');
    const item = document.createElement('div');
    item.className = 'masking-field-item';
    item.innerHTML = `
        <input type="text" placeholder="字段名（如：id_card）" class="form-input-small">
        <input type="text" placeholder="脱敏规则（如：XXX****XXX）" class="form-input-small">
        <button class="btn btn-small btn-danger" onclick="removeMaskingField(this)">删除</button>
    `;
    list.appendChild(item);
}

function removeMaskingField(btn) {
    btn.parentElement.remove();
}

// ==================== 生成的文档列表 ====================

async function loadGeneratedDocuments() {
    const searchInput = document.getElementById('generatedKeywordSearch')?.value || '';
    
    // 解析搜索输入：支持 "关键词 and 日期" 格式
    // 例如: "test and 2024-12" 或 "报表 and word"
    let keyword = '';
    let dateFilter = '';
    let formatFilter = '';
    
    if (searchInput.toLowerCase().includes(' and ')) {
        const parts = searchInput.toLowerCase().split(' and ').map(p => p.trim());
        parts.forEach(part => {
            // 检查是否是日期格式 (YYYY-MM 或 YYYY-MM-DD)
            if (/^\d{4}-\d{2}(-\d{2})?$/.test(part)) {
                dateFilter = part;
            }
            // 检查是否是格式类型
            else if (['pdf', 'word', 'html', 'docx'].includes(part.toLowerCase())) {
                formatFilter = part.toLowerCase();
                if (formatFilter === 'docx') formatFilter = 'word';
            }
            // 其他作为关键词
            else if (part) {
                keyword = keyword ? keyword + ' ' + part : part;
            }
        });
    } else {
        keyword = searchInput;
    }
    
    try {
        let url = `${API_BASE_URL}/api/documents/generated?page=${generatedCurrentPage}&page_size=${pageSize}`;
        if (keyword) url += `&keyword=${encodeURIComponent(keyword)}`;
        if (dateFilter) {
            // 如果只有年月，设置日期范围
            if (dateFilter.length === 7) {
                url += `&date_from=${dateFilter}-01`;
                // 获取下个月
                const [year, month] = dateFilter.split('-').map(Number);
                const nextMonth = month === 12 ? 1 : month + 1;
                const nextYear = month === 12 ? year + 1 : year;
                url += `&date_to=${nextYear}-${String(nextMonth).padStart(2, '0')}-01`;
            } else {
                url += `&date_from=${dateFilter}&date_to=${dateFilter}`;
            }
        }
        if (formatFilter) url += `&format_type=${formatFilter}`;
        
        const response = await fetch(url, {
            headers: getAuthHeaders(),
            cache: 'no-cache' // 禁用缓存，强制从服务器获取最新数据
        });
        
        // 处理401认证错误
        if (response.status === 401) {
            console.error('认证失败，请重新登录');
            removeToken();
            alert('登录已过期，请重新登录');
            window.location.reload();
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('生成的文档列表响应:', data);
        console.log('文档数量:', data.documents?.length || 0, '总数:', data.total || 0);
        
        renderGeneratedDocumentList(data.documents || []);
        renderGeneratedPagination(data.total || 0);
    } catch (error) {
        console.error('加载生成的文档列表错误:', error);
        renderGeneratedDocumentList([]);
        renderGeneratedPagination(0);
    }
}

function renderGeneratedDocumentList(documents) {
    const list = document.getElementById('generatedDocumentList');
    if (!list) return;
    
    list.innerHTML = '';
    
    if (documents.length === 0) {
        list.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">暂无生成的文档</div>';
        return;
    }
    
    documents.forEach(doc => {
        const docItem = document.createElement('div');
        docItem.className = 'file-item';
        docItem.dataset.docId = doc.id;
        
        // 构建权限限制显示
        const hasRestrictions = (doc.blocked_users && doc.blocked_users.length > 0) || 
                               (doc.blocked_departments && doc.blocked_departments.length > 0);
        let restrictionHtml = '';
        if (hasRestrictions) {
            const blockedUsersList = doc.blocked_users && doc.blocked_users.length > 0 
                ? `<span style="color: #dc3545;">禁止用户: ${doc.blocked_users.join(', ')}</span>` 
                : '';
            const blockedDeptsList = doc.blocked_departments && doc.blocked_departments.length > 0 
                ? `<span style="color: #dc3545;">禁止部门: ${doc.blocked_departments.join(', ')}</span>` 
                : '';
            restrictionHtml = `<div class="file-restrictions" style="font-size: 11px; color: #888; margin-top: 5px; padding: 5px; background: #fff3cd; border-radius: 4px;">
                🔒 ${blockedUsersList}${blockedUsersList && blockedDeptsList ? ' | ' : ''}${blockedDeptsList}
            </div>`;
        }
        
        docItem.innerHTML = `
            <div class="file-name">${doc.filename}</div>
            <div class="file-tags">
                <span class="file-tag">版本: ${doc.version}</span>
                <span class="file-tag">${doc.category || '未分类'}</span>
                <span class="file-tag">生成: ${doc.generated_time}</span>
                ${doc.template_name ? `<span class="file-tag" style="background-color: #28a745;">模板: ${doc.template_name}</span>` : ''}
                ${doc.tags && doc.tags.length > 0 ? doc.tags.map(tag => `<span class="file-tag">${tag}</span>`).join('') : ''}
            </div>
            <div class="file-uploader">生成人: ${doc.generator}</div>
            ${restrictionHtml}
            <div class="file-actions">
                <button class="btn btn-small btn-action" onclick="event.stopPropagation(); toggleGeneratedActions(${doc.id})">操作</button>
                <div class="file-action-menu" id="generatedActionMenu_${doc.id}">
                    ${currentUser && currentUser.role === 'admin' && doc.is_masked ? `
                        <div class="file-action-item" onclick="handleGeneratedAction(${doc.id}, 'download', 'masked')">下载脱敏版本</div>
                        <div class="file-action-item" onclick="handleGeneratedAction(${doc.id}, 'download', 'original')" style="color: #dc3545;">下载原始版本</div>
                    ` : `
                        <div class="file-action-item" onclick="handleGeneratedAction(${doc.id}, 'download')">下载</div>
                    `}
                    ${currentUser && currentUser.role === 'admin' ? `<div class="file-action-item" onclick="handleGeneratedAction(${doc.id}, 'permissions')">权限设置</div>` : ''}
                    <div class="file-action-item" onclick="handleGeneratedAction(${doc.id}, 'delete')" style="color: #dc3545;">删除</div>
                </div>
            </div>
        `;
        
        docItem.addEventListener('click', function(e) {
            if (e.target.closest('.file-actions') || e.target.closest('.file-action-menu')) {
                return;
            }
            document.querySelectorAll('.file-item').forEach(item => {
                item.classList.remove('selected');
            });
            docItem.classList.add('selected');
            selectedGeneratedDocId = doc.id;
            showGeneratedDocumentDetail(doc);
        });
        
        list.appendChild(docItem);
    });
}

function showGeneratedDocumentDetail(doc) {
    const detailPanel = document.getElementById('generatedDetailPanel');
    const detailContent = document.getElementById('generatedDetailContent');
    
    if (!detailPanel || !detailContent) return;
    
    detailPanel.style.display = 'block';
    detailContent.innerHTML = `
        <div class="detail-item">
            <strong>文件名：</strong>
            <span>${doc.filename}</span>
        </div>
        <div class="detail-item">
            <strong>版本：</strong>
            <span>${doc.version}</span>
        </div>
        <div class="detail-item">
            <strong>模板名称：</strong>
            <span>${doc.template_name || '-'}</span>
        </div>
        <div class="detail-item">
            <strong>生成时间：</strong>
            <span>${doc.generated_time}</span>
        </div>
        ${doc.blocked_users && doc.blocked_users.length > 0 ? `
        <div class="detail-item">
            <strong>禁止下载用户：</strong>
            <span style="color: #dc3545;">${doc.blocked_users.join(', ')}</span>
        </div>
        ` : ''}
        ${doc.blocked_departments && doc.blocked_departments.length > 0 ? `
        <div class="detail-item">
            <strong>禁止下载部门：</strong>
            <span style="color: #dc3545;">${doc.blocked_departments.join(', ')}</span>
        </div>
        ` : ''}
        <div class="detail-item">
            <strong>生成人：</strong>
            <span>${doc.generator || '系统'}</span>
        </div>
        <div class="detail-item">
            <strong>文件大小：</strong>
            <span>${doc.file_size ? (doc.file_size / 1024).toFixed(2) + ' KB' : '-'}</span>
        </div>
        <div class="detail-item">
            <strong>描述：</strong>
            <span>${doc.description || '-'}</span>
        </div>
    `;
}

function toggleGeneratedActions(docId) {
    document.querySelectorAll('.file-action-menu').forEach(menu => {
        if (menu.id !== `generatedActionMenu_${docId}`) {
            menu.classList.remove('show');
        }
    });
    
    const menu = document.getElementById(`generatedActionMenu_${docId}`);
    if (menu) {
        menu.classList.toggle('show');
    }
}

async function handleGeneratedAction(docId, action, version = null) {
    try {
        if (action === 'preview') {
            // 预览生成的文档
            window.open(`${API_BASE_URL}/api/documents/generated/${docId}/preview`, '_blank');
        } else if (action === 'download') {
            // 下载生成的文档
            let url = `${API_BASE_URL}/api/documents/generated/${docId}/download`;
            if (version) {
                url += `?version=${version}`;
            }
            
            const response = await fetch(url, {
                headers: getAuthHeaders()
            });
            
            // 处理401认证错误
            if (response.status === 401) {
                alert('登录已过期，请重新登录');
                removeToken();
                window.location.reload();
                return;
            }
            
            if (response.ok) {
                const blob = await response.blob();
                const url_obj = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                // 从响应头获取文件名
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = `generated_document_${docId}`;
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename="(.+)"/);
                    if (filenameMatch) {
                        filename = filenameMatch[1];
                    }
                }
                // 如果是原始版本，在文件名中添加标识
                if (version === 'original') {
                    const ext = filename.split('.').pop();
                    filename = filename.replace(`.${ext}`, `_原始版本.${ext}`);
                }
                a.href = url_obj;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url_obj);
                document.body.removeChild(a);
                alert('文档下载成功');
            } else {
                const error = await response.json().catch(() => ({ detail: '未知错误' }));
                alert('下载失败：' + (error.detail || '未知错误'));
            }
        } else if (action === 'permissions') {
            // 权限设置
            await showPermissionsDialog(docId);
        } else if (action === 'delete') {
            // 删除生成的文档
            if (confirm('确定要删除这个生成的文档吗？')) {
                const response = await fetch(`${API_BASE_URL}/api/documents/generated/${docId}`, {
                    method: 'DELETE',
                    headers: getAuthHeaders()
                });
                
                // 处理401认证错误
                if (response.status === 401) {
                    alert('登录已过期，请重新登录');
                    removeToken();
                    window.location.reload();
                    return;
                }
                
                if (response.ok) {
                    alert('文档已删除');
                    loadGeneratedDocuments();
                } else {
                    const error = await response.json().catch(() => ({ detail: '未知错误' }));
                    alert('删除失败：' + (error.detail || '未知错误'));
                }
            }
        }
    } catch (error) {
        console.error('操作失败:', error);
        alert('操作失败：' + error.message);
    }
    
    document.querySelectorAll('.file-action-menu').forEach(menu => {
        menu.classList.remove('show');
    });
}

function renderGeneratedPagination(total) {
    const pagination = document.getElementById('generatedPagination');
    if (!pagination) return;
    
    pagination.innerHTML = '';
    
    const totalPages = Math.ceil(total / pageSize);
    if (totalPages <= 1) return;
    
    const prevBtn = document.createElement('button');
    prevBtn.textContent = '«';
    prevBtn.disabled = generatedCurrentPage === 1;
    prevBtn.addEventListener('click', function() {
        if (generatedCurrentPage > 1) {
            generatedCurrentPage--;
            loadGeneratedDocuments();
        }
    });
    pagination.appendChild(prevBtn);
    
    for (let i = 1; i <= totalPages; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.textContent = i;
        pageBtn.className = i === generatedCurrentPage ? 'active' : '';
        pageBtn.addEventListener('click', function() {
            generatedCurrentPage = i;
            loadGeneratedDocuments();
        });
        pagination.appendChild(pageBtn);
    }
    
    const nextBtn = document.createElement('button');
    nextBtn.textContent = '»';
    nextBtn.disabled = generatedCurrentPage === totalPages;
    nextBtn.addEventListener('click', function() {
        if (generatedCurrentPage < totalPages) {
            generatedCurrentPage++;
            loadGeneratedDocuments();
        }
    });
    pagination.appendChild(nextBtn);
}

// ==================== 同步检查功能 ====================

async function checkSyncStatus() {
    // 检查数据库同步情况
    try {
        const response = await fetch(`${API_BASE_URL}/api/system/check-sync`, {
            headers: getAuthHeaders(),
            cache: 'no-cache'
        });
        
        // 处理401认证错误
        if (response.status === 401) {
            console.error('认证失败，请重新登录');
            removeToken();
            alert('登录已过期，请重新登录');
            window.location.reload();
            return;
        }
        
        if (!response.ok) {
            console.error('检查同步状态失败:', response.status, response.statusText);
            return;
        }
        
        const syncData = await response.json();
        
        // 如果不同步，显示详细信息
        if (!syncData.is_synced) {
            let message = '⚠️ 检测到数据不同步！\n\n';
            
            // 文件不同步
            if (!syncData.details.documents.synced) {
                const docDetails = syncData.details.documents;
                message += '📄 文件不同步：\n';
                message += `  MySQL: ${syncData.summary.documents.mysql_count} 条，MinIO: ${syncData.summary.documents.minio_count} 个，已同步: ${syncData.summary.documents.synced_count} 个\n`;
                if (docDetails.mysql_only.length > 0) {
                    message += `  ✗ 仅在MySQL中（${docDetails.mysql_only.length}个）：\n`;
                    docDetails.mysql_only.slice(0, 5).forEach(item => {
                        message += `    - ${item.filename} (ID: ${item.id})\n`;
                    });
                    if (docDetails.mysql_only.length > 5) {
                        message += `    ... 还有 ${docDetails.mysql_only.length - 5} 个\n`;
                    }
                }
                if (docDetails.minio_only.length > 0) {
                    message += `  ✗ 仅在MinIO中（${docDetails.minio_only.length}个）：\n`;
                    docDetails.minio_only.slice(0, 5).forEach(item => {
                        message += `    - ${item.path}\n`;
                    });
                    if (docDetails.minio_only.length > 5) {
                        message += `    ... 还有 ${docDetails.minio_only.length - 5} 个\n`;
                    }
                }
                message += '\n';
            }
            
            // 模板不同步
            if (!syncData.details.templates.synced) {
                const tplDetails = syncData.details.templates;
                message += '📋 模板不同步：\n';
                message += `  MySQL: ${syncData.summary.templates.mysql_count} 条，MinIO: ${syncData.summary.templates.minio_count} 个，已同步: ${syncData.summary.templates.synced_count} 个\n`;
                if (tplDetails.mysql_only.length > 0) {
                    message += `  ✗ 仅在MySQL中（${tplDetails.mysql_only.length}个）：\n`;
                    tplDetails.mysql_only.slice(0, 5).forEach(item => {
                        message += `    - ${item.template_name} (ID: ${item.id})\n`;
                    });
                    if (tplDetails.mysql_only.length > 5) {
                        message += `    ... 还有 ${tplDetails.mysql_only.length - 5} 个\n`;
                    }
                }
                if (tplDetails.minio_only.length > 0) {
                    message += `  ✗ 仅在MinIO中（${tplDetails.minio_only.length}个）：\n`;
                    tplDetails.minio_only.slice(0, 5).forEach(item => {
                        message += `    - ${item.path}\n`;
                    });
                    if (tplDetails.minio_only.length > 5) {
                        message += `    ... 还有 ${tplDetails.minio_only.length - 5} 个\n`;
                    }
                }
                message += '\n';
            }
            
            // 生成的文档不同步
            if (!syncData.details.generated_documents.synced) {
                const genDocDetails = syncData.details.generated_documents;
                message += '📝 生成的文档不同步：\n';
                message += `  MySQL: ${syncData.summary.generated_documents.mysql_count} 条，MinIO: ${syncData.summary.generated_documents.minio_count} 个，已同步: ${syncData.summary.generated_documents.synced_count} 个\n`;
                if (genDocDetails.mysql_only.length > 0) {
                    message += `  ✗ 仅在MySQL中（${genDocDetails.mysql_only.length}个）：\n`;
                    genDocDetails.mysql_only.slice(0, 5).forEach(item => {
                        message += `    - ${item.filename} (ID: ${item.id})\n`;
                    });
                    if (genDocDetails.mysql_only.length > 5) {
                        message += `    ... 还有 ${genDocDetails.mysql_only.length - 5} 个\n`;
                    }
                }
                if (genDocDetails.minio_only.length > 0) {
                    message += `  ✗ 仅在MinIO中（${genDocDetails.minio_only.length}个）：\n`;
                    genDocDetails.minio_only.slice(0, 5).forEach(item => {
                        message += `    - ${item.path}\n`;
                    });
                    if (genDocDetails.minio_only.length > 5) {
                        message += `    ... 还有 ${genDocDetails.minio_only.length - 5} 个\n`;
                    }
                }
                message += '\n';
            }
            
            message += '提示：建议使用"一键清空所有"功能清理孤立数据，或手动修复同步问题。';
            
            alert(message);
        } else {
            // 同步正常，显示统计信息（可选，也可以不显示）
            console.log('✅ 数据同步正常', syncData.summary);
        }
    } catch (error) {
        console.error('检查同步状态错误:', error);
        // 静默失败，不影响刷新操作
    }
}

// 生成的文档筛选和初始化
document.addEventListener('DOMContentLoaded', function() {
    const generatedFilterBtn = document.getElementById('generatedFilterBtn');
    if (generatedFilterBtn) {
        generatedFilterBtn.addEventListener('click', function() {
            generatedCurrentPage = 1;
            loadGeneratedDocuments();
        });
    }
    
    const generatedResetBtn = document.getElementById('generatedResetBtn');
    if (generatedResetBtn) {
        generatedResetBtn.addEventListener('click', function() {
            document.getElementById('generatedKeywordSearch').value = '';
            generatedCurrentPage = 1;
            loadGeneratedDocuments();
        });
    }
    
    const clearGeneratedBtn = document.getElementById('clearGeneratedBtn');
    if (clearGeneratedBtn) {
        clearGeneratedBtn.addEventListener('click', function() {
            if (confirm('确定要清空生成的文档列表吗？此操作将清空当前显示的列表。')) {
                const list = document.getElementById('generatedDocumentList');
                list.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">列表已清空</div>';
                const pagination = document.getElementById('generatedPagination');
                pagination.innerHTML = '';
                selectedGeneratedDocId = null;
                document.getElementById('generatedDetailPanel').style.display = 'none';
                alert('生成的文档列表已清空（占位）');
            }
        });
    }
});

// ==================== 访问日志 ====================

async function loadAccessLogs(page = 1) {
    try {
        // 简化：只加载所有日志，不进行筛选
        const url = `${API_BASE_URL}/api/logs?page=${logCurrentPage}&page_size=${pageSize}`;
        
        const response = await fetch(url, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        renderLogList(data.logs || []);
        renderLogPagination(data.total || 0);
    } catch (error) {
        console.error('加载访问日志错误:', error);
        // 显示空列表
        renderLogList([]);
        renderLogPagination(0);
    }
}

function renderLogList(logs) {
    const logList = document.getElementById('logList');
    logList.innerHTML = '';
    
    if (logs.length === 0) {
        logList.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">暂无访问日志</div>';
        return;
    }
    
    logs.forEach(log => {
        const logItem = document.createElement('div');
        logItem.className = 'log-item';
        
        const actionColors = {
            '查看': '#17a2b8',
            '下载': '#28a745',
            '修改': '#ffc107',
            '删除': '#dc3545'
        };
        
        logItem.innerHTML = `
            <div class="log-item-header">
                <span class="log-item-action" style="color: ${actionColors[log.action] || '#667eea'};">${log.action}</span>
                <span class="log-item-time">${log.time}</span>
            </div>
            <div class="log-item-details">
                <strong>用户：</strong>${log.user} | 
                <strong>文件：</strong>${log.filename}
            </div>
        `;
        
        logList.appendChild(logItem);
    });
}

function renderLogPagination(total) {
    const pagination = document.getElementById('logPagination');
    pagination.innerHTML = '';
    
    const totalPages = Math.ceil(total / pageSize);
    if (totalPages <= 1) return;
    
    for (let i = 1; i <= totalPages; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.textContent = i;
        pageBtn.className = i === logCurrentPage ? 'active' : '';
        pageBtn.addEventListener('click', function() {
            logCurrentPage = i;
            loadAccessLogs();
        });
        pagination.appendChild(pageBtn);
    }
}

// 访问日志（已移除筛选功能）
document.addEventListener('DOMContentLoaded', function() {
    // 一键清空访问日志按钮
    const clearLogsBtn = document.getElementById('clearLogsBtn');
    if (clearLogsBtn) {
        clearLogsBtn.addEventListener('click', async function() {
            if (confirm('确定要清空所有访问日志吗？此操作将删除MySQL和MinIO中的所有访问日志记录，且不可恢复！')) {
                try {
                    const response = await fetch(`${API_BASE_URL}/api/logs/clear`, {
                        method: 'DELETE',
                        headers: getAuthHeaders()
                    });
                    
                    if (response.status === 401) {
                        alert('登录已过期，请重新登录');
                        removeToken();
                        window.location.reload();
                        return;
                    }
                    
                    if (response.ok) {
                        const data = await response.json();
                        alert(data.message || '访问日志已清空');
                        
                        // 清空前端显示的日志列表
                        const logList = document.getElementById('logList');
                        if (logList) {
                            logList.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">日志列表已清空</div>';
                        }
                        const pagination = document.getElementById('logPagination');
                        if (pagination) {
                            pagination.innerHTML = '';
                        }
                        logCurrentPage = 1;
                        totalLogs = 0;
                    } else {
                        const error = await response.json().catch(() => ({ detail: '未知错误' }));
                        alert('清空访问日志失败：' + (error.detail || '未知错误'));
                    }
                } catch (error) {
                    console.error('清空访问日志错误:', error);
                    alert('清空访问日志失败：' + error.message);
                }
            }
        });
    }
});

// 初始化模板上传（延迟初始化，因为元素可能在模板管理标签页）
setTimeout(function() {
    if (document.getElementById('templateUploadArea')) {
        initTemplateUpload();
        // 初始化模板类型选择器
        if (typeof loadTemplateTypes === 'function') {
            loadTemplateTypes();
        }
        if (typeof initTemplateTypeSelectors === 'function') {
            initTemplateTypeSelectors();
        }
    }
}, 100);

// ==================== 图片管理功能 ====================

function initImageManagement() {
    // 图片上传功能（拖拽后直接上传）
    const imageFileInput = document.getElementById('imageFileInput');
    const imageUploadArea = document.getElementById('imageUploadArea');
    
    if (imageFileInput && imageUploadArea) {
        // 点击上传区域触发文件选择
        imageUploadArea.addEventListener('click', () => {
            imageFileInput.click();
        });
        
        // 拖拽上传（拖拽后直接上传）
        imageUploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            imageUploadArea.classList.add('drag-over');
        });
        
        imageUploadArea.addEventListener('dragleave', () => {
            imageUploadArea.classList.remove('drag-over');
        });
        
        imageUploadArea.addEventListener('drop', async (e) => {
            e.preventDefault();
            imageUploadArea.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                await handleImageUploadDirectly(Array.from(files));
            }
        });
        
        // 文件选择后直接上传
        imageFileInput.addEventListener('change', async () => {
            if (imageFileInput.files.length > 0) {
                await handleImageUploadDirectly(Array.from(imageFileInput.files));
            }
        });
    }
    
    // 刷新按钮
    const refreshImagesBtn = document.getElementById('refreshImagesBtn');
    if (refreshImagesBtn) {
        refreshImagesBtn.addEventListener('click', () => {
            loadImages();
        });
    }
    
    // 图片搜索（只保留关键词搜索）
    const imageKeywordSearch = document.getElementById('imageKeywordSearch');
    
    if (imageKeywordSearch) {
        let searchTimeout;
        imageKeywordSearch.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                imageCurrentPage = 1;
                loadImages();
            }, 500);
        });
    }
}

// 直接上传图片（拖拽或选择后立即上传）
async function handleImageUploadDirectly(files) {
    if (!files || files.length === 0) {
        return;
    }
    
    try {
        let successCount = 0;
        let failCount = 0;
        
        for (const file of files) {
            // 检查文件类型
            const fileName = file.name.toLowerCase();
            const validExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'];
            const isValid = validExtensions.some(ext => fileName.endsWith(ext));
            
            if (!isValid) {
                alert(`文件 ${file.name} 格式不支持，仅支持 JPG/PNG/GIF/WEBP/BMP/SVG 格式`);
                failCount++;
                continue;
            }
            
            try {
                const formData = new FormData();
                formData.append('file', file);
                // 使用文件名作为alt（如果没有扩展名，使用文件名）
                const altName = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
                formData.append('alt', altName);
                
                const response = await fetch(`${API_BASE_URL}/api/images/upload`, {
                    method: 'POST',
                    headers: getAuthHeaders(false),
                    body: formData
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || '上传失败');
                }
                
                const result = await response.json();
                console.log('图片上传成功:', result);
                successCount++;
            } catch (error) {
                console.error(`图片 ${file.name} 上传失败:`, error);
                failCount++;
            }
        }
        
        // 清空文件输入
        const imageFileInput = document.getElementById('imageFileInput');
        if (imageFileInput) {
            imageFileInput.value = '';
        }
        
        // 显示上传结果
        if (successCount > 0) {
            if (failCount > 0) {
                alert(`图片上传完成！成功 ${successCount} 个，失败 ${failCount} 个`);
            } else {
                alert(`图片上传成功！共上传 ${successCount} 个文件`);
            }
            // 刷新图片列表
            loadImages();
        } else {
            alert('所有图片上传失败');
        }
    } catch (error) {
        console.error('图片上传失败:', error);
        alert('图片上传失败: ' + error.message);
    }
}

// 加载水印图片列表
async function loadWatermarkImages() {
    const select = document.getElementById('watermarkImageSelect');
    if (!select) return;
    
    try {
        // 加载所有图片（不分页，最多100张）
        const response = await fetch(`${API_BASE_URL}/api/images?page=1&page_size=100`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                alert('登录已过期，请重新登录');
                removeToken();
                window.location.reload();
                return;
            }
            throw new Error('加载图片列表失败');
        }
        
        const data = await response.json();
        const images = data.images || [];
        
        // 清空现有选项（保留第一个默认选项）
        select.innerHTML = '<option value="">选择水印图片（可选）</option>';
        
        if (images.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = '暂无可用的图片';
            option.disabled = true;
            select.appendChild(option);
            return;
        }
        
        // 添加图片选项
        images.forEach(image => {
            const option = document.createElement('option');
            option.value = image.id;
            option.textContent = `${image.filename} (ID: ${image.id})`;
            option.title = image.alt || image.filename;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('加载水印图片列表错误:', error);
        select.innerHTML = '<option value="">加载失败: ' + error.message + '</option>';
    }
}

async function loadImages() {
    const imageList = document.getElementById('imageList');
    if (!imageList) return;
    
    const keyword = document.getElementById('imageKeywordSearch')?.value.trim() || '';
    
    try {
        const params = new URLSearchParams({
            page: imageCurrentPage,
            page_size: imagePageSize
        });
        if (keyword) {
            params.append('keyword', keyword);
        }
        
        const response = await fetch(`${API_BASE_URL}/api/images?${params}`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error('加载图片列表失败');
        }
        
        const data = await response.json();
        
        // 渲染图片列表
        imageList.innerHTML = '';
        if (data.images && data.images.length > 0) {
            data.images.forEach(image => {
                const imageItem = document.createElement('div');
                imageItem.className = 'image-item';
                imageItem.innerHTML = `
                    <div class="image-preview">
                        <img data-image-id="${image.id}" 
                             alt="${escapeHtml(image.alt)}" 
                             style="max-width: 100%; max-height: 300px; object-fit: contain;"
                             onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'200\\' height=\\'200\\'%3E%3Crect fill=\\'%23ddd\\' width=\\'200\\' height=\\'200\\'/%3E%3Ctext x=\\'50%25\\' y=\\'50%25\\' text-anchor=\\'middle\\' dy=\\'.3em\\' fill=\\'%23999\\'%3E图片加载失败%3C/text%3E%3C/svg%3E'">
                    </div>
                    <div class="image-info">
                        <div class="image-name">${escapeHtml(image.filename)}</div>
                        <div class="image-alt">${escapeHtml(image.alt)}</div>
                        <div class="image-meta">
                            <span>图片ID: <strong>${image.id}</strong></span>
                            <span>上传时间: ${image.upload_time}</span>
                            <span>大小: ${(image.file_size / 1024).toFixed(2)} KB</span>
                        </div>
                        <div class="image-actions">
                            <button class="btn btn-small btn-success" onclick="copyImageId(${image.id}, '${escapeHtml(image.alt)}')">复制ID</button>
                            <button class="btn btn-small btn-danger" onclick="deleteImage(${image.id})">删除</button>
                        </div>
                    </div>
                `;
                imageList.appendChild(imageItem);
                
                // 异步加载图片（带认证）
                loadImageWithAuth(image.id, imageItem.querySelector('img'));
            });
        } else {
            imageList.innerHTML = '<div class="empty-message">暂无图片</div>';
        }
        
        // 更新分页
        updateImagePagination(data.total, data.page_size);
    } catch (error) {
        console.error('加载图片列表失败:', error);
        imageList.innerHTML = '<div class="error-message">加载图片列表失败</div>';
    }
}

function updateImagePagination(total, pageSize) {
    const pagination = document.getElementById('imagePagination');
    if (!pagination) return;
    
    const totalPages = Math.ceil(total / pageSize);
    pagination.innerHTML = '';
    
    if (totalPages <= 1) return;
    
    // 上一页
    const prevBtn = document.createElement('button');
    prevBtn.className = 'btn btn-small';
    prevBtn.textContent = '上一页';
    prevBtn.disabled = imageCurrentPage <= 1;
    prevBtn.addEventListener('click', () => {
        if (imageCurrentPage > 1) {
            imageCurrentPage--;
            loadImages();
        }
    });
    pagination.appendChild(prevBtn);
    
    // 页码
    const pageInfo = document.createElement('span');
    pageInfo.textContent = `第 ${imageCurrentPage} 页 / 共 ${totalPages} 页 (共 ${total} 张图片)`;
    pagination.appendChild(pageInfo);
    
    // 下一页
    const nextBtn = document.createElement('button');
    nextBtn.className = 'btn btn-small';
    nextBtn.textContent = '下一页';
    nextBtn.disabled = imageCurrentPage >= totalPages;
    nextBtn.addEventListener('click', () => {
        if (imageCurrentPage < totalPages) {
            imageCurrentPage++;
            loadImages();
        }
    });
    pagination.appendChild(nextBtn);
}

// 使用认证加载图片
async function loadImageWithAuth(imageId, imgElement) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/images/${imageId}/download`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error('加载图片失败');
        }
        
        const blob = await response.blob();
        const imageUrl = URL.createObjectURL(blob);
        imgElement.src = imageUrl;
        
        // 图片加载成功后，清理blob URL（可选，如果图片很多可以延迟清理）
        imgElement.onload = () => {
            // 可以在这里清理旧的blob URL，但为了性能，我们保留它
        };
    } catch (error) {
        console.error('加载图片失败:', error);
        // onerror 处理程序会显示错误占位符
    }
}

function copyImageId(imageId, alt) {
    const imageIdStr = `image_id:${imageId}`;
    const jsonExample = `{"id": ${imageId}, "alt": "${alt}"}`;
    navigator.clipboard.writeText(imageIdStr).then(() => {
        alert(`图片ID已复制到剪贴板:\n${imageIdStr}\n\n在JSON中使用:\n${jsonExample}\n\n或者使用简化格式:\n"image_id:${imageId}"`);
    }).catch(err => {
        console.error('复制失败:', err);
        prompt('请手动复制以下ID:', imageIdStr);
    });
}

function copyImageUrl(imageId, alt) {
    const url = `${API_BASE_URL}/api/images/${imageId}/download`;
    navigator.clipboard.writeText(url).then(() => {
        alert(`图片URL已复制到剪贴板:\n${url}\n\n在JSON中使用: {"src": "${url}", "alt": "${alt}"}`);
    }).catch(err => {
        console.error('复制失败:', err);
        prompt('请手动复制以下URL:', url);
    });
}

async function deleteImage(imageId) {
    if (!confirm('确定要删除这张图片吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/files/${imageId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '删除失败');
        }
        
        alert('图片删除成功！');
        loadImages();
    } catch (error) {
        console.error('删除图片失败:', error);
        alert('删除图片失败: ' + error.message);
    }
}

// 全局函数（供 HTML 中的 onclick 调用）
window.toggleFileActions = toggleFileActions;
window.handleFileAction = handleFileAction;
window.toggleTemplateActions = toggleTemplateActions;
window.handleTemplateAction = handleTemplateAction;
window.toggleGeneratedActions = toggleGeneratedActions;
window.handleGeneratedAction = handleGeneratedAction;
window.viewVersion = viewVersion;
window.addMaskingField = addMaskingField;
window.removeMaskingField = removeMaskingField;
window.copyImageId = copyImageId;
window.copyImageUrl = copyImageUrl;
window.deleteImage = deleteImage;

// ==================== 权限设置功能 ====================

let currentPermissionsDocId = null;

// 显示权限设置对话框
async function showPermissionsDialog(docId) {
    currentPermissionsDocId = docId;
    const modal = document.getElementById('permissionsModal');
    if (!modal) return;
    
    // 清空标签列表
    document.getElementById('blockedUsersTags').innerHTML = '';
    document.getElementById('blockedDepartmentsTags').innerHTML = '';
    
    // 加载当前权限设置
    try {
        const response = await fetch(`${API_BASE_URL}/api/documents/generated/${docId}`, {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const doc = await response.json();
            // 显示已设置的权限
            if (doc.blocked_users && Array.isArray(doc.blocked_users)) {
                doc.blocked_users.forEach(user => {
                    addPermissionTag('blockedUsers', user);
                });
            }
            if (doc.blocked_departments && Array.isArray(doc.blocked_departments)) {
                doc.blocked_departments.forEach(dept => {
                    addPermissionTag('blockedDepartments', dept);
                });
            }
        }
    } catch (error) {
        console.error('加载权限设置失败:', error);
    }
    
    modal.style.display = 'block';
}

// 关闭权限设置对话框
function closePermissionsModal() {
    const modal = document.getElementById('permissionsModal');
    if (modal) {
        modal.style.display = 'none';
    }
    currentPermissionsDocId = null;
}

// 处理标签输入
function handleTagInput(event, type) {
    if (event.key === 'Enter') {
        event.preventDefault();
        const input = document.getElementById(`${type}Input`);
        const value = input.value.trim();
        if (value) {
            addPermissionTag(type, value);
            input.value = '';
        }
    }
}

// 添加权限标签
function addPermissionTag(type, value) {
    const tagsContainer = document.getElementById(`${type}Tags`);
    if (!tagsContainer) return;
    
    // 检查是否已存在
    const existingTags = Array.from(tagsContainer.children).map(tag => tag.dataset.value);
    if (existingTags.includes(value)) {
        return;
    }
    
    const tagItem = document.createElement('span');
    tagItem.className = 'tag-item';
    tagItem.dataset.value = value;
    tagItem.innerHTML = `
        <span>${escapeHtml(value)}</span>
        <span class="tag-remove" onclick="removePermissionTag('${type}', '${value}')">&times;</span>
    `;
    tagsContainer.appendChild(tagItem);
}

// 删除权限标签
function removePermissionTag(type, value) {
    const tagsContainer = document.getElementById(`${type}Tags`);
    if (!tagsContainer) return;
    
    const tagItem = tagsContainer.querySelector(`[data-value="${value}"]`);
    if (tagItem) {
        tagItem.remove();
    }
}

// 保存权限设置
async function savePermissions() {
    if (!currentPermissionsDocId) return;
    
    // 收集标签值
    const blockedUsers = Array.from(document.getElementById('blockedUsersTags').children)
        .map(tag => tag.dataset.value);
    const blockedDepartments = Array.from(document.getElementById('blockedDepartmentsTags').children)
        .map(tag => tag.dataset.value);
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/generated/${currentPermissionsDocId}/permissions`, {
            method: 'PUT',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                blocked_users: blockedUsers,
                blocked_departments: blockedDepartments
            })
        });
        
        if (response.status === 401) {
            alert('登录已过期，请重新登录');
            removeToken();
            window.location.reload();
            return;
        }
        
        if (response.ok) {
            alert('权限设置已保存');
            closePermissionsModal();
            // 重新加载文档列表
            loadGeneratedDocuments();
        } else {
            const error = await response.json().catch(() => ({ detail: '未知错误' }));
            alert('保存失败：' + (error.detail || '未知错误'));
        }
    } catch (error) {
        console.error('保存权限设置失败:', error);
        alert('保存失败：' + error.message);
    }
}

// 全局函数（供HTML调用）
window.showPermissionsDialog = showPermissionsDialog;
window.handleTagInput = handleTagInput;
window.removePermissionTag = removePermissionTag;
window.closePermissionsModal = closePermissionsModal;
window.savePermissions = savePermissions;

// 点击模态框外部关闭
window.addEventListener('click', function(event) {
    const modal = document.getElementById('permissionsModal');
    if (event.target === modal) {
        closePermissionsModal();
    }
});

// ==================== 用户管理功能 ====================

// 加载用户列表
async function loadUsers(page = 1) {
    const userList = document.getElementById('userList');
    if (!userList) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/users?page=${page}&page_size=20`, {
            method: 'GET',
            headers: getAuthHeaders()
        });
        
        if (response.status === 401) {
            alert('登录已过期，请重新登录');
            removeToken();
            window.location.reload();
            return;
        }
        
        if (response.status === 403) {
            userList.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">无权限访问用户列表，仅管理员可查看</div>';
            return;
        }
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: '未知错误' }));
            userList.innerHTML = `<div style="text-align: center; padding: 20px; color: #d32f2f;">加载失败：${error.detail || '未知错误'}</div>`;
            return;
        }
        
        const data = await response.json();
        totalUsers = data.total || 0;
        userCurrentPage = data.page || 1;
        
        if (!data.users || data.users.length === 0) {
            userList.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">暂无用户数据</div>';
            updateUserPagination(0, 1);
            return;
        }
        
        // 渲染用户列表
        userList.innerHTML = data.users.map(user => `
            <div class="file-item">
                <div class="file-name">${escapeHtml(user.display_name || user.username)}</div>
                <div class="file-info">
                    <div class="file-tags">
                        <span class="file-tag" style="background-color: #667eea; color: white;">用户名: ${escapeHtml(user.username)}</span>
                        <span class="file-tag" style="background-color: ${user.role === 'admin' ? '#dc3545' : '#28a745'}; color: white;">角色: ${escapeHtml(user.role || 'user')}</span>
                        ${user.department ? `<span class="file-tag" style="background-color: #17a2b8; color: white;">部门: ${escapeHtml(user.department)}</span>` : ''}
                    </div>
                </div>
            </div>
        `).join('');
        
        updateUserPagination(totalUsers, userCurrentPage);
    } catch (error) {
        console.error('加载用户列表错误:', error);
        if (userList) {
            userList.innerHTML = '<div style="text-align: center; padding: 20px; color: #d32f2f;">加载失败：网络错误</div>';
        }
    }
}

// 更新用户列表分页
function updateUserPagination(total, currentPage) {
    const pagination = document.getElementById('userPagination');
    if (!pagination) return;
    
    const pageSize = 20;
    const totalPages = Math.ceil(total / pageSize);
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let paginationHTML = '';
    
    // 上一页按钮
    if (currentPage > 1) {
        paginationHTML += `<button onclick="userCurrentPage = ${currentPage - 1}; loadUsers(${currentPage - 1});">上一页</button>`;
    }
    
    // 页码按钮
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            if (i === currentPage) {
                paginationHTML += `<button class="active">${i}</button>`;
            } else {
                paginationHTML += `<button onclick="userCurrentPage = ${i}; loadUsers(${i});">${i}</button>`;
            }
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            paginationHTML += `<button disabled>...</button>`;
        }
    }
    
    // 下一页按钮
    if (currentPage < totalPages) {
        paginationHTML += `<button onclick="userCurrentPage = ${currentPage + 1}; loadUsers(${currentPage + 1});">下一页</button>`;
    }
    
    pagination.innerHTML = paginationHTML;
}

// 初始化用户管理功能（在DOMContentLoaded中调用）
const originalDOMContentLoaded = window.addEventListener;
document.addEventListener('DOMContentLoaded', function() {
    // 刷新用户列表按钮
    const refreshUsersBtn = document.getElementById('refreshUsersBtn');
    if (refreshUsersBtn) {
        refreshUsersBtn.addEventListener('click', function() {
            userCurrentPage = 1;
            loadUsers(1);
        });
    }
    
    // 标签页切换监听
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            if (tabName === 'userManagement') {
                loadUsers(1);
            }
        });
    });
});
