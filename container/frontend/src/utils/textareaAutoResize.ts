export function setupTextareaAutosize() {
  const resizeTextarea = (textarea: HTMLTextAreaElement) => {
    textarea.style.height = 'auto';
    textarea.style.height = `${textarea.scrollHeight}px`;
  };

  const handleInput = (event: Event) => {
    const textarea = event.target as HTMLTextAreaElement;
    resizeTextarea(textarea);
  };

  // Функция для инициализации текстовых полей
  const initializeTextareas = () => {
    const textareas = document.querySelectorAll<HTMLTextAreaElement>('.modern-input');
    textareas.forEach((textarea) => {
      // Удаляем предыдущие обработчики, чтобы избежать дублирования
      textarea.removeEventListener('input', handleInput);
      
      // Добавляем обработчик события input
      textarea.addEventListener('input', handleInput);
      
      // Инициализируем высоту
      resizeTextarea(textarea);
    });
  };

  // Инициализация при загрузке DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeTextareas);
  } else {
    // DOM уже загружен
    initializeTextareas();
  }

  // Повторная инициализация при изменении размера окна
  window.addEventListener('resize', () => {
    const textareas = document.querySelectorAll<HTMLTextAreaElement>('.modern-input');
    textareas.forEach(resizeTextarea);
  });

  // Возвращаем функцию для ручной инициализации
  return initializeTextareas;
}