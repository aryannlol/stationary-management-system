const API_URL = "http://127.0.0.1:5000"; // Make sure API_URL is defined

// 🔹 Upload Inventory (Excel File)
async function uploadInventory() {
    const fileInput = document.getElementById("inventoryFile");
    if (!fileInput.files.length) {
        alert("Please select a file to upload.");
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    const token = localStorage.getItem("token"); // 🔹 Retrieve the JWT token

    if (!token) {
        alert("You are not logged in. Please log in as an admin.");
        return;
    }

    console.log("🔹 Uploading Inventory with Token:", token);

    try {
        const response = await fetch(`${API_URL}/upload-inventory`, {
            method: "POST",
            body: formData,
            headers: {
                "Authorization": `Bearer ${token}` // 🔹 Send token in the Authorization header
            }
        });

        const result = await response.json();
        if (response.ok) {
            alert("✅ Inventory uploaded successfully!");
        } else {
            console.error("❌ Upload Error:", result);
            alert(`Error: ${result.message || "Failed to upload inventory."}`);
        }
    } catch (error) {
        console.error("❌ Upload Error:", error);
        alert("Failed to upload inventory. Check console for details.");
    }
}

// 🔹 Fetch and Display Requests
async function displayRequests() {
    const token = localStorage.getItem("token");
    const requestTable = document.getElementById("admin-requests");
    
    try {
        const response = await fetch(`${API_URL}/admin/requests`, {
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            }
        });

        if (response.status === 403) {
            alert("Access denied. Please log in as an administrator.");
            window.location.href = "index.html";
            return;
        }

        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }

        const requests = await response.json();
        requestTable.innerHTML = "";

        if (!Array.isArray(requests) || requests.length === 0) {
            requestTable.innerHTML = "<tr><td colspan='5'>No requests found</td></tr>";
            return;
        }

        requests.forEach(request => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${request.item_name}</td>
                <td>${request.quantity}</td>
                <td>${request.status}</td>
                <td>${request.employee_name}</td>
                <td>
                    ${request.status === "pending" ? `
                        <button onclick="updateRequest('${request.id}', 'approved')" 
                                class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded mr-2">
                            Approve
                        </button>
                        <button onclick="updateRequest('${request.id}', 'rejected')"
                                class="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded">
                            Reject
                        </button>
                    ` : request.status}
                </td>
            `;
            requestTable.appendChild(row);
        });

    } catch (error) {
        console.error("Error fetching requests:", error);
        alert("Failed to load requests. Please try again.");
    }
}

async function updateRequest(requestId, status) {
    if (!requestId) {
        console.error("Error: Request ID is undefined!");
        return;
    }

    const token = localStorage.getItem("token");
    
    try {
        const response = await fetch(`${API_URL}/requests/${requestId}`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ status: status })
        });

        if (response.status === 403) {
            alert("Access denied. Please log in as an administrator.");
            window.location.href = "index.html";
            return;
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        alert(data.message);
        await displayRequests(); // Refresh the list
        
    } catch (error) {
        console.error("Error updating request:", error);
        alert("Failed to update request: " + error.message);
    }
}

// Logout function
function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    window.location.href = "index.html";
}

// Make functions available globally
window.updateRequest = updateRequest;
window.displayRequests = displayRequests;
window.logout = logout;

function fetchRequests() {
    fetch("http://127.0.0.1:5000/requests", {
        headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
    })
    .then(response => response.json())
    .then(data => {
        let tableBody = document.getElementById("admin-requests");
        tableBody.innerHTML = ""; // Clear previous entries

        data.forEach(request => {
            console.log("Request ID:", request.id);  // ✅ Debugging

            let row = document.createElement("tr");
            row.innerHTML = `
                <td>${request.item_name}</td>
                <td>${request.quantity}</td>
                <td>${request.status}</td>
                <td>
                    <button onclick="updateRequest(${request.id}, 'approved')">Approve</button>
                    <button onclick="updateRequest(${request.id}, 'rejected')">Reject</button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    })
    .catch(error => console.error("Error fetching requests:", error));
}


async function clearRequests() {
    const token = localStorage.getItem("token");

    try {
        const response = await fetch(`${API_URL}/requests/clear`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" }
        });

        if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);

        console.log("✅ Requests cleared successfully!");

        // 🔹 Remove from UI after deleting from DB
        const requestTable = document.getElementById("admin-requests");
        requestTable.innerHTML = "<tr><td colspan='4'>No requests available</td></tr>";

    } catch (error) {
        console.error("❌ Error clearing requests:", error);
        alert("Failed to clear requests.");
    }
}
window.clearRequests = clearRequests;

// 🔹 Refresh Requests
window.refreshRequests = displayRequests;

// 🔹 Load Requests on Page Load
document.addEventListener("DOMContentLoaded", displayRequests);
