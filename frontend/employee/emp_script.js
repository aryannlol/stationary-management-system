const API_URL = "http://127.0.0.1:5000";

// 🔹 Unified Initialization on Page Load
document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "/frontend/index.html";
        return;
    }

    checkUserRole();  // Ensure only employees access this page
    fetchItemsAndPopulateDropdown();  // Load inventory
    displayEmployeeRequests();  // Load requests
});

// 🔹 Search Items
async function searchItem() {
    const token = localStorage.getItem("token");
    let searchValue = document.getElementById("searchItem").value.toLowerCase();

    try {
        const response = await fetch(`${API_URL}/inventory?search=${searchValue}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (response.status === 401) {
            handleUnauthorized();
            return;
        }

        const results = await response.json();
        const resultBox = document.getElementById("searchResults");
        resultBox.innerHTML = results.length
            ? results.map(item => `<p>${item.name} (Stock: ${item.stock})</p>`).join("")
            : "<p>No items found.</p>";
    } catch (error) {
        console.error("Error searching items:", error);
        alert("Error searching items. Please try again.");
    }
}

// 🔹 Fetch Inventory & Populate Dropdown
async function fetchItemsAndPopulateDropdown() {
    const token = localStorage.getItem("token");
    const itemDropdown = document.getElementById("itemDropdown");

    try {
        // ✅ Fetch from `/items` instead of `/inventory`
        const response = await fetch(`${API_URL}/items`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);

        const items = await response.json();
        console.log("✅ Inventory Fetched:", items);

        if (!items.length) {
            alert("No items found in inventory.");
            return;
        }

        itemDropdown.innerHTML = '<option value="">Select an item</option>';
        items.forEach(item => {
            let option = document.createElement("option");
            option.value = item.id;
            option.textContent = `${item.name} (Stock: ${item.stock})`;
            itemDropdown.appendChild(option);
        });

    } catch (error) {
        console.error("❌ Error fetching inventory:", error);
        alert("Error fetching inventory. Check the console.");
    }
}

// 🔹 Submit Request
async function submitRequest(event) {
    event.preventDefault();

    const token = localStorage.getItem("token");
    if (!token) {
        alert("You must be logged in to submit a request.");
        return;
    }

    const itemId = parseInt(document.getElementById("itemDropdown").value);
    const quantity = parseInt(document.getElementById("quantity").value);
    const reason = document.getElementById("reason").value;

    if (!itemId || isNaN(itemId)) {
        alert("Please select a valid item.");
        return;
    }

    const requestData = { item_id: itemId, quantity, reason };

    try {
        console.log("🔹 Sending Request:", requestData); // ✅ Debug Log

        const response = await fetch(`${API_URL}/requests`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(requestData)
        });

        const result = await response.json();
        console.log("🔹 Response:", result); // ✅ Debug Log

        if (!response.ok) {
            throw new Error(result.message || `HTTP error! status: ${response.status}`);
        }

        alert("✅ Request submitted successfully!");
        document.getElementById("requestForm").reset();
        displayEmployeeRequests(); // Refresh requests list
    } catch (error) {
        console.error("❌ Error submitting request:", error);
        alert(error.message);
    }
}

// ✅ Make sure the form submission is handled
document.getElementById("requestForm").addEventListener("submit", submitRequest);


// 🔹 Display Employee Requests
async function displayEmployeeRequests() {
    const token = localStorage.getItem("token");
    const requestContainer = document.getElementById("my-requests");

    try {
        const response = await fetch(`${API_URL}/requests`, {
            headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" }
        });

        if (!response.ok) throw new Error(`HTTP Error! Status: ${response.status}`);

        const requests = await response.json();
        console.log("🔹 Employee Requests:", requests); // Debugging

        requestContainer.innerHTML = "";

        if (!Array.isArray(requests) || requests.length === 0) {
            requestContainer.innerHTML = "<tr><td colspan='4'>No requests found</td></tr>";
            return;
        }

        requestContainer.innerHTML = requests.map(req => `
            <tr>
                <td>${req.item_name || "Unknown"}</td>
                <td>${req.quantity}</td>
                <td>${req.status}</td>
                <td>${req.admin_response || "Pending"}</td>
            </tr>
        `).join("");

    } catch (error) {
        console.error("❌ Error Fetching Employee Requests:", error);
    }
}

// 🔹 Updated Refresh Function
async function refreshRequests() {
    console.log("🔄 Refreshing Requests...");
    await displayEmployeeRequests();
}

// 🔹 Handle Unauthorized Users
function handleUnauthorized() {
    localStorage.removeItem("token");
    localStorage.removeItem("role");

    alert("Session expired or unauthorized access. Please log in again.");
    window.location.href = "/frontend/index.html";
}

// 🔹 Check User Role
function checkUserRole() {
    const role = localStorage.getItem("role");
    if (role === "admin") {
        window.location.href = "/frontend/admin_dashboard.html";  // Redirect admins
    } else if (role !== "employee") {
        handleUnauthorized();
    }
}

// 🔹 Logout
function logout() {
    const token = localStorage.getItem("token");

    fetch(`${API_URL}/logout`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
    }).finally(() => {
        localStorage.removeItem("token");
        localStorage.removeItem("role");
        window.location.href = "/frontend/index.html";
    });
}

// 🔹 Make functions available globally
window.searchItem = searchItem;
window.submitRequest = submitRequest;
window.refreshRequests = refreshRequests;
window.logout = logout;
