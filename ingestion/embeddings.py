"""
Embedding generation module.

Note: Anthropic does not provide embeddings API yet.
This module uses OpenAI embeddings as the standard choice for RAG systems.
Alternative: You can use Voyage AI or local models like sentence-transformers.
"""

from typing import List
import os


class EmbeddingGenerator:
    """
    Generate embeddings for text chunks.

    For now, this is a placeholder. You have three options:

    Option 1 (Recommended): Use OpenAI embeddings
    - Add OPENAI_API_KEY to your .env file
    - Uncomment the OpenAI implementation below

    Option 2: Use Voyage AI embeddings (recommended by Anthropic)
    - Sign up at https://www.voyageai.com/
    - Use their API for embeddings

    Option 3: Use local embeddings (no API key needed)
    - Use sentence-transformers library
    - Slower but free
    """

    def __init__(self, provider: str = "openai"):
        """
        Initialize embedding generator.

        Args:
            provider: Either 'openai', 'voyage', or 'local'
        """
        self.provider = provider

        if provider == "openai":
            self._init_openai()
        elif provider == "voyage":
            self._init_voyage()
        elif provider == "local":
            self._init_local()
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _init_openai(self):
        """Initialize OpenAI embeddings."""
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            self.client = OpenAI(api_key=api_key)
            self.model = "text-embedding-3-small"
            print(f"Initialized OpenAI embeddings with model: {self.model}")
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")

    def _init_voyage(self):
        """Initialize Voyage AI embeddings."""
        try:
            import voyageai
            api_key = os.getenv("VOYAGE_API_KEY")
            if not api_key:
                raise ValueError("VOYAGE_API_KEY not found in environment")
            self.client = voyageai.Client(api_key=api_key)
            self.model = "voyage-2"
            print(f"Initialized Voyage AI embeddings with model: {self.model}")
        except ImportError:
            raise ImportError("VoyageAI package not installed. Run: pip install voyageai")

    def _init_local(self):
        """Initialize local sentence-transformers embeddings."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("Initialized local embeddings with sentence-transformers")
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. Run: pip install sentence-transformers"
            )

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector as list of floats
        """
        if self.provider == "openai":
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding

        elif self.provider == "voyage":
            result = self.client.embed([text], model=self.model)
            return result.embeddings[0]

        elif self.provider == "local":
            embedding = self.model.encode(text)
            return embedding.tolist()

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        if self.provider == "openai":
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [item.embedding for item in response.data]

        elif self.provider == "voyage":
            result = self.client.embed(texts, model=self.model)
            return result.embeddings

        elif self.provider == "local":
            embeddings = self.model.encode(texts)
            return [emb.tolist() for emb in embeddings]


# Example usage
if __name__ == "__main__":
    # Test with local embeddings (no API key required)
    generator = EmbeddingGenerator(provider="local")

    test_text = "SafetyPay is a payment provider in Latin America"
    embedding = generator.generate_embedding(test_text)

    print(f"Generated embedding of dimension: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")
