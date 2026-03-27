import json
import logging
import time
from typing import Any

import httpx

from cortex.extensions.x_intelligence.models import XSearchResponse, XTweet, XUser

LOG = logging.getLogger("cortex.extensions.x_intelligence.client")

BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNw%2FGrCW9kvD7REET7JlSp9qYI%3DQ"

GQL_CONF = {
    "SearchTimeline": {
        "queryId": "rkp6b4vtR9u7v3naGoOzUQ",
        "features": {"rweb_video_screen_enabled":False,"profile_label_improvements_pcf_label_in_post_enabled":True,"responsive_web_profile_redirect_enabled":False,"rweb_tipjar_consumption_enabled":False,"verified_phone_label_enabled":False,"creator_subscriptions_tweet_preview_api_enabled":True,"responsive_web_graphql_timeline_navigation_enabled":True,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":False,"premium_content_api_read_enabled":False,"communities_web_enable_tweet_community_results_fetch":True,"c9s_tweet_anatomy_moderator_badge_enabled":True,"responsive_web_grok_analyze_button_fetch_trends_enabled":False,"responsive_web_grok_analyze_post_followups_enabled":True,"responsive_web_jetfuel_frame":True,"responsive_web_grok_share_attachment_enabled":True,"responsive_web_grok_annotations_enabled":True,"articles_preview_enabled":True,"responsive_web_edit_tweet_api_enabled":True,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":True,"view_counts_everywhere_api_enabled":True,"longform_notetweets_consumption_enabled":True,"responsive_web_twitter_article_tweet_consumption_enabled":True,"tweet_awards_web_tipping_enabled":False,"content_disclosure_indicator_enabled":True,"content_disclosure_ai_generated_indicator_enabled":True,"responsive_web_grok_show_grok_translated_post":False,"responsive_web_grok_analysis_button_from_backend":True,"post_ctas_fetch_enabled":True,"freedom_of_speech_not_reach_fetch_enabled":True,"standardized_nudges_misinfo":True,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":True,"longform_notetweets_rich_text_read_enabled":True,"longform_notetweets_inline_media_enabled":False,"responsive_web_grok_image_annotation_enabled":True,"responsive_web_grok_imagine_annotation_enabled":True,"responsive_web_grok_community_note_auto_translation_is_enabled":False,"responsive_web_enhance_cards_enabled":False}
    },
    "UserByScreenName": {
        "queryId": "IGgvgiOx4QZndDHuD3x9TQ",
        "features": {"hidden_profile_subscriptions_enabled":True,"profile_label_improvements_pcf_label_in_post_enabled":True,"responsive_web_profile_redirect_enabled":False,"rweb_tipjar_consumption_enabled":False,"verified_phone_label_enabled":False,"subscriptions_verification_info_is_identity_verified_enabled":True,"subscriptions_verification_info_verified_since_enabled":True,"highlights_tweets_tab_ui_enabled":True,"responsive_web_twitter_article_notes_tab_enabled":True,"subscriptions_feature_can_gift_premium":True,"creator_subscriptions_tweet_preview_api_enabled":True,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":False,"responsive_web_graphql_timeline_navigation_enabled":True}
    },
    "UserTweets": {
        "queryId": "O0epvwaQPUx-bT9YlqlL6w",
        "features": {"rweb_video_screen_enabled":False,"profile_label_improvements_pcf_label_in_post_enabled":True,"responsive_web_profile_redirect_enabled":False,"rweb_tipjar_consumption_enabled":False,"verified_phone_label_enabled":False,"creator_subscriptions_tweet_preview_api_enabled":True,"responsive_web_graphql_timeline_navigation_enabled":True,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":False,"premium_content_api_read_enabled":False,"communities_web_enable_tweet_community_results_fetch":True,"c9s_tweet_anatomy_moderator_badge_enabled":True,"responsive_web_grok_analyze_button_fetch_trends_enabled":False,"responsive_web_grok_analyze_post_followups_enabled":False,"responsive_web_jetfuel_frame":True,"responsive_web_grok_share_attachment_enabled":True,"responsive_web_grok_annotations_enabled":True,"articles_preview_enabled":True,"responsive_web_edit_tweet_api_enabled":True,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":True,"view_counts_everywhere_api_enabled":True,"longform_notetweets_consumption_enabled":True,"responsive_web_twitter_article_tweet_consumption_enabled":True,"tweet_awards_web_tipping_enabled":False,"content_disclosure_indicator_enabled":True,"content_disclosure_ai_generated_indicator_enabled":True,"responsive_web_grok_show_grok_translated_post":False,"responsive_web_grok_analysis_button_from_backend":True,"post_ctas_fetch_enabled":False,"freedom_of_speech_not_reach_fetch_enabled":True,"standardized_nudges_misinfo":True,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":True,"longform_notetweets_rich_text_read_enabled":True,"longform_notetweets_inline_media_enabled":False,"responsive_web_grok_image_annotation_enabled":True,"responsive_web_grok_imagine_annotation_enabled":True,"responsive_web_grok_community_note_auto_translation_is_enabled":False,"responsive_web_enhance_cards_enabled":False}
    },
    "ExplorePage": {
        "queryId": "0ocOmOo8rQuZCkxCg7Bs7w",
        "features": {"rweb_video_screen_enabled":False,"profile_label_improvements_pcf_label_in_post_enabled":True,"responsive_web_profile_redirect_enabled":False,"rweb_tipjar_consumption_enabled":False,"verified_phone_label_enabled":False,"responsive_web_graphql_timeline_navigation_enabled":True,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":False,"creator_subscriptions_tweet_preview_api_enabled":True,"premium_content_api_read_enabled":False,"communities_web_enable_tweet_community_results_fetch":True,"c9s_tweet_anatomy_moderator_badge_enabled":True,"responsive_web_grok_analyze_button_fetch_trends_enabled":False,"responsive_web_grok_analyze_post_followups_enabled":False,"responsive_web_jetfuel_frame":True,"responsive_web_grok_share_attachment_enabled":True,"responsive_web_grok_annotations_enabled":True,"articles_preview_enabled":True,"responsive_web_edit_tweet_api_enabled":True,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":True,"view_counts_everywhere_api_enabled":True,"longform_notetweets_consumption_enabled":True,"responsive_web_twitter_article_tweet_consumption_enabled":True,"tweet_awards_web_tipping_enabled":False,"content_disclosure_indicator_enabled":True,"content_disclosure_ai_generated_indicator_enabled":True,"responsive_web_grok_show_grok_translated_post":False,"responsive_web_grok_analysis_button_from_backend":True,"post_ctas_fetch_enabled":False,"freedom_of_speech_not_reach_fetch_enabled":True,"standardized_nudges_misinfo":True,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":True,"longform_notetweets_rich_text_read_enabled":True,"longform_notetweets_inline_media_enabled":False,"responsive_web_grok_image_annotation_enabled":True,"responsive_web_grok_imagine_annotation_enabled":True,"responsive_web_grok_community_note_auto_translation_is_enabled":False,"responsive_web_enhance_cards_enabled":False}
    }
}


class XIntelligenceClient:
    """Forensic-Grade X GraphQL Client."""

    def __init__(self, proxy: str | None = None):
        self.client = httpx.AsyncClient(proxy=proxy, timeout=30.0)
        self.guest_token: str | None = None
        self.token_expiry: float = 0
        self.user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )

    async def _activate_guest_token(self) -> str:
        if self.guest_token and time.time() < self.token_expiry:
            return self.guest_token

        LOG.info("🔑 [X] Activating new guest token...")
        headers = {
            "Authorization": f"Bearer {BEARER_TOKEN}",
            "User-Agent": self.user_agent,
        }
        res = await self.client.post("https://api.twitter.com/1.1/guest/activate.json", headers=headers)
        if res.status_code != 200:
            raise Exception(f"Token activation failed: {res.status_code}")

        data = res.json()
        self.guest_token = data["guest_token"]
        self.token_expiry = time.time() + 15 * 60  # 15 mins
        return self.guest_token

    async def _graphql_fetch(self, operation: str, variables: dict[str, Any]) -> Any:
        token = await self._activate_guest_token()
        config = GQL_CONF[operation]
        query_id = config["queryId"]

        params = {
            "variables": json.dumps(variables),
            "features": json.dumps(config["features"]),
        }

        url = f"https://x.com/i/api/graphql/{query_id}/{operation}"
        headers = {
            "Authorization": f"Bearer {BEARER_TOKEN}",
            "x-guest-token": token,
            "content-type": "application/json",
            "Referer": "https://x.com/",
            "User-Agent": self.user_agent,
        }

        res = await self.client.get(url, params=params, headers=headers)
        if res.status_code == 429:
            self.guest_token = None
            raise Exception("X rate limit exceeded (429)")

        if res.status_code != 200:
            raise Exception(f"X GraphQL failed [{res.status_code}]: {res.text[:100]}")

        return res.json()

    async def search(self, query: str, limit: int = 20) -> XSearchResponse:
        """Execute forensic search query."""
        variables = {
            "rawQuery": query,
            "count": limit,
            "querySource": "typed_query",
            "product": "Latest",
        }
        data = await self._graphql_fetch("SearchTimeline", variables)

        instructions = data.get("data", {}).get("search_by_raw_query", {}).get("search_timeline", {}).get("timeline", {}).get("instructions", [])
        add_entries = next((i for i in instructions if i.get("type") == "TimelineAddEntries"), {})
        entries = add_entries.get("entries", [])

        tweets = []
        for entry in entries:
            content = entry.get("content", {})
            if content.get("entryType") != "TimelineTimelineItem":
                continue

            result = content.get("itemContent", {}).get("tweet_results", {}).get("result", {})
            legacy = result.get("legacy") or result.get("tweet", {}).get("legacy")
            if not legacy:
                continue

            # Parse user
            core = result.get("core") or result.get("tweet", {}).get("core")
            user_results = core.get("user_results", {}).get("result", {})
            user_legacy = user_results.get("legacy", {})

            user = XUser(
                rest_id=user_results.get("rest_id", ""),
                id_str=user_legacy.get("id_str", ""),
                name=user_legacy.get("name", "Unknown"),
                screen_name=user_legacy.get("screen_name", "unknown"),
                description=user_legacy.get("description", ""),
                followers_count=user_legacy.get("followers_count", 0),
                friends_count=user_legacy.get("friends_count", 0),
                is_blue_verified=user_results.get("is_blue_verified", False),
                raw_data=user_results
            )

            tweet = XTweet(
                rest_id=legacy.get("id_str", ""),
                id_str=legacy.get("id_str", ""),
                full_text=legacy.get("full_text", ""),
                created_at=legacy.get("created_at", ""),
                user_id_str=legacy.get("user_id_str", ""),
                user=user,
                retweet_count=legacy.get("retweet_count", 0),
                favorite_count=legacy.get("favorite_count", 0),
                reply_count=legacy.get("reply_count", 0),
                quote_count=legacy.get("quote_count", 0),
                raw_data=result
            )
            tweets.append(tweet)

        return XSearchResponse(query=query, tweets=tweets)

    async def get_user_by_screen_name(self, screen_name: str) -> XUser | None:
        """Fetch user by handle."""
        variables = {"screen_name": screen_name, "withSafetyModeUserFields": True}
        data = await self._graphql_fetch("UserByScreenName", variables)

        result = data.get("data", {}).get("user", {}).get("result", {})
        if not result or result.get("__typename") != "User":
            return None

        legacy = result.get("legacy", {})
        return XUser(
            rest_id=result.get("rest_id", ""),
            id_str=legacy.get("id_str", ""),
            name=legacy.get("name", ""),
            screen_name=legacy.get("screen_name", ""),
            description=legacy.get("description", ""),
            followers_count=legacy.get("followers_count", 0),
            friends_count=legacy.get("friends_count", 0),
            is_blue_verified=result.get("is_blue_verified", False),
            raw_data=result
        )

    async def close(self):
        await self.client.aclose()
