// Function to render sidebar based on role
function renderSidebar(userRole) {
    const menu = document.getElementById("sidebar-menu");

    // Common buttons for all users
    let menuItems = `
        <li><a href="#">Dashboard</a></li>
        <li><a href="#">Message</a></li>
        <li><a href="#">Track</a></li>
        <li><a href="#">Profile</a></li>
    `;

    // Role-specific buttons
    if (userRole === "admin") {
        menuItems += `
            <li><a href="#">Manage</a></li>
            <li><a href="#">Receipt</a></li>
        `;
    } else if (userRole === "tenant") {
        menuItems += `
            <li><a href="#">Pay</a></li>
        `;
    }

    // Logout button
    menuItems += `
        <li><a href="#">Logout</a></li>
    `;

    // Add items to the sidebar menu
    menu.innerHTML = menuItems;
}

// Example usage
const userRole = "admin"; // Replace with dynamic role from backend
renderSidebar(userRole);
