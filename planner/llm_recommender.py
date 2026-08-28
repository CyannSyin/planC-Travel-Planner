"""
LLM-based POI Recommendation Module.

"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv

# Resolve the project-level file independently of the caller's working directory.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class LLMRecommender:
    """LLM-based POI recommender.
    
    使用LLM根据城市、偏好等信息推荐POI，并估计游玩时间。
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """Initialize LLM recommender.
        
        Args:
            provider: LLM provider ('openai', 'aihubmix', 'anthropic', 'google')
            model: Model name (e.g., 'gpt-4', 'claude-3-opus-20240229')
            api_key: API key (if None, will read from environment)
            temperature: Temperature for generation (0.0-2.0)
        """
        self.provider = (provider or os.getenv("LLM_PROVIDER", "openai")).strip().lower()
        self.model = model or os.getenv("LLM_MODEL", "gpt-4")
        self.temperature = (
            temperature
            if temperature is not None
            else float(os.getenv("LLM_TEMPERATURE", "0.7"))
        )
        
        # Get API key
        if api_key:
            self.api_key = api_key
        else:
            # but allow a dedicated AIHUBMIX_API_KEY fallback.
            if self.provider == "aihubmix":
                self.api_key = os.getenv("AIHUBMIX_API_KEY") or os.getenv("OPENAI_API_KEY")
            elif self.provider == "openai":
                self.api_key = os.getenv("OPENAI_API_KEY")
            elif self.provider == "anthropic":
                self.api_key = os.getenv("ANTHROPIC_API_KEY")
            elif self.provider == "google":
                self.api_key = os.getenv("GOOGLE_API_KEY")
            else:
                self.api_key = None
        
        if not self.api_key:
            raise ValueError(
                f"API key not found for provider '{self.provider}'. "
                f"Please set the appropriate environment variable or pass api_key."
            )
        
        # Initialize client based on provider
        self.client = self._init_client()
    
    def _init_client(self):
        """Initialize LLM client based on provider."""
        # OpenAI-compatible providers share the same client and base URL behavior.
        if self.provider in {"openai", "aihubmix"}:
            from openai import OpenAI
            import httpx

            base_url = os.getenv("OPENAI_BASE_URL")
            if self.provider == "aihubmix" and not base_url:
                raise ValueError(
                    "OPENAI_BASE_URL is required when LLM_PROVIDER=aihubmix"
                )
            # 设置更长的超时时间（连接超时30秒，读取超时120秒）
            timeout = httpx.Timeout(30.0, connect=30.0, read=120.0)
            client_kwargs = {"api_key": self.api_key, "timeout": timeout}
            if base_url:
                client_kwargs["base_url"] = base_url
            return OpenAI(**client_kwargs)
        elif self.provider == "anthropic":
            try:
                import anthropic
                return anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "Anthropic package not installed. Install with: pip install anthropic"
                )
        elif self.provider == "google":
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                return genai.GenerativeModel(self.model)
            except ImportError:
                raise ImportError(
                    "Google Generative AI package not installed. "
                    "Install with: pip install google-generativeai"
                )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def recommend_pois(
        self,
        city: str,
        num_days: int = 3,
        preferences: Optional[str] = None,
        budget: Optional[str] = None,
        interests: Optional[List[str]] = None,
        num_pois: Optional[int] = None,
    ) -> pd.DataFrame:
        """Recommend POIs using LLM.
        
        Args:
            city: City name (e.g., "Chengdu", "Beijing")
            num_days: Number of travel days
            preferences: User preferences (e.g., "cultural sites", "nature")
            budget: Budget level (e.g., "budget", "mid-range", "luxury")
            interests: List of interests (e.g., ["museums", "parks", "food"])
            num_pois: Target number of POIs to recommend (default: num_days * 5-8)
        
        Returns:
            DataFrame with columns: poi_id, name, lat, lon, category, rating, 
            duration_min, popularity, opening_hours
        """
        if num_pois is None:
            num_pois = num_days * 6  # ~6 POIs per day
        
        # Build prompt
        prompt = self._build_recommendation_prompt(
            city=city,
            num_days=num_days,
            preferences=preferences,
            budget=budget,
            interests=interests,
            num_pois=num_pois,
        )
        
        # Call LLM
        response = self._call_llm(prompt)
        
        # Parse response to DataFrame
        pois_df = self._parse_llm_response(response, city)
        
        return pois_df
    
    def _build_recommendation_prompt(
        self,
        city: str,
        num_days: int,
        preferences: Optional[str],
        budget: Optional[str],
        interests: Optional[List[str]],
        num_pois: int,
    ) -> str:
        """Build prompt for LLM recommendation."""
        prompt_parts = [
            f"You are a travel planning expert. Recommend {num_pois} Points of Interest (POIs) "
            f"for a {num_days}-day trip to {city}.",
            "",
            "Requirements:",
            "1. Provide diverse POIs including attractions, museums, parks, restaurants, etc.",
            "2. Estimate realistic visit duration for each POI (in minutes)",
            "3. Provide ratings (1.0-5.0) based on popularity and quality",
            "4. Include approximate coordinates (latitude, longitude) for each POI",
            "5. Categorize each POI (e.g., 'tourism=attraction', 'tourism=museum', 'leisure=park')",
        ]
        
        if preferences:
            prompt_parts.append(f"6. User preferences: {preferences}")
        
        if budget:
            prompt_parts.append(f"7. Budget level: {budget}")
        
        if interests:
            prompt_parts.append(f"8. Interests: {', '.join(interests)}")
        
        prompt_parts.extend([
            "",
            "Output format (JSON array):",
            "[",
            "  {",
            '    "name": "POI Name",',
            '    "lat": 30.123456,',
            '    "lon": 104.123456,',
            '    "category": "tourism=attraction",',
            '    "rating": 4.5,',
            '    "duration_min": 120,',
            '    "popularity": 0.8,',
            '    "opening_hours": "09:00-18:00"',
            "  },",
            "  ...",
            "]",
            "",
            "Important:",
            "- Ensure coordinates are accurate for the city",
            "- Duration should be realistic (30-300 minutes typical)",
            "- Rating should reflect actual quality/popularity (1.0-5.0)",
            "- Popularity is a normalized score (0.0-1.0)",
            "- Return ONLY valid JSON, no additional text",
        ])
        
        return "\n".join(prompt_parts)
    
    def _call_llm(self, prompt: str, max_retries: int = 3, retry_delay: float = 2.0) -> str:
        """Call LLM API and return response with retry logic.
        
        Args:
            prompt: The prompt to send to LLM
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        
        Returns:
            LLM response text
        
        Raises:
            Exception: If all retry attempts fail
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if self.provider in {"openai", "aihubmix"}:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a helpful travel planning assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=self.temperature,
                    )
                    return response.choices[0].message.content
                
                elif self.provider == "anthropic":
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=4000,
                        temperature=self.temperature,
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                    )
                    return response.content[0].text
                
                elif self.provider == "google":
                    response = self.client.generate_content(
                        prompt,
                        generation_config={
                            "temperature": self.temperature,
                            "max_output_tokens": 4000,
                        }
                    )
                    return response.text
                
                else:
                    raise ValueError(f"Unsupported provider: {self.provider}")
                    
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # 检查是否是超时或连接错误（可重试的错误）
                is_retryable = any(keyword in error_str for keyword in [
                    'timeout', 'connect', 'connection', 'network', 
                    'handshake', 'temporarily unavailable', '503', '502', '504'
                ])
                
                if not is_retryable or attempt == max_retries - 1:
                    # 不可重试的错误或最后一次尝试，直接抛出
                    raise
                
                # 可重试的错误，等待后重试
                wait_time = retry_delay * (attempt + 1)  # 指数退避
                print(f"  ⚠️  API调用失败（尝试 {attempt + 1}/{max_retries}）: {type(e).__name__}")
                print(f"  ⏳ 等待 {wait_time:.1f} 秒后重试...")
                time.sleep(wait_time)
        
        # 如果所有重试都失败
        if last_error:
            raise last_error
        else:
            raise RuntimeError("Unexpected error: all retries exhausted but no error captured")
    
    def _parse_llm_response(self, response: str, city: str) -> pd.DataFrame:
        """Parse LLM JSON response into DataFrame."""
        # Extract JSON from response (handle cases where LLM adds extra text)
        response = response.strip()
        
        # Try to find JSON array in response
        start_idx = response.find('[')
        end_idx = response.rfind(']') + 1
        
        if start_idx == -1 or end_idx == 0:
            raise ValueError("No JSON array found in LLM response")
        
        json_str = response[start_idx:end_idx]
        
        try:
            pois_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from LLM response: {e}")
        
        # Convert to DataFrame
        pois_list = []
        for i, poi in enumerate(pois_data):
            if not isinstance(poi, dict):
                continue
            
            # Generate POI ID
            poi_id = f"llm_{city.lower()}_{i+1}"
            
            # Extract fields with defaults
            pois_list.append({
                "poi_id": poi_id,
                "name": poi.get("name", f"POI {i+1}"),
                "lat": float(poi.get("lat", 0.0)),
                "lon": float(poi.get("lon", 0.0)),
                "category": poi.get("category", "tourism=attraction"),
                "rating": float(poi.get("rating", 4.0)),
                "duration_min": float(poi.get("duration_min", 60.0)),
                "popularity": float(poi.get("popularity", 0.5)),
                "opening_hours": poi.get("opening_hours", ""),
            })
        
        if not pois_list:
            raise ValueError("No valid POIs found in LLM response")
        
        df = pd.DataFrame(pois_list)
        
        # Validate coordinates (should be reasonable for the city)
        # This is a basic check - in production, you might want more sophisticated validation
        if df["lat"].abs().max() > 90 or df["lon"].abs().max() > 180:
            raise ValueError("Invalid coordinates in LLM response")
        
        return df


def load_llm_recommended_pois(
    city: str,
    num_days: int = 3,
    preferences: Optional[str] = None,
    budget: Optional[str] = None,
    interests: Optional[List[str]] = None,
    num_pois: Optional[int] = None,
    cache_path: Optional[Path] = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Convenience function to load LLM-recommended POIs.
    
    Args:
        city: City name
        num_days: Number of travel days
        preferences: User preferences
        budget: Budget level
        interests: List of interests
        num_pois: Target number of POIs
        cache_path: Path to cache file (default: data/llm_pois_{city}.csv)
        use_cache: Whether to use cached results if available
    
    Returns:
        DataFrame with POI data
    """
    # Check cache
    if cache_path is None:
        cache_path = Path("data") / f"llm_pois_{city.lower().replace(' ', '_')}.csv"
    
    cache_path = Path(cache_path)
    
    if use_cache and cache_path.exists():
        print(f"Loading cached LLM recommendations from {cache_path}")
        return pd.read_csv(cache_path)
    
    # Get recommendations from LLM
    print(f"Requesting POI recommendations from LLM for {city}...")
    recommender = LLMRecommender()
    pois_df = recommender.recommend_pois(
        city=city,
        num_days=num_days,
        preferences=preferences,
        budget=budget,
        interests=interests,
        num_pois=num_pois,
    )
    
    # Save to cache
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    pois_df.to_csv(cache_path, index=False)
    print(f"Saved LLM recommendations to {cache_path}")
    
    return pois_df
