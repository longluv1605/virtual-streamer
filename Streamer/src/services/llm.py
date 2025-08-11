import os
import aiohttp
import openai
from openai import AsyncOpenAI
from typing import Optional

from src.models import Product, ScriptTemplate

from dotenv import load_dotenv
load_dotenv()


class LLMService:
    """Service for LLM integration (OpenAI/Gemini)"""

    def __init__(self, provider: str = "openai", api_key: Optional[str] = None):
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv(
            "OPENAI_API_KEY" if provider == "openai" else "GEMINI_API_KEY"
        )

        if self.provider == "openai":
            if self.api_key:
                # Initialize OpenAI client following best practices
                self.openai_client = AsyncOpenAI(
                    api_key=self.api_key,
                    timeout=30.0,  # 30 second timeout
                    max_retries=2,  # Retry failed requests twice
                )
            else:
                self.openai_client = None
                print(
                    "Warning: OpenAI API key not found. LLM features will use fallback scripts."
                )
                print("To use OpenAI, set the OPENAI_API_KEY environment variable.")
        else:
            self.openai_client = None

    async def generate_product_script(
        self,
        product: Product,
        template: ScriptTemplate,
        additional_context: Optional[str] = None,
    ) -> str:
        """Generate product presentation script using LLM"""

        # Prepare prompt
        prompt = self._create_prompt(product, template, additional_context)

        try:
            if self.provider == "openai":
                return await self._generate_openai(prompt)
            elif self.provider == "gemini":
                return await self._generate_gemini(prompt)
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")
        except Exception as e:
            print(f"Error generating script: {e}")
            return self._fallback_script(product, template)

    def _create_prompt(
        self, product: Product, template: ScriptTemplate, additional_context: str
    ) -> str:
        """Create prompt for LLM"""

        context = f"""
Bạn là một người bán hàng livestream chuyên nghiệp, nhiệt tình và có kinh nghiệm. 
Hãy tạo một đoạn script để giới thiệu sản phẩm một cách hấp dẫn, thuyết phục và tự nhiên.

Thông tin sản phẩm:
- Tên: {product.name}
- Mô tả: {product.description or "Không có mô tả"}
- Giá: {product.price:,.0f} VNĐ
- Danh mục: {product.category or "Không xác định"}
- Số lượng trong kho: {product.stock_quantity}

Template cơ bản:
{template.template}

Yêu cầu:
1. Script phải tự nhiên, không quá dài (khoảng 10-20 giây khi đọc)
2. Sử dụng ngôn ngữ thân thiện, gần gũi
3. Tạo cảm giác khan hiếm và khẩn cấp phù hợp
4. Khuyến khích tương tác từ khán giả
5. Kết thúc bằng call-to-action rõ ràng

{f"Bối cảnh thêm: {additional_context}" if additional_context else ""}

Hãy tạo script hoàn chỉnh dựa trên template và thông tin trên:
"""
        return context

    async def _generate_openai(self, prompt: str) -> str:
        """Generate using OpenAI API"""
        if not self.openai_client:
            raise Exception(
                "OpenAI client not initialized. Please set OPENAI_API_KEY environment variable."
            )

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Bạn là chuyên gia viết script livestream bán hàng chuyên nghiệp. Hãy tạo script hấp dẫn, tự nhiên và thuyết phục.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=800,
                temperature=0.7,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )

            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content:
                    return content.strip()
                else:
                    raise Exception("Empty response from OpenAI")
            else:
                raise Exception("No choices returned from OpenAI")

        except openai.RateLimitError as e:
            print(f"OpenAI Rate limit exceeded: {e}")
            raise Exception("Rate limit exceeded. Please try again later.")
        except openai.APIConnectionError as e:
            print(f"OpenAI API connection error: {e}")
            raise Exception("Failed to connect to OpenAI API.")
        except openai.AuthenticationError as e:
            print(f"OpenAI Authentication error: {e}")
            raise Exception("Invalid OpenAI API key.")
        except Exception as e:
            print(f"OpenAI API error: {e}")
            raise

    async def _generate_gemini(self, prompt: str) -> str:
        """Generate using Gemini API"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.api_key}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 800},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                else:
                    raise Exception(f"Gemini API error: {response.status}")

    def _fallback_script(self, product: Product, template: ScriptTemplate) -> str:
        """Fallback script if LLM fails"""

        script = template.template.format(
            product_name=product.name,
            product_description=product.description or "Sản phẩm chất lượng cao",
            price=f"{product.price:,.0f}",
            stock_quantity=product.stock_quantity,
            features="Chất lượng cao, thiết kế đẹp, giá cả hợp lý",
            benefit_1="Tiết kiệm thời gian",
            benefit_2="Chất lượng đảm bảo",
            benefit_3="Giá cả cạnh tranh",
            detailed_description=product.description
            or "Sản phẩm được thiết kế với công nghệ hiện đại",
            comparison="Tính năng vượt trội và giá cả hợp lý hơn",
        )

        return script
