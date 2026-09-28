"""Mock AI provider.

Produces intelligent-enough responses for demos and tests without
any external API. Real providers (Gemini, OpenAI) plug in later
by implementing the same interface.

Behavior:
- Looks at the last user message.
- Matches keywords for common scenarios (booking, hotel, restaurant, travel, etc.)
- Returns a helpful response using Platform-X's known data shapes.
- Falls back to a generic friendly reply.
"""

import re

from app.services.ai.provider import AIProvider, AIMessage, AIResponse


class MockProvider(AIProvider):
    """Deterministic mock AI provider for demos and tests."""

    name = "mock"

    def is_available(self) -> bool:
        return True

    def chat(
        self,
        messages: list[AIMessage],
        *,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AIResponse:
        """Return a keyword-based smart response."""
        last_user = ""
        for m in reversed(messages):
            if m.role == "user":
                last_user = m.content.strip()
                break

        reply = self._craft_reply(last_user)

        return AIResponse(
            content=reply,
            provider="mock",
            model="mock-v1",
            tokens_used=len(reply.split()),
            metadata={"matched_input": last_user[:120]},
        )

    def _craft_reply(self, text: str) -> str:
        """Match keywords and produce a helpful reply."""
        text_l = text.lower()

        # Greetings
        if not text_l or re.search(r"\b(hi|hello|hey|salam|مرحبا|سلام|kamusta)\b", text_l):
            return (
                "Hello! I'm your Platform-X assistant. I can help you:\n"
                "• Find hotels, restaurants, travel packages, or entertainment\n"
                "• Check your bookings or rewards\n"
                "• Discover partner businesses on the platform\n\n"
                "What would you like to do?"
            )

        # Booking
        if re.search(r"\b(book|booking|reserve|reservation|حجز|bumili)\b", text_l):
            return (
                "I can help you book! To get started, tell me:\n"
                "• The kind of experience (hotel / restaurant / travel / entertainment)\n"
                "• Your preferred date and location\n\n"
                "Or browse our categories directly to see all options."
            )

        # Hotels
        if re.search(r"\b(hotel|stay|room|فندق|hotel|kwarto)\b", text_l):
            return (
                "We have boutique, luxury, and business hotels across the platform.\n"
                "Popular choices include Trianon Royal Hotel, Azure Palm Resort, and Aurora Boutique.\n"
                "Visit /hotels to see all options with prices and photos."
            )

        # Restaurants
        if re.search(r"\b(restaurant|food|dinner|eat|مطعم|restawran)\b", text_l):
            return (
                "Great choice! Our restaurant partners include Saffron (Middle Eastern),\n"
                "Olive Grove (Mediterranean), and Sakura Sushi (Japanese).\n"
                "You can reserve a table or order food online — visit /restaurants."
            )

        # Travel
        if re.search(r"\b(travel|tour|flight|package|سفر|paglalakbay)\b", text_l):
            return (
                "Our travel partners offer city breaks, cultural tours, and full packages.\n"
                "Skyways Travel, Horizon Voyages, and Caravan Tours are popular choices.\n"
                "Visit /travel to explore."
            )

        # Entertainment
        if re.search(r"\b(entertainment|ticket|park|fun|ترفيه|libangan)\b", text_l):
            return (
                "For entertainment, try Oasis (family park), SkyPark (ziplines),\n"
                "Aqua World (waterpark), or Virtual Realm (VR).\n"
                "Visit /entertainment to see all options."
            )

        # Rewards
        if re.search(r"\b(reward|point|tier|loyalty|مكافأة|gantimpala)\b", text_l):
            return (
                "You earn points on every booking — across all businesses on the platform.\n"
                "Your points and tier are visible in your Account dashboard.\n"
                "Reach higher tiers (Silver, Gold, Platinum, Royal) for exclusive perks."
            )

        # Referrals
        if re.search(r"\b(refer|invite|friend|إحالة|kaibigan)\b", text_l):
            return (
                "You can refer friends from your Account page.\n"
                "Each successful referral earns you 100 points, and your friend earns 50.\n"
                "Find your personal referral code in your Account dashboard."
            )

        # Account
        if re.search(r"\b(account|profile|login|ماذا|حساب|account)\b", text_l):
            return (
                "Your Account dashboard shows all bookings, orders, rewards, and referrals.\n"
                "Sign in or create an account to get started."
            )

        # Business
        if re.search(r"\b(business|owner|partner|commercial|تجاري)\b", text_l):
            return (
                "Are you a business owner? Platform-X offers a dedicated Business Panel\n"
                "with services management, bookings inbox, customer list, and staff accounts.\n"
                "Apply at /partners/apply to get started."
            )

        # Default
        return (
            "I can help you discover and book hotels, restaurants, travel packages,\n"
            "and entertainment across Platform-X. Try asking:\n"
            "• \"Find a hotel in Dubai\"\n"
            "• \"Best restaurants in the platform\"\n"
            "• \"Show me travel packages\"\n"
            "• \"How do rewards work?\""
        )
