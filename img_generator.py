from diffusers import StableDiffusionPipeline
from googletrans import Translator
import torch
import time


# Проверяем доступность CUDA
device = "cuda" if torch.cuda.is_available() else "cpu"
# Оптимизации для CPU
torch_dtype = torch.float32 if device == "cpu" else torch.float16

model = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch_dtype,
    safety_checker=None,
    requires_safety_checker=False
).to(device)

# Включаем оптимизации для CPU
if device == "cpu":
    model.enable_attention_slicing()  # Экономит память

translator = Translator()


def generate_image(russian_prompt, style="реализм", num_inference_steps=20, save_image=True):
    # Генерирует изображение из русского текстового запроса

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
        translation = translator.translate(full_prompt, src='ru', dest='en')
        english_prompt = translation.text
    except Exception as e:
        english_prompt = full_prompt

    start_time = time.time()

    # Генерация изображения с оптимизированными параметрами
    with torch.inference_mode():
        image = model(
            english_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=7.5,
            height=512,
            width=512
        ).images[0]

    generation_time = time.time() - start_time
    print(f"Время генерации: {generation_time:.1f} сек")

    # Сохраняем изображение
    if save_image:
        filename = f"output_{hash(russian_prompt) % 10000}.png"
        image.save(filename)
        print(f"Изображение сохранено как: {filename}")

    return image



# тестирование
if __name__ == "__main__":
    image1 = generate_image("красивый закат", "фэнтези")



