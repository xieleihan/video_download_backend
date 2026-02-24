/**
 * 联通网盘文件上传模块
 */
const API_BASE = window.location.origin;
const UPLOAD_URL = `${API_BASE}/api/video/wopan/file-upload`;

// DOM
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');

// ========== 工具函数 ==========

function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
}

function getFileExt(name) {
    const dot = name.lastIndexOf('.');
    return dot > -1 ? name.slice(dot + 1).toUpperCase() : '?';
}

// ========== UI 渲染 ==========

function createFileItem(file) {
    const id = `file-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    const el = document.createElement('div');
    el.className = 'file-item';
    el.id = id;
    el.innerHTML = `
        <div class="file-icon">${getFileExt(file.name)}</div>
        <div class="file-info">
            <div class="file-name" title="${file.name}">${file.name}</div>
            <div class="file-meta">${formatSize(file.size)}</div>
            <div class="file-progress">
                <div class="file-progress-bar" id="${id}-bar"></div>
            </div>
        </div>
        <div class="file-status waiting" id="${id}-status">等待中</div>
    `;
    fileList.prepend(el);
    return id;
}

function updateProgress(id, percent) {
    const bar = document.getElementById(`${id}-bar`);
    const status = document.getElementById(`${id}-status`);
    if (bar) bar.style.width = percent + '%';
    if (status) {
        status.textContent = percent + '%';
        status.className = 'file-status uploading';
    }
}

function markSuccess(id) {
    const bar = document.getElementById(`${id}-bar`);
    const status = document.getElementById(`${id}-status`);
    if (bar) { bar.style.width = '100%'; bar.classList.add('success'); }
    if (status) { status.textContent = '已完成'; status.className = 'file-status success'; }
}

function markError(id, msg) {
    const bar = document.getElementById(`${id}-bar`);
    const status = document.getElementById(`${id}-status`);
    if (bar) bar.classList.add('error');
    if (status) { status.textContent = msg || '失败'; status.className = 'file-status error'; }
}

// ========== 上传逻辑 ==========

function uploadFile(file) {
    const id = createFileItem(file);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('directory_id', '0');

    const xhr = new XMLHttpRequest();
    xhr.open('POST', UPLOAD_URL);

    xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
            updateProgress(id, Math.round((e.loaded / e.total) * 100));
        }
    });

    xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
            try {
                const res = JSON.parse(xhr.responseText);
                if (res.status === 'success') {
                    markSuccess(id);
                } else {
                    markError(id, res.detail || '上传失败');
                }
            } catch {
                markError(id, '响应解析失败');
            }
        } else {
            let msg = '上传失败';
            try { msg = JSON.parse(xhr.responseText).detail || msg; } catch {}
            markError(id, msg);
        }
    });

    xhr.addEventListener('error', () => markError(id, '网络错误'));
    xhr.addEventListener('timeout', () => markError(id, '请求超时'));
    xhr.timeout = 600000; // 10 min

    xhr.send(formData);
}

function handleFiles(files) {
    Array.from(files).forEach(uploadFile);
}

// ========== 事件绑定 ==========

dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
    fileInput.value = '';
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
});
