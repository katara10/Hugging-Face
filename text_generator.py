from openai import OpenAI
import time
from datetime import datetime
import requests
import json
import sys
import types

cgi_module = types.ModuleType('cgi')
cgi_module.parse_header = lambda x: ('text/plain', {})
cgi_module.MiniFieldStorage = type('MiniFieldStorage', (), {})
cgi_module.parse_multipart = None
sys.modules['cgi'] = cgi_module

httpcore_module = types.ModuleType('httpcore')
httpcore_module.SyncHTTPTransport = type('SyncHTTPTransport', (), {})
httpcore_module.AsyncHTTPTransport = type('AsyncHTTPTransport', (), {})
sys.modules['httpcore'] = httpcore_module

from googletrans import Translator

class AdvancedSmolLM3:
    def __init__(self, api_keys=None):
        if api_keys is None:
            api_keys = [
                "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",
                "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",
                "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",
                "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",
                "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",
                "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",
                "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"
            ]

        self.api_keys = api_keys
        self.key_usage = {key: {'last_used': None, 'error_count': 0} for key in api_keys}
        self.current_key_index = 0
        self.max_retries = len(api_keys)
        self.model = "HuggingFaceTB/SmolLM3-3B"
        self.translator = Translator()
        self.api_base = "https://router.huggingface.co/v1"

    def get_best_key(self):
        """Выбирает лучший ключ на основе истории использования"""
        current_key = self.api_keys[self.current_key_index]
        if self.key_usage[current_key]['error_count'] == 0:
            return current_key

        best_key = min(self.api_keys,
                       key=lambda k: (self.key_usage[k]['error_count'],
                                      self.key_usage[k]['last_used'] or datetime.min))

        self.current_key_index = self.api_keys.index(best_key)
        return best_key

    def mark_key_error(self, key):
        """Отмечаем ошибку для ключа"""
        self.key_usage[key]['error_count'] += 1
        self.key_usage[key]['last_used'] = datetime.now()

    def mark_key_success(self, key):
        """Отмечаем успешное использование ключа"""
        self.key_usage[key]['last_used'] = datetime.now()
        if self.key_usage[key]['error_count'] > 0:
            self.key_usage[key]['error_count'] -= 1

    def rotate_key(self):
        """Переключаем на следующий ключ"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)

    def detect_language(self, text):
        try:
            detection = self.translator.detect(text)
            return detection.lang
        except:
            return 'en'

    def clean_response(self, text):
        """Очищает ответ от тегов <think> и английского текста"""
        import re
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            russian_chars = len([c for c in line if '\u0400' <= c <= '\u04FF'])
            total_chars = len([c for c in line if c.isalpha()])

            if total_chars == 0:
                cleaned_lines.append(line)
            elif russian_chars / total_chars > 0.3:
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines).strip()

    def query_huggingface(self, prompt, api_key, max_tokens=2500):
        """Прямой запрос к Hugging Face API"""
        try:
            client = OpenAI(
                base_url=self.api_base,
                api_key=api_key,
            )

            completion = client.chat.completions.create(
                model=self.model,
                messages=prompt,
                max_tokens=max_tokens,
                temperature=0.6,
            )

            if completion.choices and len(completion.choices) > 0:
                return completion.choices[0].message.content
            else:
                raise Exception("Пустой ответ от модели")
        except Exception as e:
            raise Exception(f"HuggingFace API error: {str(e)}")


    def ask(self, question, thinking=False, max_tokens=2500):
        retries = 0

        while retries < self.max_retries:
            current_key = self.get_best_key()

            try:
                question_language = self.detect_language(question)

                system_msg = """Ты - русскоязычный ассистент. Отвечай ТОЛЬКО на русском языке.
Запрещено:
- Использовать теги <think> или любые другие XML-теги
- Писать на английском языке
- Включать внутренние размышления в ответ
- Использовать markdown разметку

Отвечай четко, ясно и по делу на русском языке."""

                if thinking:
                    system_msg += " Объясни свои рассуждения шаг за шагом на русском языке."

                # Формируем полный промпт

                full_prompt = [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": question}
                ]

                # Используем прямой запрос к Hugging Face
                response_text = self.query_huggingface(full_prompt, current_key, max_tokens)

                if not response_text:
                    raise Exception("Пустой ответ от модели")

                cleaned_response = self.clean_response(response_text)
                self.mark_key_success(current_key)

                if question_language != 'en':
                    if self.detect_language(cleaned_response) != question_language:
                        translated_response = self.translator.translate(cleaned_response, dest=question_language).text
                        return translated_response
                    return cleaned_response
                else:
                    return cleaned_response

            except Exception as e:
                error_msg = str(e)
                print(f"Ошибка с ключом {current_key[:10]}...: {error_msg}")
                self.mark_key_error(current_key)

                if "rate limit" in error_msg.lower() or "quota" in error_msg.lower() or "429" in error_msg:
                    retries += 1
                    if retries < self.max_retries:
                        time.sleep(2)
                        self.rotate_key()
                else:
                    # Для других ошибок сразу пробуем следующий ключ
                    retries += 1
                    if retries < self.max_retries:
                        time.sleep(1)
                        self.rotate_key()

        return "Ошибка: Все ключи исчерпали лимит запросов или произошла ошибка"


# Функция для импорта в другие файлы
def get_ai_text(question, thinking=True, api_keys=None):
    if api_keys is None:
        api_keys = [
            "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",
            "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",
            "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",
            "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",
            "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",
            "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",
            "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"
        ]

    model = AdvancedSmolLM3(api_keys)
    return model.ask(question, thinking=thinking)


# Тестирование
if __name__ == "__main__":
    print(get_ai_text("что такое искусственный интеллект?"))