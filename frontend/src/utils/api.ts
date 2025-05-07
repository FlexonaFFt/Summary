// API клиент для взаимодействия с бэкендом

const API_BASE_URL = 'http://localhost:8000';

export interface ApiResponse {
  request_id?: string;
  filename?: string;
  status?: string;
  summary?: string;
  error?: string;
}

/**
 * Отправляет текст на суммаризацию
 */
export const summarizeText = async (text: string): Promise<ApiResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/summarize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    
    if (!response.ok) {
      throw new Error(`Ошибка HTTP: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Ошибка при отправке текста на суммаризацию:', error);
    return { error: 'Произошла ошибка при отправке текста на суммаризацию' };
  }
};

/**
 * Проверяет статус суммаризации по ID запроса
 */
export const checkStatus = async (requestId: string): Promise<ApiResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/status/${requestId}`, {
      method: 'GET'
    });
    
    if (!response.ok) {
      throw new Error(`Ошибка HTTP: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Ошибка при проверке статуса:', error);
    return { error: 'Произошла ошибка при проверке статуса' };
  }
};

/**
 * Отправляет файл на суммаризацию
 */
export const summarizeFile = async (file: File): Promise<ApiResponse> => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE_URL}/summarize-file`, {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      throw new Error(`Ошибка HTTP: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Ошибка при суммаризации файла:', error);
    return { error: 'Произошла ошибка при суммаризации файла' };
  }
};

/**
 * Опрашивает статус суммаризации до получения результата
 */
export const pollStatus = async (requestId: string, maxAttempts = 30, interval = 1000): Promise<ApiResponse> => {
  let attempts = 0;
  
  while (attempts < maxAttempts) {
    const result = await checkStatus(requestId);
    
    if (result.error) {
      return result;
    }
    
    if (result.status === 'done') {
      return result;
    }
    
    if (result.status === 'not_found') {
      return { error: 'Запрос не найден' };
    }
    
    // Ждем перед следующей попыткой
    await new Promise(resolve => setTimeout(resolve, interval));
    attempts++;
  }
  
  return { error: 'Превышено время ожидания ответа' };
};