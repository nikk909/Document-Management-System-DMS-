// 图片文件关联功能

// 加载文件列表用于图片关联
async function loadFilesForImageTags() {
    const imageFileTags = document.getElementById('imageFileTags');
    if (!imageFileTags) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/files?page=1&page_size=1000`, {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const data = await response.json();
            imageFileTags.innerHTML = '<option value="">请选择文件...</option>';
            
            if (data.files && data.files.length > 0) {
                data.files.forEach(file => {
                    const option = document.createElement('option');
                    option.value = file.id;
                    option.textContent = `${file.filename} (v${file.version})`;
                    imageFileTags.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('加载文件列表失败:', error);
    }
}

