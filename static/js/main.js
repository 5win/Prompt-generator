// 전역 유틸리티 함수들

// 클립보드 복사 유틸리티
async function copyToClipboardUtil(text, successMessage = '클립보드에 복사되었습니다!') {
    try {
        await navigator.clipboard.writeText(text);
        showToast(successMessage, 'success');
        return true;
    } catch (err) {
        // 폴백: 텍스트 영역 생성해서 복사
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        
        try {
            const successful = document.execCommand('copy');
            if (successful) {
                showToast(successMessage, 'success');
                return true;
            } else {
                throw new Error('복사 실패');
            }
        } catch (err) {
            showToast('복사에 실패했습니다. 수동으로 복사해주세요.', 'error');
            return false;
        } finally {
            document.body.removeChild(textarea);
        }
    }
}

// 토스트 메시지 표시
function showToast(message, type = 'info') {
    // 기존 토스트가 있으면 제거
    const existingToast = document.getElementById('dynamicToast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // 토스트 컨테이너 생성 또는 가져오기
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // 아이콘과 색상 설정
    const iconMap = {
        success: 'fas fa-check-circle text-success',
        error: 'fas fa-exclamation-triangle text-danger',
        warning: 'fas fa-exclamation-circle text-warning',
        info: 'fas fa-info-circle text-info'
    };
    
    const icon = iconMap[type] || iconMap.info;
    
    // 토스트 HTML 생성
    const toastHtml = `
        <div id="dynamicToast" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <i class="${icon} me-2"></i>
                <strong class="me-auto">알림</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    toastContainer.innerHTML = toastHtml;
    
    // 토스트 표시
    const toastElement = document.getElementById('dynamicToast');
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 3000
    });
    toast.show();
    
    // 토스트가 숨겨진 후 DOM에서 제거
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

// 로딩 스피너 표시/숨김
function showLoading(element, text = '처리 중...') {
    const originalContent = element.innerHTML;
    element.dataset.originalContent = originalContent;
    element.innerHTML = `
        <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
        ${text}
    `;
    element.disabled = true;
}

function hideLoading(element) {
    const originalContent = element.dataset.originalContent;
    if (originalContent) {
        element.innerHTML = originalContent;
        delete element.dataset.originalContent;
    }
    element.disabled = false;
}

// API 호출 헬퍼
async function apiCall(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, finalOptions);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// 폼 유효성 검사 헬퍼
function validateForm(formElement) {
    const requiredFields = formElement.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// 텍스트 포맷팅 유틸리티
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function truncateText(text, maxLength = 100) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// 키보드 단축키 등록
function registerShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl+S: 현재 폼 저장 (기본 저장 동작 방지)
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            const submitButton = document.querySelector('button[type="submit"]');
            if (submitButton && !submitButton.disabled) {
                submitButton.click();
            }
        }
        
        // Escape: 모달 닫기
        if (e.key === 'Escape') {
            const openModal = document.querySelector('.modal.show');
            if (openModal) {
                const modal = bootstrap.Modal.getInstance(openModal);
                if (modal) modal.hide();
            }
        }
        
        // Ctrl+C: 프롬프트 내용 복사 (프롬프트 상세 페이지에서)
        if (e.ctrlKey && e.key === 'c' && !e.target.matches('input, textarea')) {
            const promptContent = document.getElementById('promptContent');
            if (promptContent) {
                e.preventDefault();
                copyToClipboardUtil(promptContent.textContent);
            }
        }
    });
}

// 자동 저장 기능
function setupAutoSave(formId, interval = 30000) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    const saveKey = `autosave_${formId}`;
    
    // 저장된 데이터 복원
    function restoreData() {
        const savedData = localStorage.getItem(saveKey);
        if (savedData) {
            try {
                const data = JSON.parse(savedData);
                Object.keys(data).forEach(fieldName => {
                    const field = form.querySelector(`[name="${fieldName}"]`);
                    if (field) {
                        field.value = data[fieldName];
                    }
                });
                showToast('이전에 작성하던 내용을 복원했습니다.', 'info');
            } catch (e) {
                console.error('Failed to restore autosave data:', e);
            }
        }
    }
    
    // 데이터 저장
    function saveData() {
        const formData = new FormData(form);
        const data = {};
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        localStorage.setItem(saveKey, JSON.stringify(data));
    }
    
    // 저장된 데이터 삭제
    function clearSavedData() {
        localStorage.removeItem(saveKey);
    }
    
    // 폼 필드 변경 시 자동 저장
    form.addEventListener('input', debounce(saveData, 2000));
    
    // 폼 제출 시 저장된 데이터 삭제
    form.addEventListener('submit', clearSavedData);
    
    // 페이지 로드 시 데이터 복원
    restoreData();
    
    return { saveData, clearSavedData, restoreData };
}

// 디바운스 유틸리티
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 페이지별 초기화
function initializePage() {
    const path = window.location.pathname;
    
    if (path.includes('/templates/create') || path.includes('/templates/') && path.includes('/edit')) {
        // 템플릿 생성/수정 페이지
        setupAutoSave('templateForm');
    } else if (path.includes('/prompts/create/')) {
        // 프롬프트 생성 페이지
        setupAutoSave('promptForm');
    }
    
    // 전역 기능 초기화
    registerShortcuts();
    
    // 모든 hover-card에 애니메이션 추가
    document.querySelectorAll('.hover-card').forEach(card => {
        card.classList.add('fade-in');
    });
    
    // 툴팁 초기화
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// DOM 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', initializePage);

// 페이지 가시성 변경 시 처리
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
        // 페이지가 다시 보일 때 필요한 경우 새로고침
        const pendingElements = document.querySelectorAll('.badge.bg-warning');
        if (pendingElements.length > 0) {
            // Gemini 처리 중인 항목이 있으면 상태 확인
            setTimeout(() => {
                location.reload();
            }, 1000);
        }
    }
});

// 전역 에러 핸들러
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    showToast('예상치 못한 오류가 발생했습니다.', 'error');
});

// 전역 Promise rejection 핸들러
window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    showToast('네트워크 오류가 발생했습니다.', 'error');
});

// 네트워크 상태 모니터링
window.addEventListener('online', function() {
    showToast('인터넷 연결이 복구되었습니다.', 'success');
});

window.addEventListener('offline', function() {
    showToast('인터넷 연결이 끊어졌습니다.', 'warning');
}); 