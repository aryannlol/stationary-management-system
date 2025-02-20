// 🔹 SUPPLIER: Mark Order as Delivered
function markDelivered(orderId) {
    let orderIndex = supplierOrders.findIndex(order => order.id === orderId);
    if (orderIndex === -1) return;

    let order = supplierOrders[orderIndex];

    // Update inventory
    let itemIndex = inventory.findIndex(item => item.name.toLowerCase() === order.item.toLowerCase());
    if (itemIndex !== -1) {
        inventory[itemIndex].stock += order.quantity;
    } else {
        inventory.push({ id: inventory.length + 1, name: order.item, stock: order.quantity });
    }

    // Update order status
    supplierOrders[orderIndex].status = "Delivered";
    localStorage.setItem("supplierOrders", JSON.stringify(supplierOrders));
    alert("Order delivered and inventory updated!");
    displaySupplierOrders();
}

// 🔹 INIT: Load Data on Page Load
document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("my-requests")) displayEmployeeRequests();
    if (document.getElementById("admin-requests")) displayAdminRequests();
    if (document.getElementById("supplier-orders")) displaySupplierOrders();
});
// supplier.js
function displaySupplierOrders() { /* Show Orders */ }
function markDelivered(orderId) { /* Update Inventory */ }

document.addEventListener("DOMContentLoaded", displaySupplierOrders);
