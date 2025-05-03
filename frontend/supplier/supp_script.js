const API_URL = "http://127.0.0.1:5000";

document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "/frontend/index.html";
        return;
    }
    fetchSupplierOrders();
});

async function fetchSupplierOrders() {
    const container = document.getElementById("ordersContainer");
    const token = localStorage.getItem("token");
    try {
        container.innerHTML = "<p>Loading orders...</p>";
        const response = await fetch(`${API_URL}/supplier-orders`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!response.ok) {
            throw new Error(`Failed to load orders: ${response.status}`);
        }
        const orders = await response.json();
        container.innerHTML = orders.length
            ? orders.map(order => `
                <div class="order-card">
                    <p>Item: ${order.item_name}</p>
                    <p>Quantity: ${order.quantity}</p>
                    <p>Status: ${order.status}</p>
                    ${order.status === "pending" ? `
                        <button onclick="updateOrderStatus(${order.id}, 'shipped')">Mark as Shipped</button>
                        <button onclick="updateOrderStatus(${order.id}, 'delivered')">Mark as Delivered</button>
                    ` : ""}
                </div>
            `).join("")
            : "<p>No orders found</p>";
    } catch (error) {
        console.error("Error:", error);
        container.innerHTML = `<p class="error">Failed to load orders: ${error.message}</p>`;
    }
}

async function updateOrderStatus(orderId, status) {
    const token = localStorage.getItem("token");
    try {
        const response = await fetch(`${API_URL}/supplier-orders/${orderId}`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ status })
        });
        if (!response.ok) throw new Error((await response.json()).message || "Failed to update order");
        alert(`Order marked as ${status}!`);
        fetchSupplierOrders();
    } catch (error) {
        console.error("Error:", error);
        alert(`Error: ${error.message}`);
    }
}