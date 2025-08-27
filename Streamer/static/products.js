// Products management JavaScript
let currentPage = 1;
let currentLimit = 12;
let editingProductId = null;

// Initialize page
document.addEventListener("DOMContentLoaded", function () {
    loadCategories();
    loadProducts();

    // Set up event listeners
    document
        .getElementById("searchInput")
        .addEventListener("input", debounce(loadProducts, 500));
    document
        .getElementById("categoryFilter")
        .addEventListener("change", loadProducts);
    document
        .getElementById("minPrice")
        .addEventListener("input", debounce(loadProducts, 500));
    document
        .getElementById("maxPrice")
        .addEventListener("input", debounce(loadProducts, 500));
    document
        .getElementById("showInactive")
        .addEventListener("change", loadProducts);
});

// Debounce function for search inputs
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

// Load products with filters
async function loadProducts() {
    const searchInput = document.getElementById("searchInput").value;
    const categoryFilter = document.getElementById("categoryFilter").value;
    const minPrice = document.getElementById("minPrice").value;
    const maxPrice = document.getElementById("maxPrice").value;
    const showInactive = document.getElementById("showInactive").checked;

    const params = new URLSearchParams({
        page: currentPage,
        limit: currentLimit,
    });

    if (searchInput) params.append("search", searchInput);
    if (categoryFilter) params.append("category", categoryFilter);
    if (minPrice) params.append("min_price", minPrice);
    if (maxPrice) params.append("max_price", maxPrice);
    if (showInactive) params.append("include_inactive", "true");

    try {
        console.log("Loading products with params:", params.toString());
        const response = await fetch(`/api/products?${params}`);
        const data = await response.json();

        console.log("API response status:", response.status);
        console.log("API response data:", data);

        if (response.ok) {
            // Check if data has the expected structure
            if (data && data.items && Array.isArray(data.items)) {
                displayProducts(data.items);
                displayPagination(
                    data.total || 0,
                    data.page || 1,
                    data.pages || 1
                );
                console.log(
                    `Loaded ${data.items.length} products successfully`
                );
            } else {
                console.warn("Unexpected API response format:", data);
                displayProducts([]);
                displayPagination(0, 1, 1);
                showAlert("Phản hồi API không đúng định dạng", "warning");
            }
        } else {
            console.error("API error:", data);
            showAlert(
                "Lỗi khi tải sản phẩm: " + (data.detail || "Unknown error"),
                "danger"
            );
        }
    } catch (error) {
        console.error("Network error loading products:", error);
        showAlert("Lỗi kết nối khi tải sản phẩm: " + error.message, "danger");
    }
}

// Display products in grid
function displayProducts(products) {
    const container = document.getElementById("productsContainer");

    try {
        console.log("Displaying products:", products);

        // Check if products is valid
        if (!products || !Array.isArray(products)) {
            console.warn("Invalid products data:", products);
            products = [];
        }

        if (products.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="fas fa-box-open fa-3x text-muted mb-3"></i>
                    <h4 class="text-muted">Không tìm thấy sản phẩm nào</h4>
                </div>
            `;
            return;
        }

        container.innerHTML = products
            .map((product) => {
                try {
                    // Add safety checks for product properties
                    const productId = product?.id || 0;
                    const productName = product?.name || "Tên không xác định";
                    const productDescription =
                        product?.description || "Không có mô tả";
                    const productPrice = product?.price || 0;
                    const productStock = product?.stock_quantity || 0;
                    const productCategory = product?.category || "";
                    const productImageUrl = product?.image_url || "";
                    const isActive = product?.is_active !== false; // Default to true if undefined

                    return `
                <div class="col-md-4 mb-4">
                    <div class="card product-card h-100 ${
                        productStock < 10 ? "low-stock" : ""
                    }">
                        ${
                            productImageUrl
                                ? `
                            <img src="${productImageUrl}" class="card-img-top" alt="${productName}" style="height: 200px; object-fit: contain;">
                        `
                                : `
                            <div class="card-img-top bg-light d-flex align-items-center justify-content-center" style="height: 200px;">
                                <i class="fas fa-image fa-3x text-muted"></i>
                            </div>
                        `
                        }
                        <div class="card-body d-flex flex-column">
                            <h5 class="card-title">${productName}</h5>
                            <p class="card-text text-muted small">${productDescription}</p>
                            <div class="mt-auto">
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <span class="h5 text-primary mb-0">${formatPrice(
                                        productPrice
                                    )}₫</span>
                                    <span class="badge ${
                                        productStock < 10
                                            ? "bg-warning"
                                            : "bg-success"
                                    }">
                                        ${productStock} còn lại
                                    </span>
                                </div>
                                ${
                                    productCategory
                                        ? `
                                    <span class="badge bg-secondary mb-2">${productCategory}</span>
                                `
                                        : ""
                                }
                                <div class="d-flex gap-2">
                                    <button class="btn btn-sm btn-outline-primary flex-fill" onclick="editProduct(${productId})">
                                        <i class="fas fa-edit"></i> Sửa
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteProduct(${productId})">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                    ${
                                        !isActive
                                            ? `
                                        <button class="btn btn-sm btn-success" onclick="restoreProduct(${productId})">
                                            <i class="fas fa-undo"></i>
                                        </button>
                                    `
                                            : ""
                                    }
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
                } catch (error) {
                    console.error("Error rendering product:", product, error);
                    return `
                        <div class="col-md-4 mb-4">
                            <div class="card product-card h-100 border-danger">
                                <div class="card-body d-flex flex-column align-items-center justify-content-center text-danger">
                                    <i class="fas fa-exclamation-triangle fa-2x mb-2"></i>
                                    <p>Lỗi hiển thị sản phẩm</p>
                                </div>
                            </div>
                        </div>
                    `;
                }
            })
            .join("");
    } catch (error) {
        console.error("Error displaying products:", error);
        container.innerHTML = `
            <div class="col-12 text-center py-5 text-danger">
                <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                <h4>Lỗi hiển thị danh sách sản phẩm</h4>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// Display pagination
function displayPagination(total, page, totalPages) {
    const pagination = document.getElementById("pagination");

    try {
        console.log("Displaying pagination:", { total, page, totalPages });

        // Add safety checks for pagination parameters
        const safeTotal = total || 0;
        const safePage = page || 1;
        const safeTotalPages = totalPages || 1;

        if (safeTotalPages <= 1) {
            pagination.innerHTML = "";
            return;
        }

        let html = "";

        // Previous button
        html += `
            <li class="page-item ${safePage === 1 ? "disabled" : ""}">
                <a class="page-link" href="#" onclick="goToPage(${
                    safePage - 1
                })">Trước</a>
            </li>
        `;

        // Page numbers
        const startPage = Math.max(1, safePage - 2);
        const endPage = Math.min(safeTotalPages, safePage + 2);

        for (let i = startPage; i <= endPage; i++) {
            html += `
                <li class="page-item ${i === safePage ? "active" : ""}">
                    <a class="page-link" href="#" onclick="goToPage(${i})">${i}</a>
                </li>
            `;
        }

        // Next button
        html += `
            <li class="page-item ${
                safePage === safeTotalPages ? "disabled" : ""
            }">
                <a class="page-link" href="#" onclick="goToPage(${
                    safePage + 1
                })">Sau</a>
            </li>
        `;

        pagination.innerHTML = html;
    } catch (error) {
        console.error("Error displaying pagination:", error);
        pagination.innerHTML = `
            <li class="page-item disabled">
                <span class="page-link text-danger">Lỗi phân trang</span>
            </li>
        `;
    }
}

// Go to specific page
function goToPage(page) {
    currentPage = page;
    loadProducts();
}

// Load categories for filter
async function loadCategories() {
    try {
        const response = await fetch("/api/products/categories");
        const categories = await response.json();

        const select = document.getElementById("categoryFilter");
        select.innerHTML =
            '<option value="">Tất cả danh mục</option>' +
            categories
                .map((cat) => `<option value="${cat}">${cat}</option>`)
                .join("");
    } catch (error) {
        console.error("Error loading categories:", error);
    }
}

// Show create product modal
function showCreateModal() {
    editingProductId = null;
    document.getElementById("modalTitle").textContent = "Thêm sản phẩm mới";
    document.getElementById("productForm").reset();
    document.getElementById("productId").value = "";

    const modal = new bootstrap.Modal(document.getElementById("productModal"));
    modal.show();
}

// Edit product
async function editProduct(id) {
    try {
        console.log("Loading product for edit, ID:", id);

        if (!id || isNaN(id)) {
            showAlert("ID sản phẩm không hợp lệ", "danger");
            return;
        }

        const response = await fetch(`/api/products/${id}`);
        const product = await response.json();

        console.log("Edit product API response status:", response.status);
        console.log("Edit product API response data:", product);

        if (response.ok) {
            // Check if product data is valid
            if (!product || typeof product !== "object") {
                showAlert("Dữ liệu sản phẩm không hợp lệ", "danger");
                return;
            }

            editingProductId = id;
            document.getElementById("modalTitle").textContent = "Sửa sản phẩm";

            // Fill form with product data, using fallback values for safety
            document.getElementById("productId").value = product.id || "";
            document.getElementById("productName").value = product.name || "";
            document.getElementById("productDescription").value =
                product.description || "";
            document.getElementById("productPrice").value = product.price || 0;
            document.getElementById("productStock").value =
                product.stock_quantity || 0;
            document.getElementById("productCategory").value =
                product.category || "";
            document.getElementById("productImage").value =
                product.image_url || "";

            console.log("Form populated with product data");

            const modal = new bootstrap.Modal(
                document.getElementById("productModal")
            );
            modal.show();
        } else {
            console.error("Edit product API error:", product);
            const errorMessage =
                product.detail || product.message || "Lỗi không xác định";
            showAlert(
                "Lỗi khi tải thông tin sản phẩm: " + errorMessage,
                "danger"
            );
        }
    } catch (error) {
        console.error("Network error loading product for edit:", error);
        showAlert("Lỗi kết nối khi tải sản phẩm: " + error.message, "danger");
    }
}

// Save product (create or update)
async function saveProduct() {
    try {
        console.log("Starting to save product...");

        const name = document.getElementById("productName").value;
        const description = document.getElementById("productDescription").value;
        const price = parseFloat(document.getElementById("productPrice").value);
        const stock = parseInt(document.getElementById("productStock").value);
        const category = document.getElementById("productCategory").value;
        const imageUrl = document.getElementById("productImage").value;

        console.log("Form data collected:", {
            name,
            description,
            price,
            stock,
            category,
            imageUrl,
        });

        // Enhanced validation
        if (!name || name.trim() === "") {
            showAlert("Tên sản phẩm không được để trống", "warning");
            return;
        }

        if (isNaN(price) || price <= 0) {
            showAlert("Giá sản phẩm phải là số dương", "warning");
            return;
        }

        if (isNaN(stock) || stock < 0) {
            showAlert("Số lượng tồn kho phải là số không âm", "warning");
            return;
        }

        const productData = {
            name: name.trim(),
            description:
                description && description.trim() !== ""
                    ? description.trim()
                    : null,
            price: price,
            stock_quantity: stock,
            category:
                category && category.trim() !== "" ? category.trim() : null,
            image_url:
                imageUrl && imageUrl.trim() !== "" ? imageUrl.trim() : null,
        };

        console.log("Product data to send:", productData);

        let response;
        let url;
        let method;

        if (editingProductId) {
            // Update existing product
            url = `/api/products/${editingProductId}`;
            method = "PUT";
            console.log("Updating product with ID:", editingProductId);
        } else {
            // Create new product
            url = "/api/products";
            method = "POST";
            console.log("Creating new product");
        }

        response = await fetch(url, {
            method: method,
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(productData),
        });

        console.log("API response status:", response.status);
        const result = await response.json();
        console.log("API response data:", result);

        if (response.ok) {
            const successMessage = editingProductId
                ? "Sản phẩm đã được cập nhật thành công"
                : "Sản phẩm đã được thêm thành công";
            showAlert(successMessage, "success");

            // Close modal
            const modal = bootstrap.Modal.getInstance(
                document.getElementById("productModal")
            );
            if (modal) {
                modal.hide();
            }

            // Refresh data
            await loadProducts();
            await loadCategories(); // Refresh categories in case new category was added
        } else {
            console.error("API error:", result);
            const errorMessage =
                result.detail ||
                result.message ||
                "Lỗi không xác định khi lưu sản phẩm";
            showAlert("Lỗi: " + errorMessage, "danger");
        }
    } catch (error) {
        console.error("Network error saving product:", error);
        showAlert("Lỗi kết nối khi lưu sản phẩm: " + error.message, "danger");
    }
}

// Delete product
async function deleteProduct(id) {
    try {
        console.log("Attempting to delete product with ID:", id);

        if (!id || isNaN(id)) {
            showAlert("ID sản phẩm không hợp lệ", "danger");
            return;
        }

        if (!confirm("Bạn có chắc chắn muốn xóa sản phẩm này?")) {
            console.log("Delete cancelled by user");
            return;
        }

        const response = await fetch(`/api/products/${id}`, {
            method: "DELETE",
        });

        console.log("Delete response status:", response.status);

        if (response.ok) {
            showAlert("Sản phẩm đã được xóa thành công", "success");
            await loadProducts(); // Refresh product list
        } else {
            const error = await response.json();
            console.error("Delete API error:", error);
            const errorMessage =
                error.detail || error.message || "Lỗi không xác định";
            showAlert("Lỗi khi xóa sản phẩm: " + errorMessage, "danger");
        }
    } catch (error) {
        console.error("Network error deleting product:", error);
        showAlert("Lỗi kết nối khi xóa sản phẩm: " + error.message, "danger");
    }
}

// Restore product
async function restoreProduct(id) {
    try {
        console.log("Attempting to restore product with ID:", id);

        if (!id || isNaN(id)) {
            showAlert("ID sản phẩm không hợp lệ", "danger");
            return;
        }

        const response = await fetch(`/api/products/${id}/restore`, {
            method: "PUT",
        });

        console.log("Restore response status:", response.status);

        if (response.ok) {
            showAlert("Sản phẩm đã được khôi phục thành công", "success");
            await loadProducts(); // Refresh product list
        } else {
            const error = await response.json();
            console.error("Restore API error:", error);
            const errorMessage =
                error.detail || error.message || "Lỗi không xác định";
            showAlert("Lỗi khi khôi phục sản phẩm: " + errorMessage, "danger");
        }
    } catch (error) {
        console.error("Network error restoring product:", error);
        showAlert(
            "Lỗi kết nối khi khôi phục sản phẩm: " + error.message,
            "danger"
        );
    }
}

// Load and display statistics
async function loadStats() {
    try {
        console.log("Loading stats from API...");
        const response = await fetch("/api/products/stats/summary");
        const stats = await response.json();

        console.log("API response status:", response.status);
        console.log("API response data:", stats);
        // console.log(response)

        if (response.ok) {
            displayStats(stats);
            const modal = new bootstrap.Modal(
                document.getElementById("statsModal")
            );
            modal.show();
        } else {
            console.error("API error:", stats);
            showAlert(
                "Lỗi khi tải thống kê: " + (stats.detail || "Unknown error"),
                "danger"
            );
        }
    } catch (error) {
        console.error("Network error loading stats:", error);
        showAlert("Lỗi kết nối khi tải thống kê: " + error.message, "danger");
    }
}

// Display statistics
function displayStats(stats) {
    try {
        console.log("Displaying stats:", stats);

        const content = document.getElementById("statsContent");

        // Add safety checks for all stats properties
        const safeStats = {
            total_products: stats.total_products || 0,
            active_products: stats.active_products || 0,
            low_stock_products: stats.low_stock_products || 0,
            total_value: stats.total_value || 0,
            top_products_by_value: stats.top_products_by_value || [],
            products_by_category: stats.products_by_category || [],
        };

        console.log("Safe stats:", safeStats);

        content.innerHTML = `
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card stats-card text-center">
                        <div class="card-body">
                            <i class="fas fa-box fa-2x mb-2"></i>
                            <h3>${safeStats.total_products}</h3>
                            <p class="mb-0">Tổng sản phẩm</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-success text-white text-center">
                        <div class="card-body">
                            <i class="fas fa-check-circle fa-2x mb-2"></i>
                            <h3>${safeStats.active_products}</h3>
                            <p class="mb-0">Đang bán</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-warning text-white text-center">
                        <div class="card-body">
                            <i class="fas fa-exclamation-triangle fa-2x mb-2"></i>
                            <h3>${safeStats.low_stock_products}</h3>
                            <p class="mb-0">Sắp hết hàng</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-info text-white text-center">
                        <div class="card-body">
                            <i class="fas fa-dollar-sign fa-2x mb-2"></i>
                            <h3>${formatPrice(safeStats.total_value)}₫</h3>
                            <p class="mb-0">Tổng giá trị</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0">Top sản phẩm theo giá trị</h5>
                        </div>
                        <div class="card-body">
                            ${
                                safeStats.top_products_by_value.length > 0
                                    ? safeStats.top_products_by_value
                                          .map(
                                              (product) => `
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <span>${
                                            product.name || "Không có tên"
                                        }</span>
                                        <span class="badge bg-primary">${formatPrice(
                                            product.total_value || 0
                                        )}₫</span>
                                    </div>
                                `
                                          )
                                          .join("")
                                    : '<p class="text-muted">Không có dữ liệu</p>'
                            }
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0">Danh mục sản phẩm</h5>
                        </div>
                        <div class="card-body">
                            ${
                                safeStats.products_by_category.length > 0
                                    ? safeStats.products_by_category
                                          .map(
                                              (cat) => `
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <span>${
                                            cat.category || "Không phân loại"
                                        }</span>
                                        <span class="badge bg-secondary">${
                                            cat.count || 0
                                        } sản phẩm</span>
                                    </div>
                                `
                                          )
                                          .join("")
                                    : '<p class="text-muted">Không có dữ liệu</p>'
                            }
                        </div>
                    </div>
                </div>
            </div>
        `;
    } catch (error) {
        console.error("Error displaying stats:", error);
        showAlert("Lỗi hiển thị thống kê: " + error.message, "danger");
    }
}

// Utility functions
function formatPrice(price) {
    return new Intl.NumberFormat("vi-VN").format(price);
}

function showAlert(message, type = "info") {
    const alertDiv = document.createElement("div");
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText =
        "top: 20px; right: 20px; z-index: 9999; min-width: 300px;";
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alertDiv);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}
