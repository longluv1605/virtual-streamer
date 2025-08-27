// API Base URL
const API_BASE = "/api";

// WebSocket connection
let ws = null;

// Global data
let products = [];
let sessions = [];
let templates = [];
let availableAvatars = [];

// Initialize app
document.addEventListener("DOMContentLoaded", function () {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    loadDashboard();
});


// Dashboard functions
async function loadDashboard() {
    try {
        // Load summary data
        const [productsRes, sessionsRes, templatesRes] = await Promise.all([
            fetch(`${API_BASE}/products`),
            fetch(`${API_BASE}/sessions`),
            fetch(`${API_BASE}/templates`),
        ]);

        const productsData = await productsRes.json();
        const sessions = await sessionsRes.json();
        const templates = await templatesRes.json();

        console.log("Products response:", productsData);
        console.log("Sessions response:", sessions);

        // Extract products array from paginated response
        const products = Array.isArray(productsData.items)
            ? productsData.items
            : Array.isArray(productsData)
            ? productsData
            : [];

        console.log("Extracted products array:", products);
        console.log("Is products an array?", Array.isArray(products));

        // Update counters
        document.getElementById("total-products").textContent =
            productsData.total || products.length;
        document.getElementById("total-sessions").textContent = sessions.length;
        document.getElementById("live-sessions").textContent = sessions.filter(
            (s) => s.status === "live"
        ).length;
        document.getElementById("total-templates").textContent =
            templates.length;

        // Show recent sessions
        sessions.reverse();
        const recentSessions = sessions.slice(0, 5);
        const recentSessionsHtml = recentSessions
            .map(
                (session) => `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div>
                    <strong>${session.title}</strong><br>
                    <small class="text-muted">${formatDate(
                        session.created_at
                    )}</small>
                </div>
                <span class="badge ${getStatusBadgeClass(
                    session.status
                )}">${getStatusText(session.status)}</span>
            </div>
        `
            )
            .join("");
        document.getElementById("recent-sessions").innerHTML =
            recentSessionsHtml ||
            '<p class="text-muted">Chưa có phiên live nào</p>';

        // Show featured products
        const featuredProducts = products.slice(0, 5);
        const featuredProductsHtml = featuredProducts
            .map(
                (product) => `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div>
                    <strong>${product.name}</strong><br>
                    <small class="text-muted">${formatPrice(
                        product.price
                    )} VNĐ</small>
                </div>
                <span class="badge bg-success">${
                    product.stock_quantity
                } trong kho</span>
            </div>
        `
            )
            .join("");
        document.getElementById("featured-products").innerHTML =
            featuredProductsHtml ||
            '<p class="text-muted">Chưa có sản phẩm nào</p>';
    } catch (error) {
        console.error("Error loading dashboard:", error);
        showNotification("error", "Lỗi tải dashboard");
    }
}

// Utility functions
function formatPrice(price) {
    return new Intl.NumberFormat("vi-VN").format(price);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleString("vi-VN");
}

function showNotification(type, message) {
    // Create notification element
    const notification = document.createElement("div");
    notification.className = `alert alert-${
        type === "error" ? "danger" : type
    } alert-dismissible fade show position-fixed`;
    notification.style.cssText =
        "top: 20px; right: 20px; z-index: 9999; min-width: 300px;";
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

function getStatusBadgeClass(status) {
    const classes = {
        preparing: "bg-secondary",
        processing: "bg-warning",
        ready: "bg-info",
        live: "bg-success",
        completed: "bg-primary",
        error: "bg-danger",
    };
    return classes[status] || "bg-secondary";
}

function getStatusText(status) {
    const texts = {
        preparing: "Chuẩn bị",
        processing: "Đang xử lý",
        ready: "Sẵn sàng",
        live: "Đang live",
        completed: "Hoàn thành",
        error: "Lỗi",
    };
    return texts[status] || status;
}