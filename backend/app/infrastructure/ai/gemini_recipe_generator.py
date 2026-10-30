import logging

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from app.application.dto.recipe_dto import (
    RecipeSuggestionSchema,
    RecipeSuggestionsResponse,
    RecipeGenerationSchema,
)
from app.application.exceptions import (
    AIProviderRateLimitError,
    AIProviderUnavailableError,
    AIProviderInvalidResponseError,
)
from app.application.interfaces.recipe_generator import RecipeGenerator
from app.domain.entities.product import Product
from app.infrastructure.ai.rate_limiter import InMemoryGeminiRateLimiter


logger = logging.getLogger(__name__)


class GeminiRecipeGenerator(RecipeGenerator):

    SYSTEM_INSTRUCTION = """
    Ти — професійний кулінарний помічник.

    Усі текстові значення у відповідях повинні бути
    виключно українською мовою.

    Не використовуй російську, англійську або інші мови
    у назвах страв, описах, інгредієнтах та інструкціях.

    Відповідай відповідно до переданої JSON-схеми.
    Не додавай Markdown або текст поза JSON.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        rate_limiter: InMemoryGeminiRateLimiter,
    ) -> None:
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(
                    attempts=1,
                ),
            ),
        )

        self.aio = self.client.aio
        self.model = model
        self.rate_limiter = rate_limiter

    async def _generate_content(
        self,
        prompt: str,
        response_schema: type,
        max_output_tokens: int,
    ):
        await self.rate_limiter.acquire()

        try:
            return await self.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    max_output_tokens=max_output_tokens,
                ),
            )

        except errors.APIError as exc:
            if exc.code == 429:
                logger.warning("Gemini API rate limit reached.")
                raise AIProviderRateLimitError() from exc

            logger.exception(
                "Gemini API error. Status code: %s",
                exc.code,
            )
            raise AIProviderUnavailableError() from exc

        except Exception as exc:
            logger.exception("Unexpected Gemini API error.")
            raise AIProviderUnavailableError() from exc

    @staticmethod
    def _parse_response(response, schema: type):
        try:
            if response.parsed is not None:
                return schema.model_validate(response.parsed)

            if response.text:
                return schema.model_validate_json(response.text)

        except ValidationError as exc:
            logger.exception("Gemini returned invalid structured data.")
            raise AIProviderInvalidResponseError() from exc

        raise AIProviderInvalidResponseError()

    async def suggest_recipes(
        self,
        products: list[Product]
    ) -> RecipeSuggestionsResponse:

        product_list = "\n".join(
            f"ID: {product.id}, назва: {product.name}"
            for product in products
        )

        prompt = f"""
        Користувач обрав такі продукти:

        {product_list}

        Твоє завдання — запропонувати від 1 до 8
        різних страв, які можна приготувати з цих продуктів.

        ОБОВ'ЯЗКОВІ ПРАВИЛА:

        1. Кожна страва повинна використовувати щонайменше
           2 різні продукти із наданого списку.

        2. Насамперед пропонуй рецепти, які використовують
           максимальну кількість обраних продуктів.

        3. Бажано, щоб перші рецепти використовували
           всі обрані продукти, якщо це кулінарно доречно.

        4. Не створюй штучні комбінації продуктів,
           які кулінарно не поєднуються.

        5. Якщо з наданих продуктів неможливо приготувати
           жодної доречної та реалістичної страви, поверни
           порожній список recipes.

        6. Не вигадуй рецепти лише для того, щоб заповнити список.

        7. Далі можна пропонувати рецепти, які використовують
           меншу кількість обраних продуктів, але не менше двох.

        8. Пропонуй різні страви, а не декілька незначних
           варіацій однієї й тієї самої страви.

        9. Не використовуй продукти, яких немає у списку,
           як основні інгредієнти. Дозволені звичайні
           додаткові продукти на кшталт солі, перцю,
           води та олії.

        10. used_product_ids повинен містити тільки ID
           тих обраних продуктів, які справді входять
           до конкретної страви.

        11. Не вигадуй ID. Використовуй лише надані ID.

        12. Поверни тільки назву, короткий опис,
            час приготування та used_product_ids.
            Не створюй детальні інструкції.

        13. Усі текстові поля повинні бути українською мовою.

        Поверни не більше 8 різних рецептів.
        """

        response = await self._generate_content(
            prompt=prompt,
            response_schema=RecipeSuggestionsResponse,
            max_output_tokens=3000,
        )

        return self._parse_response(
            response,
            RecipeSuggestionsResponse,
        )

    async def generate_full_recipe(
        self,
        suggestion: RecipeSuggestionSchema,
        products: list[Product]
    ) -> RecipeGenerationSchema:

        product_list = "\n".join(
            f"- {product.name}"
            for product in products
        )

        prompt = f"""
        Користувач обрав рецепт:

        Назва: {suggestion.title}
        Опис: {suggestion.description}
        Орієнтовний час: {suggestion.cooking_time} хвилин.

        Обов'язкові продукти:

        {product_list}

        Створи повноцінний рецепт цієї страви.

        ОБОВ'ЯЗКОВІ ПРАВИЛА:

        1. Збережи задум та назву обраної страви.
        2. Використай усі передані продукти.
        3. Вкажи точні кількості інгредієнтів
           та одиниці вимірювання.
        4. Можеш додавати базові додаткові інгредієнти,
           наприклад сіль, перець, олію та спеції.
        5. Створи детальну послідовну інструкцію
           приготування.
        6. Час приготування вкажи цілим числом хвилин.
        7. Усі текстові значення повинні бути українською мовою.
        """

        response = await self._generate_content(
            prompt=prompt,
            response_schema=RecipeGenerationSchema,
            max_output_tokens=4096,
        )

        return self._parse_response(
            response,
            RecipeGenerationSchema,
        )

    async def close(self) -> None:
        await self.aio.aclose()