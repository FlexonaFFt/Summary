import { useState, useEffect, useRef } from 'react'
import { setupTextareaAutosize } from './utils/textareaAutoResize'
import TypewriterText from './components/TypewriterText'
import './App.css'

function App() {
  const [inputText, setInputText] = useState('')
  const [messages, setMessages] = useState<Array<{type: 'user' | 'model', text: string}>>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const initTextareaResize = useRef<() => void>()

  useEffect(() => {
    // Сохраняем функцию инициализации для повторного использования
    initTextareaResize.current = setupTextareaAutosize();
  }, []);

  // Эффект для обновления высоты при изменении текста
  useEffect(() => {
    if (initTextareaResize.current) {
      initTextareaResize.current();
    }
  }, [inputText]);

  // Прокрутка чата вниз при добавлении новых сообщений
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!inputText.trim() || isLoading || isTyping) return
    
    // Добавляем сообщение пользователя в чат
    const userMessage = inputText.trim();
    setMessages(prev => [...prev, { type: 'user', text: userMessage }]);
    setInputText('');
    setIsLoading(true);
    
    try {
      // Здесь будет запрос к вашему API для суммаризации
      // Пример заглушки для демонстрации:
      setTimeout(() => {
        const modelResponse = `Это пример суммаризации текста: "${userMessage.substring(0, 50)}..."`;
        setIsLoading(false);
        setIsTyping(true);
        // Добавляем сообщение модели в чат
        setMessages(prev => [...prev, { type: 'model', text: modelResponse }]);
      }, 1000);
      
      // Реальный запрос будет выглядеть примерно так:
      // const response = await fetch('ваш_api_endpoint', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ text: userMessage })
      // });
      // const data = await response.json();
      // setIsTyping(true);
      // setMessages(prev => [...prev, { type: 'model', text: data.summary }]);
    } catch (error) {
      console.error('Ошибка при получении суммаризации:', error);
      setIsTyping(true);
      setMessages(prev => [...prev, { 
        type: 'model', 
        text: 'Произошла ошибка при обработке текста. Пожалуйста, попробуйте снова.' 
      }]);
    } finally {
      setIsLoading(false);
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      if (event.target?.result) {
        setInputText(event.target.result as string);
      }
    };
    reader.readAsText(file);
  }

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Отправка формы по нажатию Enter без Shift
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (inputText.trim() && !isLoading && !isTyping) {
        handleSubmit(e as unknown as React.FormEvent);
      }
    }
  };

  return (
    <div className="app-container">
      <div className="logo-container">
        <div className="logo">
          <div className="logo-top"></div>
          <div className="logo-bottom"></div>
        </div>
      </div>
      
      <div className="chat-container" ref={chatContainerRef}>
        {messages.length === 0 ? (
          <div className="welcome-message">
            <h1>Суммаризатор текста</h1>
            <p>Введите текст для суммаризации или загрузите файл</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div key={index} className={`message ${message.type}-message`}>
              <div className="message-avatar">
                {message.type === 'user' ? '👤' : '🤖'}
              </div>
              <div className="message-content">
                {message.type === 'model' && index === messages.length - 1 && isTyping ? (
                  <TypewriterText 
                    text={message.text} 
                    speed={20} 
                    onComplete={() => setIsTyping(false)} 
                  />
                ) : (
                  message.text
                )}
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="message model-message">
            <div className="message-avatar">🤖</div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
      </div>
      
      <div className="input-wrapper">
        <form onSubmit={handleSubmit} className="input-form">
          <textarea
            ref={textareaRef}
            value={inputText}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="Введите текст для суммаризации..."
            className="modern-input"
            rows={1}
            disabled={isLoading || isTyping}
          />
          <div className="input-actions">
            <label className="file-upload-label">
              <input 
                type="file" 
                accept=".txt,.doc,.docx,.pdf" 
                onChange={handleFileUpload}
                className="file-input"
                disabled={isLoading || isTyping}
              />
              <svg className="attachment-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M21.44 11.05l-9.19 9.19a6.003 6.003 0 01-8.49-8.49l9.19-9.19a4.002 4.002 0 015.66 5.66l-9.2 9.19a2.001 2.001 0 01-2.83-2.83l8.49-8.48" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </label>
            <button 
              type="submit" 
              className="send-button"
              disabled={isLoading || !inputText.trim() || isTyping}
            >
              {isLoading ? (
                <div className="loading-spinner"></div>
              ) : (
                <span className="send-icon-text">➤</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default App
