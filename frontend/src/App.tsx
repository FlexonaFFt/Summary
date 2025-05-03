import { useState, useEffect, useRef } from 'react'
import { setupTextareaAutosize } from './utils/textareaAutoResize'
import TypewriterText from './components/TypewriterText'
import './App.css'

// Добавим новый тип сообщения
type MessageType = 'user' | 'model' | 'file';

// Обновим интерфейс сообщения
interface Message {
  type: MessageType;
  text: string;
  fileInfo?: {
    name: string;
    size: number;
    type: string;
  };
}

function App() {
  const [inputText, setInputText] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [activeFile, setActiveFile] = useState<File | null>(null)
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
  
    // Сохраняем файл для дальнейшей обработки
    setActiveFile(file);
  
    // Добавляем сообщение о загрузке файла в чат с упрощенным текстом
    setMessages(prev => [...prev, { 
      type: 'file', 
      text: `Вами был загружен файл ${file.name} для суммаризации`,
      fileInfo: {
        name: file.name,
        size: file.size,
        type: file.type
      }
    }]);
  
    // Автоматически отправляем запрос на суммаризацию файла
    handleFileSubmit(file);
  }

  const handleFileSubmit = async (file: File) => {
    setIsLoading(true);
    
    try {
      // Здесь будет логика отправки файла на сервер
      // Пример заглушки для демонстрации:
      setTimeout(() => {
        const modelResponse = `Это пример суммаризации файла "${file.name}". Документ содержит информацию о...`;
        setIsLoading(false);
        setIsTyping(true);
        // Добавляем сообщение модели в чат
        setMessages(prev => [...prev, { type: 'model', text: modelResponse }]);
      }, 1500);
      
      // Реальный запрос будет выглядеть примерно так:
      // const formData = new FormData();
      // formData.append('file', file);
      // const response = await fetch('ваш_api_endpoint/upload', {
      //   method: 'POST',
      //   body: formData
      // });
      // const data = await response.json();
      // setIsTyping(true);
      // setMessages(prev => [...prev, { type: 'model', text: data.summary }]);
    } catch (error) {
      console.error('Ошибка при обработке файла:', error);
      setIsTyping(true);
      setMessages(prev => [...prev, { 
        type: 'model', 
        text: 'Произошла ошибка при обработке файла. Пожалуйста, попробуйте снова.' 
      }]);
    } finally {
      setIsLoading(false);
    }
  }

  // Функции для кнопок под ответом модели
  const handleContinueSummarization = () => {
    if (!activeFile) return;
    
    setIsLoading(true);
    
    // Здесь будет логика запроса продолжения суммаризации
    setTimeout(() => {
      const modelResponse = `Продолжение суммаризации файла "${activeFile.name}". Дополнительно можно отметить, что...`;
      setIsLoading(false);
      setIsTyping(true);
      setMessages(prev => [...prev, { type: 'model', text: modelResponse }]);
    }, 1500);
  }

  const handleAskQuestion = () => {
    if (!activeFile) return;
    
    // Показываем поле ввода с подсказкой для вопроса
    setInputText('');
    // Можно добавить специальную подсказку
    if (textareaRef.current) {
      textareaRef.current.placeholder = `Задайте вопрос по файлу "${activeFile.name}"...`;
      textareaRef.current.focus();
    }
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
          <>
            {messages.map((message, index) => (
              <div key={index} className={`message ${message.type}-message`}>
                <div className="message-avatar">
                  {message.type === 'user' ? '👤' : message.type === 'file' ? '📄' : '🤖'}
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
            ))}
            
            {/* Кнопки действий под последним ответом модели */}
            {messages.length > 0 && 
             messages[messages.length - 1].type === 'model' && 
             !isTyping && 
             activeFile && (
              <div className="model-actions">
                <button 
                  className="action-button"
                  onClick={handleContinueSummarization}
                >
                  Продолжить суммаризацию
                </button>
                <button 
                  className="action-button"
                  onClick={handleAskQuestion}
                >
                  Задать вопрос по файлу
                </button>
              </div>
            )}
          </>
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

// Вспомогательные функции
function getFileIcon(fileType: string): string {
  if (fileType.includes('pdf')) return 'PDF';
  if (fileType.includes('word') || fileType.includes('docx')) return 'DOC';
  if (fileType.includes('text')) return 'TXT';
  return 'FILE';
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

export default App
