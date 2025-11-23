# img_generator.py
import time

# Глобальные переменные для ленивой инициализации
_model = None
_device = None
_translator = None


def _initialize_model():
    """Инициализирует модель только при первом вызове"""
    global _model, _device, _translator

    if _model is not None:
        return

    # ОТЛОЖЕННЫЙ ИМПОРТ - решает проблему
    from diffusers import StableDiffusionPipeline
    from googletrans import Translator
    import torch

    # Проверяем доступность CUDA
    _device = "cuda" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float32 if _device == "cpu" else torch.float16

    _model = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=torch_dtype,
        safety_checker=None,
        requires_safety_checker=False
    ).to(_device)

    # Включаем оптимизации для CPU
    if _device == "cpu":
        _model.enable_attention_slicing()

    _translator = Translator()


def generate_image(russian_prompt, style="реализм", num_inference_steps=20, save_image=True):
    # Генерирует изображение из русского текстового запроса

    # Инициализируем модель при первом вызове
    _initialize_model()

    # Стили для улучшения качества
    styles = {
        "реализм": ", realistic, highly detailed, professional photography",
        "фэнтези": ", fantasy art, magical, epic, digital painting",
        "аниме": ", anime style, vibrant colors, Japanese animation",
        "цифровое искусство": ", digital art, concept art, detailed",
        "масляная живопись": ", oil painting, brush strokes, artistic",
        "быстрый": ", simple sketch"
    }

    # Добавляем стиль
    style_suffix = styles.get(style, "")
    full_prompt = russian_prompt + style_suffix

    # Автоматический перевод
    try:
        translation = _translator.translate(full_prompt, src='ru', dest='en')
        english_prompt = translation.text
    except Exception as e:
        english_prompt = full_prompt

    start_time = time.time()

    # Генерация изображения с оптимизированными параметрами
    import torch
    with torch.inference_mode():
        image = _model(
            english_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=7.5,
            height=512,
            width=512
        ).images[0]

    generation_time = time.time() - start_time
    # print(f"Время генерации: {generation_time:.1f} сек")

    # Сохраняем изображение
    if save_image:
        filename = f"output_{hash(russian_prompt) % 10000}.png"
        image.save(filename)
        # print(f"Изображение сохранено как: {filename}")

    return image


# тестирование
if __name__ == "__main__":
    image1 = generate_image("красивый закат", "фэнтези")