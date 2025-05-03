const API_URL = "http://127.0.0.1:5000";

// 🔹 Load Requests, Orders, and Items on Page Load
document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    if (!token) {
        alert("Please log in as an administrator.");
        window.location.href = "/frontend/index.html";
        return;
    }
    displayRequests();
    loadAllOrders();
    fetchAndDisplayItems(); // New: Show inventory
});

// 🔹 Upload Inventory File (Excel)
async function uploadInventory() {
    const fileInput = document.getElementById("inventoryFile");
    const status = document.getElementById("uploadStatus");
    if (!fileInput.files.length) {
        status.textContent = "Please select a file.";
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    const token = localStorage.getItem("token");

    try {
        status.textContent = "Uploading...";
        const response = await fetch(`${API_URL}/upload-inventory`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}` },
            body: formData
        });

        const result = await response.json();
        if (response.ok) {
            status.textContent = "✅ Inventory uploaded successfully!";
            fetchAndDisplayItems(); // Refresh inventory
        } else {
            status.textContent = `❌ Error: ${result.message || "Failed to upload."}`;
        }
    } catch (error) {
        console.error("❌ Upload Error:", error);
        status.textContent = "Failed to upload. Check console.";
    }
}

// 🔹 Fetch and Display Items (New)
async function fetchAndDisplayItems() {
    const container = document.getElementById("itemsContainer");
    if (!container) return; // Skip if not in HTML yet

    const token = localStorage.getItem("token");
    try {
        container.innerHTML = "<p>Loading items...</p>";
        const response = await fetch(`${API_URL}/items?page=1`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!response.ok) throw new Error("Failed to load items");
        const data = await response.json();

        container.innerHTML = data.items.length
            ? data.items.map(item => `
                <div class="item-card">
                    <h3>${item.name}</h3>
                    <p class="${item.stock <= 10 ? 'low-stock' : ''}">
                        Stock: ${item.stock} ${item.stock <= 10 ? '(Low)' : ''}
                    </p>
                    ${item.stock <= 10 ? `
                        <button onclick="placeSupplierOrder(${item.id}, '${item.name.replace(/'/g, "\\'")}')">
                            Request from Supplier
                        </button>
                    ` : ''}
                </div>
            `).join("")
            : "<p>No items found</p>";
    } catch (error) {
        console.error("❌ Error fetching items:", error);
        container.innerHTML = `<p class="error">Error: ${error.message}</p>`;
    }
}

// 🔹 Place Supplier Order (New)
// Fetch suppliers
async function fetchSuppliers() {
    const token = localStorage.getItem("token");
    try {
        const response = await fetch(`${API_URL}/users?role=supplier`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!response.ok) {
            let message = "Failed to load suppliers";
            try {
                const errorData = await response.json();
                message = errorData.message || message;
            } catch {
                // Non-JSON response (e.g., HTML)
                message = `Server error: ${response.status} ${response.statusText}`;
            }
            throw new Error(message);
        }
        const suppliers = await response.json();
        return suppliers;
    } catch (error) {
        console.error("❌ Error fetching suppliers:", error);
        alert(`Error loading suppliers: ${error.message}`);
        return [];
    }
}

// Place Supplier Order
async function placeSupplierOrder(itemId, itemName) {
    const token = localStorage.getItem("token");
    const quantity = prompt(`Enter quantity to order for ${itemName}:`, "10");
    if (!quantity || isNaN(quantity) || quantity <= 0) {
        alert("Please enter a valid quantity.");
        return;
    }

    const suppliers = await fetchSuppliers();
    if (!suppliers.length) {
        alert("No suppliers available. Please contact an administrator to add suppliers.");
        return;
    }

    const supplier = suppliers[0];  // Use first supplier (add dropdown later)

    try {
        const response = await fetch(`${API_URL}/supplier-orders`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                item_id: itemId,
                quantity: parseInt(quantity),
                supplier_id: supplier.id
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || "Failed to place order");
        }

        alert("✅ Supplier order placed!");
        fetchAndDisplayItems();
    } catch (error) {
        console.error("❌ Error placing order:", error);
        alert(`Error: ${error.message}`);
    }
}
// 🔹 Display All Requests for Admin (Updated with Stock)
async function displayRequests() {
    const token = localStorage.getItem("token");
    const tbody = document.getElementById("admin-requests");

    try {
        const response = await fetch(`${API_URL}/admin/requests`, {
            headers: { 
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            }
        });

        if (response.status === 403) {
            alert("Access denied. Please log in as an administrator.");
            window.location.href = "/frontend/index.html";
            return;
        }

        const requests = await response.json();
        tbody.innerHTML = requests.length
            ? requests.map(req => `
                <tr>
                    <td>${req.employee_name}</td>
                    <td>${req.item_name}</td>
                    <td>${req.quantity}</td>
                    <td>${req.stock ?? 'N/A'}</td> <!-- Stock column -->
                    <td class="${req.status.toLowerCase()}">${req.status}</td>
                    <td>
                        ${req.status === "pending" ? `
                            <button onclick="updateRequest('${req.id}', 'approved')" 
                                    class="bg-green-500 hover:bg-green-700 text-white font-bold py-1 px-3 rounded mr-2">
                                Approve
                            </button>
                            <button onclick="updateRequest('${req.id}', 'rejected')"
                                    class="bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-3 rounded">
                                Reject
                            </button>
                        ` : req.status}
                    </td>
                </tr>
            `).join("")
            : "<tr><td colspan='6'>No requests found</td></tr>";

    } catch (error) {
        console.error("❌ Error fetching requests:", error);
        tbody.innerHTML = "<tr><td colspan='6'>Error loading requests</td></tr>";
    }
}

// 🔹 Update Request Status
async function updateRequest(requestId, status) {
    const token = localStorage.getItem("token");

    try {
        const response = await fetch(`${API_URL}/requests/${requestId}`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ status })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || "Failed to update request");
        }

        alert("Request updated.");
        await displayRequests();
    } catch (error) {
        console.error("❌ Error updating request:", error);
        alert("Failed to update request: " + error.message);
    }
}

// 🔹 Load All Orders
async function loadAllOrders() {
    const token = localStorage.getItem("token");
    const tbody = document.querySelector("#allOrdersTable tbody");

    try {
        const response = await fetch(`${API_URL}/admin/orders`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!response.ok) throw new Error("Failed to fetch orders");

        const orders = await response.json();
        tbody.innerHTML = orders.length
            ? orders.map(order => `
                <tr>
                    <td>${order.employee_name}</td>
                    <td>${order.item_name}</td>
                    <td>${order.quantity}</td>
                    <td class="status-${order.status.toLowerCase()}">${order.status}</td>
                    <td>${new Date(order.created_at).toLocaleDateString()}</td>
                </tr>
            `).join("")
            : `<tr><td colspan="5">No orders found</td></tr>`;
    } catch (error) {
        console.error("❌ Failed to load orders:", error);
        tbody.innerHTML = `<tr><td colspan="5" class="error">Error loading orders</td></tr>`;
    }
}

// 🔹 Export All Orders to Excel
async function exportAllOrders() {
    try {
        const response = await fetch(`${API_URL}/admin/orders/export`, {
            headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
        });

        if (!response.ok) throw new Error("Export failed");

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "all_orders.xlsx";
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    } catch (error) {
        alert("Export failed: " + error.message);
        console.error("Export error:", error);
    }
}

// 🔹 Export All Orders to CSV (Optional, if implemented in backend)
async function exportAllOrdersCSV() {
    alert("CSV export not implemented yet.");
    // Add backend route and logic if needed
}

// 🔹 Refresh Requests (for button)
function refreshRequests() {
    displayRequests();
}

// 🔹 Logout
function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    window.location.href = "/frontend/index.html";
}

// 🔹 Attach to Window for Global Access (Temporary; refactor later)
window.uploadInventory = uploadInventory;
window.displayRequests = displayRequests;
window.updateRequest = updateRequest;
window.exportAllOrders = exportAllOrders;
window.exportAllOrdersCSV = exportAllOrdersCSV;
window.refreshRequests = refreshRequests;
window.logout = logout;