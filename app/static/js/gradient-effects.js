/**
 * Дополнительные скрипты для работы с градиентными эффектами
 */

// Функция для создания градиентного эффекта при наведении на карточки
function initGradientEffects() {
    const cards = document.querySelectorAll('.card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.borderTopColor = '#0066cc';
            const overlay = document.createElement('div');
            overlay.className = 'gradient-overlay';
            overlay.style.position = 'absolute';
            overlay.style.top = '0';
            overlay.style.left = '0';
            overlay.style.width = '100%';
            overlay.style.height = '4px';
            overlay.style.background = 'linear-gradient(90deg, #0066cc, #00994d)';
            overlay.style.zIndex = '10';
            overlay.style.opacity = '0';
            overlay.style.transition = 'opacity 0.3s';
            
            // Проверка на дубликаты
            const existingOverlay = this.querySelector('.gradient-overlay');
            if (!existingOverlay) {
                this.style.position = 'relative';
                this.prepend(overlay);
                setTimeout(() => {
                    overlay.style.opacity = '1';
                }, 10);
            }
        });
        
        card.addEventListener('mouseleave', function() {
            const overlay = this.querySelector('.gradient-overlay');
            if (overlay) {
                overlay.style.opacity = '0';
                setTimeout(() => {
                    overlay.remove();
                }, 300);
            }
        });
    });
}

// Функция для добавления градиентов к заголовкам
function addGradientHeadings() {
    const mainHeadings = document.querySelectorAll('h1.main-title, h2.section-title');
    mainHeadings.forEach(heading => {
        if (!heading.classList.contains('gradient-text')) {
            heading.classList.add('gradient-text');
        }
    });
}

// Функция для замены красных элементов градиентом
function replaceRedElements() {
    // Получаем все элементы на странице
    const allElements = document.querySelectorAll('*');
    
    // Перебираем элементы
    allElements.forEach(el => {
        // Проверяем вычисленные стили
        const style = window.getComputedStyle(el);
        const color = style.color;
        const backgroundColor = style.backgroundColor;
        const borderColor = style.borderColor;
        
        // Проверяем, содержит ли цвет красный компонент
        function isRedColor(colorStr) {
            // Обрабатываем RGB и RGBA форматы
            if (colorStr.includes('rgb')) {
                const rgbValues = colorStr.match(/\d+/g);
                if (rgbValues && rgbValues.length >= 3) {
                    const r = parseInt(rgbValues[0]);
                    const g = parseInt(rgbValues[1]);
                    const b = parseInt(rgbValues[2]);
                    // Если красный компонент значительно больше других, считаем это красным цветом
                    return r > 180 && g < 100 && b < 100;
                }
            }
            return false;
        }
        
        // Заменяем красные цвета текста на градиент
        if (isRedColor(color)) {
            el.style.color = 'transparent';
            el.style.backgroundImage = 'linear-gradient(90deg, #0066cc, #00994d)';
            el.style.backgroundClip = 'text';
            el.style.webkitBackgroundClip = 'text';
        }
        
        // Заменяем красные фоны на градиент
        if (isRedColor(backgroundColor)) {
            el.style.background = 'linear-gradient(135deg, #0066cc, #00994d)';
        }
        
        // Заменяем красные границы на градиентные
        if (isRedColor(borderColor)) {
            el.style.border = 'none';
            el.style.position = 'relative';
            
            // Добавляем псевдоэлемент с градиентной рамкой
            const hasGradientBorder = el.classList.contains('gradient-border-applied');
            if (!hasGradientBorder) {
                el.classList.add('gradient-border-applied');
                el.style.position = 'relative';
                el.style.border = '2px solid transparent';
                el.style.backgroundClip = 'padding-box';
                el.style.borderImage = 'linear-gradient(135deg, #0066cc, #00994d) 1';
            }
        }
    });
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initGradientEffects();
    addGradientHeadings();
    replaceRedElements();
    
    // Вызываем функцию замены красных элементов периодически,
    // чтобы обработать динамически добавленный контент
    setInterval(replaceRedElements, 3000);
});
