const API_URL = "http://127.0.0.1:5000";

// 🔹 On Load: Basic Token Check + Init
document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "/frontend/index.html";
        return;
    }

    // Fetch items and requests on page load
    fetchItems();
    displayEmployeeRequests(); 
    loadOrderHistory(); // Ensure employee requests are displayed after page load
});

// 🔹 Fetch & Display Items
async function fetchItems() {
    currentSearch = '';
    currentPage = 1;
    await fetchAndDisplayItems();
}

// 🔹 Select Item & Show Modal
function selectItem(id, name) {
    document.getElementById("selectedItemId").value = id;
    document.getElementById("selectedItemName").value = name;
    document.getElementById("requestModal").style.display = "flex";
}

function closeModal() {
    document.getElementById("requestModal").style.display = "none";
}

// 🔹 Live Search
async function searchItem() {
    currentSearch = document.getElementById("searchItem").value;
    currentPage = 1; // Reset to first page on new search
    await fetchAndDisplayItems();
}

// 🔹 Submit Request
async function submitRequest(event) {
    event.preventDefault();

    const token = localStorage.getItem("token");
    const itemId = parseInt(document.getElementById("selectedItemId").value);
    const quantity = parseInt(document.getElementById("quantity").value);
    const reason = document.getElementById("reason").value;

    if (!itemId) {
        alert("Please select an item.");
        return;
    }

    const requestData = { item_id: itemId, quantity, reason };

    try {
        const response = await fetch(`${API_URL}/requests`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(requestData)
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.message || "Low Stock.....");

        alert("✅ Request submitted successfully!");
        document.getElementById("requestForm").reset();
        closeModal();

        // Refresh the employee requests
        displayEmployeeRequests();

    } catch (error) {
        console.error("❌ Error submitting request:", error);
        alert(error.message);
    }
}

// 🔹 Display Employee Requests
async function displayEmployeeRequests() {
    const token = localStorage.getItem("token");
    const requestContainer = document.getElementById("my-requests");

    try {
        const response = await fetch(`${API_URL}/requests`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!response.ok) throw new Error("Error fetching requests.");

        const requests = await response.json();
        requestContainer.innerHTML = requests.length
            ? requests.map(req => `
                <tr>
                    <td>${req.item_name || "Unknown"}</td>
                    <td>${req.quantity}</td>
                    <td class="${req.status.toLowerCase()}">${req.status}</td>
                    <td>${req.admin_response || "Pending"}</td>
                </tr>
            `).join("")
            : "<tr><td colspan='4'>No requests found</td></tr>";

    } catch (error) {
        console.error("❌ Error Fetching Employee Requests:", error);
        requestContainer.innerHTML = "<tr><td colspan='4'>Error loading employee requests.</td></tr>";
    }
}

// 🔹 Logout
function logout() {
    // Clear all client-side data
    localStorage.removeItem("token");
    localStorage.removeItem("role");

    // Clear the UI
    document.getElementById("itemsContainer").innerHTML = "";
    document.getElementById("my-requests").innerHTML = "";
    const orderHistory = document.getElementById("orderHistoryTable");
    if (orderHistory) orderHistory.querySelector("tbody").innerHTML = "";

    // Redirect to login
    window.location.href = "/frontend/index.html";
}

// 🔹 Form Submit Handler
document.getElementById("requestForm").addEventListener("submit", submitRequest);

// 🔹 Pagination for Items
async function fetchAndDisplayItems() {
    const container = document.getElementById("itemsContainer");
    const token = localStorage.getItem("token");

    try {
        container.innerHTML = "<p>Loading items...</p>";

        const response = await fetch(
            `${API_URL}/items?search=${encodeURIComponent(currentSearch)}&page=${currentPage}`,
            { headers: { "Authorization": `Bearer ${token}` } }
        );

        if (!response.ok) throw new Error("Failed to load items");

        const data = await response.json();

        // Clear previous results
        container.innerHTML = "";

        if (data.items.length === 0) {
            container.innerHTML = "<p class='no-results'>No items found</p>";
            return;
        }

        // Display items
        data.items.forEach(item => {
            const itemCard = document.createElement("div");
            itemCard.classList.add("item-card");
            itemCard.innerHTML = `
                <h3>${item.name}</h3>
                <p>Stock: ${item.stock}</p>
                <button onclick="selectItem(${item.id}, '${item.name.replace("'", "\\'")}', ${item.stock})">
                    Request
                </button>
            `;
            container.appendChild(itemCard);
        });

        // Add pagination (now properly contained)
        if (data.total_pages > 1) {
            const paginationContainer = document.createElement("div");
            paginationContainer.className = "pagination-container";

            const paginationControls = document.createElement("div");
            paginationControls.className = "pagination-controls";
            paginationControls.innerHTML = `
                <button ${currentPage <= 1 ? 'disabled' : ''} 
                    onclick="changePage(${currentPage - 1})">
                    ← Previous
                </button>
                <span>Page ${currentPage} of ${data.total_pages}</span>
                <button ${currentPage >= data.total_pages ? 'disabled' : ''} 
                    onclick="changePage(${currentPage + 1})">
                    Next →
                </button>
            `;

            paginationContainer.appendChild(paginationControls);
            container.appendChild(paginationContainer);
        }

    } catch (error) {
        container.innerHTML = `<p class="error">Error: ${error.message}</p>`;
    }
}

// 🔹 Page Change Handler
function changePage(newPage) {
    currentPage = newPage;
    fetchAndDisplayItems();
}

// 🔹 Display Order History (Employee Orders)
async function showOrderHistory() {
    try {
        const response = await fetch(`${API_URL}/employee/orders`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const orders = await response.json();

        const historySection = document.createElement('div');
        historySection.className = 'order-history';
        historySection.innerHTML = `
            <h3>My Order History</h3>
            <button onclick="exportMyOrders()" class="export-btn">
                📊 Export to CSV
            </button>
            <table>
                <thead>
                    <tr>
                        <th>Item</th>
                        <th>Quantity</th>
                        <th>Status</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
                    ${orders.map(order => `
                        <tr>
                            <td>${order.item_name}</td>
                            <td>${order.quantity}</td>
                            <td class="${order.status}">${order.status}</td>
                            <td>${order.date}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;

        document.getElementById('orderHistoryContainer').appendChild(historySection);
    } catch (error) {
        console.error('Error loading order history:', error);
    }
}
// Display order history
async function loadOrderHistory() {
    const token = localStorage.getItem('token');
    const tbody = document.querySelector("#orderHistoryTable tbody");

    // Clear previous content and show loading state
    tbody.innerHTML = '<tr><td colspan="4" class="loading">Loading history...</td></tr>';

    // Check authentication first
    if (!token) {
        tbody.innerHTML = '<tr><td colspan="4" class="error">Please login to view order history</td></tr>';
        return;
    }

    try {
        const response = await fetch(`${API_URL}/employee/orders`, {
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        // Check for HTTP errors
        if (!response.ok) {
            const error = await response.json().catch(() => null);
            throw new Error(error?.message || `HTTP error! status: ${response.status}`);
        }

        const orders = await response.json();

        // Update the UI
        if (orders.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="no-orders">No order history found</td></tr>';
        } else {
            tbody.innerHTML = orders.map(order => `
                <tr>
                    <td>${escapeHtml(order.item_name)}</td>
                    <td>${order.quantity}</td>
                    <td class="status-${order.status.toLowerCase()}">${order.status}</td>
                    <td>${order.date}</td>
                </tr>
            `).join('');
        }

    } catch (error) {
        console.error('Error loading order history:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="error">
                    Failed to load history: ${escapeHtml(error.message)}
                </td>
            </tr>
        `;
        
        // Auto-redirect if unauthorized
        if (error.message.includes('401')) {
            setTimeout(() => {
                window.location.href = '/frontend/index.html';
            }, 2000);
        }
    }
}


// 🔹 Export Order History to CSV
async function exportMyOrders() {
    try {
        const response = await fetch(`${API_URL}/employee/orders/export`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });

        if (!response.ok) throw new Error('Export failed');

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'my_orders.csv';
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);

    } catch (error) {
        alert('Export failed: ' + error.message);
        console.error('Export error:', error);
    }
}

// 🔹 Helper Function to Escape HTML (Prevent XSS)
function escapeHtml(unsafe) {
    return unsafe?.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;") || '';
}
