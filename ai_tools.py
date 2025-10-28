from datetime import datetime
from huggingface_hub import InferenceClient
from database import save_error_data, save_start_downtime, save_end_downtime
from config.config import Config, load_config


config: Config = load_config('config/.env')

client = InferenceClient(
    provider="hf-inference",
    api_key=config.tg_bot.hf_token
  )

def evaluate_model(prompt):
    messages = [
        {
            "role": "user",
            "content": prompt
        }
    ]

    completion = client.chat.completions.create(
        model="google/gemma-2-27b-it",
        messages=messages,
        max_tokens=250
    )

    return completion.choices[0].message.content


PROMPT_TEMPLATE = """
Анализируй производственные сообщения строго по следующим правилам:

1. Определи тип события:
- "Начало простоя" если оборудование остановлено
- "Устранение простоя" если работа восстановлена
- "Появление ошибки" если есть проблема для устранения

2. Извлеки данные по шаблону:
[Тип: тип_события]
[Цех: номер_цеха]
[Агрегат: идентификатор_агрегата]
[Информация: дополнительный_текст] (ТОЛЬКО для ошибок)

3. Правила извлечения:
- Используй паттерны: "цех X", "станок Y", "агрегат Z"
- Для ошибок извлекай всю доступную информацию после описания проблемы
- Если данные не найдены → "не указано"

Примеры ответов:
[Тип: Появление ошибки]
[Цех: 12]
[Агрегат: ПА-05]
[Информация: Гидравлическая утечка, требуется срочный ремонт]

[Тип: Начало простоя]
[Цех: 3]
[Агрегат: ЛМ-789]

Сообщение: {input_text}
Ответ:
"""
def extract_data_downtime(text):
    prompt = PROMPT_TEMPLATE.format(input_text=text)
    answer = evaluate_model(prompt).split()
    workshop_num = answer[0]
    unit_num = answer[1]
    return workshop_num, unit_num


def extract_data_error(text):
    prompt = PROMPT_TEMPLATE.format(input_text=text)
    answer = evaluate_model(prompt).split(";")
    workshop_num = answer[0]
    unit_num = answer[1]
    info = answer[2]
    return workshop_num, unit_num, info

def analyze_production_message(text: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(input_text=text)
    try:
        message = evaluate_model(prompt)
    except Exception as e:
        print(f"Ошибка вызова модели {model}: {str(e)}")
        return {"type": "ошибка", "workshop": "н/д", "unit": "н/д"}
    return message

def process_response(model_response: str) -> dict:
    result = {
        "type": "не определено",
        "workshop": "н/д",
        "unit": "н/д"
    }

    current_info = []
    info_block = False

    for line in model_response.split('\n'):
        line = line.strip()
        if not line:
            continue

        try:
            if line.startswith('[Тип:'):
                result["type"] = line.split(': ')[1].strip(' ]')
            elif line.startswith('[Цех:'):
                result["workshop"] = line.split(': ')[1].strip(' ]').replace('"', '')
            elif line.startswith('[Агрегат:'):
                result["unit"] = line.split(': ')[1].strip(' ]').replace('"', '')
            elif line.startswith('[Информация:'):
                info_content = line.split(': ', 1)[1].strip(' ]')
                current_info.append(info_content)
                info_block = True
            elif info_block:
                current_info.append(line.strip(' []'))
        except Exception as e:
            print(f"Ошибка обработки строки: {line} | {str(e)}")
            continue
    if current_info:
        result["info"] = ' '.join(current_info).strip()
        return f'[Тип: {result["type"]}]\n[Цех: {result["workshop"]}]\n\n[Агрегат: {result["unit"]}]\n[Информация: {result["info"]}]'
    if result["type"] == '"Появление ошибки"' or result["type"] == "Появление ошибки":
        save_error_data(result["workshop"], result["unit"], datetime.now().strftime("%H:%M:%S"), result["info"])
    elif result["type"] == '"Начало простоя"' or result["type"] == "Начало простоя":
        save_start_downtime(result["workshop"], result["unit"], datetime.now().strftime("%H:%M:%S"))
    elif result["type"] == "Устранение простоя" or result["type"] == "Устранение простоя":
        save_end_downtime(result["workshop"], result["unit"], datetime.now().strftime("%H:%M:%S"))
    return f'[Тип: {result["type"]}]\n[Цех: {result["workshop"]}]\n[Время: {datetime.now().strftime("%H:%M:%S")}]\n[Агрегат: {result["unit"]}]'

