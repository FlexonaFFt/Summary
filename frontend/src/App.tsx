import { useState, useEffect, useRef } from 'react'
import { setupTextareaAutosize } from './utils/textareaAutoResize'
import './App.css'

function App() {
  const [inputText, setInputText] = useState('')
  const [summary, setSummary] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const initTextareaResize = useRef<() => void>()

  useEffect(() => {
    initTextareaResize.current = setupTextareaAutosize();
  }, []);

  useEffect(() => {
    if (initTextareaResize.current) {
      initTextareaResize.current();
    }
  }, [inputText]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!inputText.trim()) return
    
    setIsLoading(true)
    
    try {
      // Здесь будет запрос к API для суммаризации
      // заглушка
      setTimeout(() => {
        setSummary(`Это пример суммаризации текста: "${inputText.substring(0, 50)}..."`);
        setIsLoading(false);
      }, 1000);
      
      // Реальный запрос будет выглядеть примерно так:
      // const response = await fetch('ваш_api_endpoint', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ text: inputText })
      // });
      // const data = await response.json();
      // setSummary(data.summary);
    } catch (error) {
      console.error('Ошибка при получении суммаризации:', error);
      setSummary('Произошла ошибка при обработке текста. Пожалуйста, попробуйте снова.');
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
      if (inputText.trim() && !isLoading) {
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
      
      <div className="content-container">
        {summary && (
          <div className="summary-container">
            <h2>Результат суммаризации:</h2>
            <div className="summary-text">{summary}</div>
            <button 
              onClick={() => {
                setSummary('');
                setInputText('');
              }}
              className="reset-button"
            >
              Новая суммаризация
            </button>
          </div>
        )}
        
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
            />
            <div className="input-actions">
              <label className="file-upload-label">
                <input 
                  type="file" 
                  accept=".txt,.doc,.docx,.pdf" 
                  onChange={handleFileUpload}
                  className="file-input"
                />
                <svg className="attachment-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M21.44 11.05l-9.19 9.19a6.003 6.003 0 01-8.49-8.49l9.19-9.19a4.002 4.002 0 015.66 5.66l-9.2 9.19a2.001 2.001 0 01-2.83-2.83l8.49-8.48" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </label>
              <button 
                type="submit" 
                className="send-button"
                disabled={isLoading || !inputText.trim()}
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
    </div>
  )
}

export default App
