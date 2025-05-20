from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
import os
import shutil  # Добавлен импорт shutil для функции copy_tokenizer_files

def copy_tokenizer_files(base_model_name, target_dir):
    """
    Копирует файлы токенизатора из базовой модели в целевую директорию.
    
    Args:
        base_model_name (str): Имя базовой модели
        target_dir (str): Путь к целевой директории
    """
    print(f"Загрузка токенизатора из {base_model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    cache_dir = tokenizer.save_pretrained("temp_tokenizer")
    tokenizer_files = ["tokenizer_config.json", "special_tokens_map.json", "spiece.model"]
    
    # Копируем файлы в целевую директорию
    for file in tokenizer_files:
        src_path = os.path.join("temp_tokenizer", file)
        if os.path.exists(src_path):
            dst_path = os.path.join(target_dir, file)
            print(f"Копирование {file} в {dst_path}...")
            shutil.copy(src_path, dst_path)
        else:
            print(f"Файл {file} не найден в кэше токенизатора.")
    
    # Удаляем временную директорию
    shutil.rmtree("temp_tokenizer")
    print("Готово!")

def load_model(model_path, base_model_name="t5-small"):
    """
    Загружает модель и токенизатор из указанного пути.
    Если локальная модель недоступна, использует базовую модель с Hugging Face.
    
    Args:
        model_path (str): Путь к директории с моделью
        base_model_name (str): Имя базовой модели для использования в случае ошибки
        
    Returns:
        tuple: (модель, токенизатор)
    """
    print(f"Загрузка модели из {model_path}...")
    
    try:
        # Проверяем наличие необходимых файлов для токенизатора
        tokenizer_files = ["tokenizer_config.json", "special_tokens_map.json", "spiece.model"]
        missing_files = [f for f in tokenizer_files if not os.path.exists(os.path.join(model_path, f))]
        
        if missing_files:
            print(f"Предупреждение: В директории модели отсутствуют следующие файлы токенизатора: {', '.join(missing_files)}")
            print(f"Попытка загрузки только модели из {model_path}...")
            
            # Загружаем токенизатор из базовой модели
            print(f"Загрузка токенизатора из базовой модели {base_model_name}...")
            tokenizer = AutoTokenizer.from_pretrained(base_model_name)
            
            # Загружаем модель из локального пути
            if os.path.exists(os.path.join(model_path, "pytorch_model.bin")) or os.path.exists(os.path.join(model_path, "model.safetensors")):
                model = AutoModelForSeq2SeqLM.from_pretrained(model_path)
            else:
                print(f"Файлы модели также отсутствуют. Загрузка полной модели из {base_model_name}...")
                model = AutoModelForSeq2SeqLM.from_pretrained(base_model_name)
        else:
            # Загрузка токенизатора и модели из локального пути
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_path)
    
    except Exception as e:
        print(f"Ошибка при загрузке модели: {str(e)}")
        print(f"Загрузка базовой модели {base_model_name} с Hugging Face...")
        tokenizer = AutoTokenizer.from_pretrained(base_model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(base_model_name)
    
    print("Модель успешно загружена!")
    return model, tokenizer

def summarize_text(model, tokenizer, text, max_length=150, min_length=40):
    """
    Создает суммаризацию для заданного текста.
    
    Args:
        model: Модель для суммаризации
        tokenizer: Токенизатор для модели
        text (str): Текст для суммаризации
        max_length (int): Максимальная длина суммаризации
        min_length (int): Минимальная длина суммаризации
        
    Returns:
        str: Суммаризированный текст
    """
    # Подготовка входных данных
    inputs = tokenizer(text, return_tensors="pt", max_length=1024, truncation=True)
    
    # Генерация суммаризации
    with torch.no_grad():
        summary_ids = model.generate(
            inputs["input_ids"],
            max_length=max_length,
            min_length=min_length,
            num_beams=4,
            length_penalty=2.0,
            early_stopping=True
        )
    
    # Декодирование результата
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summary

def main():
    # Путь к модели - исправлен на полный путь
    model_path = "/Users/flexonafft/Documents/Summary/final_model/"
    base_model_name = "t5-small"  
    model, tokenizer = load_model(model_path, base_model_name)
    test_texts = [
        """Жертвами урагана «Агата», обрушившегося на Центральную Америку, стали 146 человек. В Гватемале от стихии погибли 123 человека, 59 пропали без вести. «Агата» убила девять человек в Сальвадоре и 14 в Гондурасе. 
        Как передает Reuters , тысячи людей пытаются найти своих близких в разрушенных домах. Спасатели уговаривают жителей покинуть все строения, многие из которых могут рухнуть, и перейти в специальные приюты. Наиболее серьезные разрушения ураган принес в горную часть страны. 
        Большинство домов в Гватемале просто снесли сошедшие из-за проливных дождей оползни, какие-то строения смыли вышедшие из берегов реки. «Мне некому помочь. Я просто молча смотрела, как вода забирает все», — рассказывает Карлота Рамос, жительница города Аматитлан, находящегося рядом со столицей страны Гватемалой. 
        Один из спасателей Рони Велис говорит, что работать в возникших условиях «очень тяжело». Из-за непрекращающихся ливней вертолеты все еще не могут подняться в воздух, и спасателям приходиться пешком переходит горные перевалы по размытым дорогам, чтобы добраться до некоторых городов и деревень. 
        Затем пешком вместе с ранеными идти обратно. Спасатель Марио Крус сказал Reuters, что для спасения людей катастрофически не хватает оборудования. «У нас есть только лопаты и кирки. И ими нам приходится раскапывать заваленные землей дома», — говорит он. Ожидается, что дожди в регионе прекратятся во вторник, и тогда в эвакуации будут участвовать самолеты и вертолеты. 
        Первая помощь пострадавшим странам от иностранных государств начала поступать уже в понедельник. Правительство США предоставило $113 тысяч Гватемале, которые пойдут на обеспечение пострадавших районов предметами первой необходимости и оплату услуг частных вертолетных компаний. Последние, как ожидают в правительстве, помогут эвакуировать раненых и доставить в регионы необходимые продукты. 
        Официальные лица уже признают, что ураган «Агата» нанес пострадавшим странам, в особенности Гватемале, колоссальный ущерб: разрушены или затоплены тысячи домов, размыты дороги, в том числе и крупные автострады, нарушено энергоснабжение, во многих районах отсутствует телефонная связь. Эвакуированы около 112 тысяч человек. 
        Кроме того, в Гватемале уничтожены посевы кофе, производство которого является одним из основных доходов страны. Эксперты говорят, что «Агата» открыла сезон ураганов для Центральной Америки, который, утверждают специалисты, «будет особенно жестоким». В ближайшие полгода эксперты ожидают, что на регион обрушится 14 достаточно сильных ураганов. 
        «Это может быть самый страшный сезон ураганов за последние 50 лет», — сказал один из координаторов Красного Креста Расо Мальдонадо. Организация, по его словам, готовится к стихийным бедствиям. Сейчас Красный Крест, говорит Мальдонадо, может оказать неотложную помощь 18 тысячам человек. Напомним, что в пятницу в Гватемале также произошло извержение вулкана Пакайя. 
        Из-за этого был закрыт главный международный аэропорт страны Aurora. Были также эвакуированы жители четырех деревень, расположенных на склонах вулкана.""",
    ]
    
    # Тестирование модели на примерах
    print("\n--- Тестирование модели суммаризации ---\n")
    for i, text in enumerate(test_texts, 1):
        print(f"Пример #{i}:")
        print(f"Исходный текст: {text[:100]}...")
        
        summary = summarize_text(model, tokenizer, text)
        
        print(f"Суммаризация: {summary}")
        print("-" * 50)

if __name__ == "__main__":
    main()