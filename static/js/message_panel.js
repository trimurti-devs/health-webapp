console.log('message_panel.js loaded');
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded and parsed');
    const messageItems = document.querySelectorAll('.message-item');
    const sidePanel = document.createElement('div');
    sidePanel.id = 'messageSidePanel';
    sidePanel.style.position = 'fixed';
    sidePanel.style.top = '0';
    sidePanel.style.right = '-400px';
    sidePanel.style.width = '400px';
    sidePanel.style.height = '100%';
    sidePanel.style.backgroundColor = '#fff';
    sidePanel.style.boxShadow = '-2px 0 5px rgba(0,0,0,0.3)';
    sidePanel.style.transition = 'right 0.3s ease';
    sidePanel.style.zIndex = '1050';
    sidePanel.style.overflowY = 'auto';
    sidePanel.style.padding = '20px';
    sidePanel.style.display = 'flex';
    sidePanel.style.flexDirection = 'column';

    // Close button
    const closeBtn = document.createElement('button');
    closeBtn.textContent = '×';
    closeBtn.style.fontSize = '2rem';
    closeBtn.style.border = 'none';
    closeBtn.style.background = 'none';
    closeBtn.style.alignSelf = 'flex-end';
    closeBtn.style.cursor = 'pointer';
    closeBtn.setAttribute('aria-label', 'Close message panel');
    closeBtn.addEventListener('click', () => {
        sidePanel.style.right = '-400px';
    });
    sidePanel.appendChild(closeBtn);

    // Content container
    const contentContainer = document.createElement('div');
    contentContainer.id = 'messageContentContainer';
    contentContainer.style.flexGrow = '1';
    sidePanel.appendChild(contentContainer);

    document.body.appendChild(sidePanel);

    if (messageItems.length === 0) {
        console.warn('No message items found');
    }

    messageItems.forEach(item => {
        const viewBtn = item.querySelector('button.open-message-btn');
        if (viewBtn) {
            viewBtn.addEventListener('click', function(event) {
                event.preventDefault();
                console.log('Message eye icon clicked');
                const messageId = this.getAttribute('data-message-id');
                console.log('Message ID:', messageId);
                if (messageId) {
                    fetchMessage(`/api/message/${messageId}`);
                    markMessageRead(messageId);
                } else {
                    console.error('Invalid message ID:', messageId);
                }
            });
        } else {
            console.warn('No open-message-btn found in message item');
        }
    });

    function fetchMessage(url) {
        console.log('Fetching message from URL:', url);
        // Extract message_id from URL
        try {
            const urlObj = new URL(url, window.location.origin);
            const messageId = urlObj.pathname.split('/').pop();

            fetch(`/api/message/${messageId}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Message data received:', data);
                    displayMessage(data);
                    sidePanel.style.right = '0';
                })
                .catch(error => {
                    alert('Failed to load message details. See console for details.');
                    console.error('Error fetching message:', error);
                });
        } catch (e) {
            alert('Invalid URL for fetching message.');
            console.error('URL parsing error:', e);
        }
    }

    function markMessageRead(messageId) {
        fetch(`/api/message/mark-read/${messageId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrf_token') // If CSRF protection is enabled
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to mark message as read');
            }
            // Update UI to remove "New" badge and bold styling
            const messageItem = document.querySelector(`button.open-message-btn[data-message-id="${messageId}"]`).closest('.message-item');
            if (messageItem) {
                messageItem.classList.remove('message-unread');
                const badge = messageItem.querySelector('.badge.bg-primary');
                if (badge) {
                    badge.remove();
                }
                const senderName = messageItem.querySelector('h6.fw-bold');
                if (senderName) {
                    senderName.classList.remove('fw-bold');
                }
            }
        })
        .catch(error => {
            console.error('Error marking message as read:', error);
        });
    }

    // Helper function to get cookie by name (for CSRF token)
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function displayMessage(message) {
        contentContainer.innerHTML = `
            <h4>${message.subject}</h4>
            <p><strong>From:</strong> ${message.sender_full_name} (${message.sender_user_type})</p>
            <p><strong>Date:</strong> ${message.created_at}</p>
            <hr>
            <p>${message.content.replace(/\n/g, '<br>')}</p>
        `;
    }
});
