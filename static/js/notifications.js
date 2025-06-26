// Notification system with smooth animations
class NotificationSystem {
    constructor() {
        this.container = null;
        this.init();
    }

    init() {
        // Create notification container if it doesn't exist
        if (!document.getElementById('notification-container')) {
            this.container = document.createElement('div');
            this.container.id = 'notification-container';
            this.container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                display: flex;
                flex-direction: column;
                gap: 10px;
                max-width: 350px;
            `;
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('notification-container');
        }
    }

    show(message, type = 'success', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            background: white;
            border-left: 4px solid ${this.getColorForType(type)};
            padding: 15px 20px;
            border-radius: 4px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transform: translateX(100%);
            opacity: 0;
            transition: all 0.3s ease-out;
            margin-bottom: 10px;
            position: relative;
            overflow: hidden;
        `;

        // Add icon based on type
        const icon = this.getIconForType(type);
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <i class="fas ${icon}" style="color: ${this.getColorForType(type)};"></i>
                <div style="flex-grow: 1;">${message}</div>
                <button class="close-btn" style="background: none; border: none; cursor: pointer; padding: 0 5px;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="progress-bar" style="
                position: absolute;
                bottom: 0;
                left: 0;
                height: 3px;
                background: ${this.getColorForType(type)};
                width: 100%;
                transform: scaleX(1);
                transform-origin: left;
                transition: transform ${duration}ms linear;
            "></div>
        `;

        this.container.appendChild(notification);

        // Trigger animation
        requestAnimationFrame(() => {
            notification.style.transform = 'translateX(0)';
            notification.style.opacity = '1';
        });

        // Add close button functionality
        const closeBtn = notification.querySelector('.close-btn');
        closeBtn.addEventListener('click', () => this.close(notification));

        // Start progress bar animation
        requestAnimationFrame(() => {
            const progressBar = notification.querySelector('.progress-bar');
            progressBar.style.transform = 'scaleX(0)';
        });

        // Auto close after duration
        const timeout = setTimeout(() => {
            this.close(notification);
        }, duration);

        // Store timeout ID for cleanup
        notification.dataset.timeoutId = timeout;
    }

    close(notification) {
        // Clear timeout if exists
        if (notification.dataset.timeoutId) {
            clearTimeout(parseInt(notification.dataset.timeoutId));
        }

        // Animate out
        notification.style.transform = 'translateX(100%)';
        notification.style.opacity = '0';

        // Remove after animation
        setTimeout(() => {
            if (notification.parentNode === this.container) {
                this.container.removeChild(notification);
            }
        }, 300);
    }

    getColorForType(type) {
        const colors = {
            success: '#28a745',
            error: '#dc3545',
            warning: '#ffc107',
            info: '#17a2b8'
        };
        return colors[type] || colors.info;
    }

    getIconForType(type) {
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-times-circle',
            warning: 'fa-exclamation-circle',
            info: 'fa-info-circle'
        };
        return icons[type] || icons.info;
    }
}

// Create global notification instance
window.notifications = new NotificationSystem();

// Global function to show notifications
function showNotification(message, type = 'success', duration = 5000) {
    window.notifications.show(message, type, duration);
} 