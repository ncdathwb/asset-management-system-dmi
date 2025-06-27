// Initialize variables
let isBranchAdmin = false;
let currentBranch = '';
let lastFocusedElement = null;

// Setup CSRF token for all AJAX requests
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", $('meta[name="csrf-token"]').attr('content'));
        }
    }
});

// Initialize settings page
function initSettings() {
    isBranchAdmin = $('#isBranchAdmin').val() === 'true';
    currentBranch = $('#currentBranch').val();
    
    // Initialize modals with proper focus management
    initDepartmentModals();
    initAssetTypeModals();
    
    // Load initial data
    loadDepartments();
    loadAssetTypes();
}

// Department Management
function initDepartmentModals() {
    // Store last focused element before opening modal
    $('#addDepartmentModal, #editDepartmentModal').on('show.bs.modal', function() {
        lastFocusedElement = document.activeElement;
    });

    // Restore focus when modal is hidden
    $('#addDepartmentModal, #editDepartmentModal').on('hidden.bs.modal', function() {
        if (lastFocusedElement) {
            lastFocusedElement.focus();
        }
        // Clear form and remove any validation states
        $(this).find('form').trigger('reset');
        $(this).find('.is-invalid').removeClass('is-invalid');
    });

    // Focus first input when modal is shown
    $('#addDepartmentModal, #editDepartmentModal').on('shown.bs.modal', function() {
        $(this).find('input[type="text"]:first').focus();
    });

    // Add Department Form
    $('#departmentForm').on('submit', function(e) {
        e.preventDefault();
        const formData = $(this).serialize();
        const submitBtn = $(this).find('button[type="submit"]');
        const originalText = submitBtn.html();
        
        // Disable submit button to prevent double submission
        submitBtn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> 処理中...');
        
        $.ajax({
            url: '/api/settings/departments',
            method: 'POST',
            data: formData,
            success: function(response) {
                if (response.success) {
                    showNotification('success', response.message);
                    $('#departmentForm').trigger('reset');
                    $('#addDepartmentModal').modal('hide');
                    loadDepartments();
                } else {
                    showNotification('error', response.message || '部署の追加に失敗しました');
                }
            },
            error: function(xhr) {
                showNotification('error', '部署の追加に失敗しました: ' + (xhr.responseJSON && xhr.responseJSON.message ? xhr.responseJSON.message : ''));
            },
            complete: function() {
                // Re-enable submit button
                submitBtn.prop('disabled', false).html(originalText);
            }
        });
    });

    // Edit Department Form
    $('#editDepartmentForm').on('submit', function(e) {
        e.preventDefault();
        const formData = $(this).serialize();
        const id = $('#editDepartmentId').val();
        const submitBtn = $(this).find('button[type="submit"]');
        const originalText = submitBtn.html();
        
        // Disable submit button to prevent double submission
        submitBtn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> 処理中...');
        
        $.ajax({
            url: `/api/settings/departments/${id}`,
            method: 'PUT',
            data: formData,
            success: function(response) {
                showNotification('success', response.message);
                $('#editDepartmentModal').modal('hide');
                loadDepartments();
            },
            error: function(xhr) {
                showNotification('error', '部署の更新に失敗しました: ' + xhr.responseJSON.message);
            },
            complete: function() {
                // Re-enable submit button
                submitBtn.prop('disabled', false).html(originalText);
            }
        });
    });
}

function loadDepartments(page = 1) {
    $.get(`/api/settings/departments?page=${page}`, function(data) {
        const tbody = $('#departmentsTable tbody');
        tbody.empty();
        if (data.success && Array.isArray(data.departments)) {
            data.departments.forEach(dept => {
                const branchJP = dept.branch === 'vietnam' ? 'ベトナム' : (dept.branch === 'japan' ? '日本' : dept.branch);
                const row = `
                    <tr>
                        <td>${dept.name}</td>
                        <td>${branchJP}</td>
                        <td>
                            ${isBranchAdmin ? `
                                <button class="btn btn-sm btn-primary" onclick="editDepartment(${dept.id}, '${dept.name}')">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn btn-sm btn-danger" onclick="deleteDepartment(${dept.id}, '${dept.name}', this)">
                                    <i class="fas fa-trash"></i>
                                </button>
                            ` : ''}
                        </td>
                    </tr>
                `;
                tbody.append(row);
            });
        }
        renderPagination('#departmentsPagination', data.page, data.pages, loadDepartments);
    });
}

function editDepartment(id, name) {
    $('#editDepartmentId').val(id);
    $('#editDepartmentName').val(name);
    $('#editDepartmentModal').modal('show');
}

function deleteDepartment(id, name, btn) {
    if (confirm(`部署 "${name}" を削除してもよろしいですか？`)) {
        $.ajax({
            url: `/api/settings/departments/${id}`,
            method: 'DELETE',
            success: function(response) {
                if (response.success) {
                    const row = btn.closest('tr');
                    row.style.transition = 'all 0.5s cubic-bezier(.4,2,.6,1)';
                    row.style.opacity = '0.3';
                    row.style.transform = 'translateX(100px)';
                    setTimeout(() => {
                        row.remove();
                        showNotification('success', response.message || '部署が正常に削除されました');
                    }, 400);
                } else {
                    showNotification('error', response.message || '部署の削除に失敗しました');
                }
            },
            error: function(xhr) {
                showNotification('error', '部署の削除に失敗しました: ' + (xhr.responseJSON && xhr.responseJSON.message ? xhr.responseJSON.message : ''));
            }
        });
    }
}

// Asset Type Management
function initAssetTypeModals() {
    // Store last focused element before opening modal
    $('#addAssetTypeModal, #editAssetTypeModal, #deleteAssetTypeModal').on('show.bs.modal', function() {
        lastFocusedElement = document.activeElement;
    });

    // Restore focus when modal is hidden
    $('#addAssetTypeModal, #editAssetTypeModal, #deleteAssetTypeModal').on('hidden.bs.modal', function() {
        if (lastFocusedElement) {
            lastFocusedElement.focus();
        }
        // Clear form and remove any validation states
        $(this).find('form').trigger('reset');
        $(this).find('.is-invalid').removeClass('is-invalid');
    });

    // Focus first input when modal is shown
    $('#addAssetTypeModal, #editAssetTypeModal').on('shown.bs.modal', function() {
        $(this).find('input[type="text"]:first').focus();
    });

    // Add Asset Type Form
    $('#assetTypeForm').on('submit', function(e) {
        e.preventDefault();
        const formData = $(this).serialize();
        const submitBtn = $(this).find('button[type="submit"]');
        const originalText = submitBtn.html();
        
        // Disable submit button to prevent double submission
        submitBtn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> 処理中...');
        
        $.ajax({
            url: '/api/settings/asset-types',
            method: 'POST',
            data: formData,
            success: function(response) {
                if (response.success) {
                    showNotification('success', response.message);
                    $('#assetTypeForm').trigger('reset');
                    $('#addAssetTypeModal').modal('hide');
                    loadAssetTypes();
                } else {
                    showNotification('error', response.message || '資産タイプの追加に失敗しました');
                }
            },
            error: function(xhr) {
                showNotification('error', '資産タイプの追加に失敗しました: ' + (xhr.responseJSON && xhr.responseJSON.message ? xhr.responseJSON.message : ''));
            },
            complete: function() {
                // Re-enable submit button
                submitBtn.prop('disabled', false).html(originalText);
            }
        });
    });

    // Edit Asset Type Form
    $('#editAssetTypeForm').on('submit', function(e) {
        e.preventDefault();
        const formData = $(this).serialize();
        const id = $('#editAssetTypeId').val();
        const submitBtn = $(this).find('button[type="submit"]');
        const originalText = submitBtn.html();
        
        // Disable submit button to prevent double submission
        submitBtn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> 処理中...');
        
        $.ajax({
            url: `/api/settings/asset-types/${id}`,
            method: 'PUT',
            data: formData,
            success: function(response) {
                showNotification('success', response.message);
                $('#editAssetTypeModal').modal('hide');
                loadAssetTypes();
            },
            error: function(xhr) {
                showNotification('error', '資産タイプの更新に失敗しました: ' + xhr.responseJSON.message);
            },
            complete: function() {
                // Re-enable submit button
                submitBtn.prop('disabled', false).html(originalText);
            }
        });
    });

    // Delete Asset Type Confirmation
    $('#confirmDeleteAssetTypeBtn').on('click', function() {
        const id = $(this).data('id');
        const btn = $(this);
        const originalText = btn.html();
        
        // Disable button to prevent double submission
        btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> 処理中...');
        
        deleteAssetType(id, btn, originalText);
    });

    // Add this after document ready or inside initAssetTypeModals
    $('#deleteAssetTypeModal').on('hidden.bs.modal', function() {
        if (lastFocusedElement) {
            lastFocusedElement.focus();
        } else {
            document.body.focus();
        }
    });
}

function loadAssetTypes(page = 1) {
    $.get(`/api/settings/asset-types?page=${page}`, function(data) {
        const tbody = $('#assetTypesTable tbody');
        tbody.empty();
        if (data.success && Array.isArray(data.asset_types)) {
            data.asset_types.forEach(type => {
                const branchJP = type.branch === 'vietnam' ? 'ベトナム' : (type.branch === 'japan' ? '日本' : type.branch);
                const safeTypeName = type.name.replace(/'/g, "\\'");
                const row = `
                    <tr>
                        <td>${type.name}</td>
                        <td>${branchJP}</td>
                        <td>
                            ${isBranchAdmin ? `
                                <button class="btn btn-sm btn-primary" onclick="editAssetType(${type.id}, '${safeTypeName}')">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn btn-sm btn-danger" onclick="confirmDeleteAssetType(${type.id}, '${safeTypeName}')">
                                    <i class="fas fa-trash"></i>
                                </button>
                            ` : ''}
                        </td>
                    </tr>
                `;
                tbody.append(row);
            });
        }
        renderPagination('#assetTypesPagination', data.page, data.pages, loadAssetTypes);
    });
}

function editAssetType(id, name) {
    $('#editAssetTypeId').val(id);
    $('#editAssetTypeName').val(name);
    $('#editAssetTypeModal').modal('show');
}

function confirmDeleteAssetType(id, name) {
    $('#deleteAssetTypeName').text(name);
    $('#confirmDeleteAssetTypeBtn').data('id', id);
    $('#deleteAssetTypeModal').modal('show');
}

function deleteAssetType(id, btn, originalText) {
    // If called from table button (without modal), show confirmation first
    if (!originalText) {
        confirmDeleteAssetType(id, btn);
        return;
    }
    
    $.ajax({
        url: `/api/settings/asset-types/${id}`,
        method: 'DELETE',
        success: function(response) {
            $('#deleteAssetTypeModal').modal('hide');
            const row = $(`button[onclick*="confirmDeleteAssetType(${id}"]`).closest('tr');
            if (row.length) {
                row.css({
                    transition: 'all 0.5s cubic-bezier(.4,2,.6,1)',
                    opacity: '0.3',
                    transform: 'translateX(100px)'
                });
                setTimeout(() => {
                    row.remove();
                    showNotification('success', response.message || '資産タイプが正常に削除されました');
                }, 400);
            } else {
                showNotification('success', response.message || '資産タイプが正常に削除されました');
            }
        },
        error: function(xhr) {
            showNotification('error', '資産タイプの削除に失敗しました: ' + (xhr.responseJSON && xhr.responseJSON.message ? xhr.responseJSON.message : ''));
        },
        complete: function() {
            // Re-enable button
            if (btn && originalText) {
                btn.prop('disabled', false).html(originalText);
            }
        }
    });
}

// Utility Functions
function showNotification(type, message) {
    // Luôn ưu tiên message từ backend (đã là tiếng Nhật)
    let msg = message;
    if (!msg) msg = 'エラーが発生しました。';
    if (window.notifications) {
        window.notifications.show(msg, type);
    } else {
        alert(msg);
    }
}

// Initialize when document is ready
$(document).ready(function() {
    initSettings();
});

// Ensure accessibility: when any modal closes, focus is returned to the last focused element or to body
$('#addDepartmentModal, #editDepartmentModal, #addAssetTypeModal, #editAssetTypeModal, #deleteAssetTypeModal').on('hidden.bs.modal', function() {
    // Nếu phần tử đang focus nằm trong modal này, chuyển focus ra ngoài
    if ($(this).find(':focus').length > 0 || $.contains(this, document.activeElement)) {
        if (lastFocusedElement && document.contains(lastFocusedElement)) {
            lastFocusedElement.focus();
        } else {
            document.body.focus();
        }
    }
});

function renderPagination(containerSelector, currentPage, totalPages, onPageChange) {
    const container = $(containerSelector);
    container.empty();
    if (totalPages <= 1) return;
    let html = '';
    html += `<nav><ul class="pagination pagination-sm mb-0 custom-pagination">`;
    html += `<li class="page-item${currentPage === 1 ? ' disabled' : ''}"><a class="page-link" href="#" data-page="${currentPage - 1}">«</a></li>`;
    for (let i = 1; i <= totalPages; i++) {
        html += `<li class="page-item${i === currentPage ? ' active' : ''}"><a class="page-link" href="#" data-page="${i}">${i}</a></li>`;
    }
    html += `<li class="page-item${currentPage === totalPages ? ' disabled' : ''}"><a class="page-link" href="#" data-page="${currentPage + 1}">»</a></li>`;
    html += `</ul></nav>`;
    container.html(html);
    container.find('a.page-link').click(function(e) {
        e.preventDefault();
        const page = parseInt($(this).data('page'));
        if (!isNaN(page) && page >= 1 && page <= totalPages && page !== currentPage) {
            onPageChange(page);
        }
    });
} 