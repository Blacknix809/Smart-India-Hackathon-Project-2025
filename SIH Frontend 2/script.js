const authSection = document.getElementById('auth-section');
const loginForm = document.getElementById('login-form');
const signupForm = document.getElementById('signup-form');
const showSignupLink = document.getElementById('show-signup');
const showLoginLink = document.getElementById('show-login');
const dynamicTitle = document.getElementById('dynamic-title');
const dynamicSubtitle = document.getElementById('dynamic-subtitle');

function showPage(page) {
    if (page === 'login') {
        loginForm.classList.remove('hidden');
        signupForm.classList.add('hidden');
        dynamicTitle.textContent = 'Nice to see you again!';
        dynamicSubtitle.textContent = 'Please log in to continue your journey';
    } else {
        loginForm.classList.add('hidden');
        signupForm.classList.remove('hidden');
        dynamicTitle.textContent = 'Nice to see you!';
        dynamicSubtitle.textContent = 'Please enter your details to create your account';
    }
}

// Handle Signup Form Submission
signupForm.addEventListener('submit', (e) => {
    e.preventDefault();

    const name = document.getElementById('name-signup').value;
    const email = document.getElementById('email-signup').value;
    const password = document.getElementById('password-signup').value;
    const wisherName = document.getElementById('wisher-name-signup').value;
    const wisherRelation = document.getElementById('wisher-relation-signup').value;
    const wisherPhone = document.getElementById('wisher-phone-signup').value;
    const wisherEmail = document.getElementById('wisher-email-signup').value;
    
    if (!name || !email || !password || !wisherName || !wisherRelation || !wisherPhone || !wisherEmail) {
        alert('Please fill in all required fields to create an account.');
        return;
    }

    const userData = {
        name,
        email,
        password,
        wisher: {
            name: wisherName,
            relation: wisherRelation,
            phone: wisherPhone,
            email: wisherEmail
        }
    };
    localStorage.setItem('userData', JSON.stringify(userData));
    
    alert('Sign up successful! Please log in with your new account.');
    showPage('login');
});

// Handle Login Form Submission
loginForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const email = document.getElementById('email-login').value;
    const password = document.getElementById('password-login').value;
    const storedData = localStorage.getItem('userData');
    
    if (storedData) {
        const userData = JSON.parse(storedData);
        if (userData.email === email && userData.password === password) {
            window.location.href = 'index.html'; 
        } else {
            alert('Invalid email or password.');
        }
    } else {
        alert('No account found. Please sign up first.');
    }
});

// Event listeners for toggling
showSignupLink.addEventListener('click', (e) => {
    e.preventDefault();
    showPage('signup');
});

showLoginLink.addEventListener('click', (e) => {
    e.preventDefault();
    showPage('login');
});

// Initial check on page load
window.addEventListener('load', () => {
    const storedData = localStorage.getItem('userData');
    if (storedData) {
        showPage('login');
    } else {
        showPage('signup');
    }
});