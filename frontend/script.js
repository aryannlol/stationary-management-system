document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const role = document.getElementById('role').value;
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    // Basic validation
    if (!role || !username || !password) {
        alert('Please fill in all fields');
        return;
    }

    try {
        // Send login request to the backend
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password, role }),
        });

        const data = await response.json();

        if (response.ok) {
            // Save the token in localStorage or sessionStorage
            localStorage.setItem('token', data.token);
            localStorage.setItem('role', data.role);

            // Redirect based on role
            let redirectUrl;
            switch (data.role) {
                case 'admin':
                    redirectUrl = '/frontend/admin/admin_index.html';
                    break;
                case 'employee':
                    redirectUrl = '/frontend/employee/emp_index.html';
                    break;
                case 'supplier':
                    redirectUrl = '/frontend/supplier/supp_index.html';
                    break;
                default:
                    alert('Invalid role');
                    return;
            }

            window.location.href = redirectUrl;
        } else {
            alert(data.message || 'Login failed');
        }
    } catch (error) {
        console.error('Error during login:', error);
        alert('An error occurred during login');
    }
});
