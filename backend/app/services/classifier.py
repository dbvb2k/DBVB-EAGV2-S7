import numpy as np
import logging
from typing import Dict, List, Any, Tuple
from app.services.embedding import get_embedding, normalize_embedding

logger = logging.getLogger(__name__)


def _build_category_prototypes(categories: List[str], user_prefs: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """Create prototype embeddings for each category using name + description + keywords + user examples."""
    prototypes: Dict[str, np.ndarray] = {}

    # Defaults (can be extended via user_prefs)
    default_descriptions: Dict[str, str] = {
        'Sports': 'Sports, games, match, team, league, tournament, olympics, athletes',
        'Politics': 'Politics, government, election, policy, parliament, president, senate',
        'Financial': 'Finance, markets, stocks, investment, banking, economy, trading',
        'Health & Medical': 'Healthcare, medical, disease, treatment, clinical, patient, hospital',
        'Current Affairs': 'News, breaking, update, current events, announcement, report',
        'Technology': 'Technology, software, hardware, AI, programming, cybersecurity, data, internet',
        'Others': 'General content that does not fit the other categories'
    }

    category_overrides: Dict[str, Dict[str, Any]] = (user_prefs or {}).get('category_overrides', {})
    feedback_examples: Dict[str, List[Dict[str, str]]] = (user_prefs or {}).get('category_feedback', {})
    
    total_feedback_examples = sum(len(examples) for examples in feedback_examples.values())
    logger.info(f"Building prototypes for {len(categories)} categories with {total_feedback_examples} total feedback examples")

    for cat in categories:
        parts: List[str] = [cat]
        # Use override description if provided
        desc = (category_overrides.get(cat, {}) or {}).get('description') or default_descriptions.get(cat, '')
        if desc:
            parts.append(desc)
        # Include override keywords
        keywords = (category_overrides.get(cat, {}) or {}).get('keywords', [])
        if keywords:
            parts.append(', '.join(keywords))
        # Include up to N feedback example texts as seed context
        examples = feedback_examples.get(cat, []) or []
        for ex in examples[:5]:
            ex_text = (ex.get('title', '') + ' ' + ex.get('content', '')).strip()
            if ex_text:
                parts.append(ex_text)

        seed_text = '\n'.join(parts)
        proto = normalize_embedding(get_embedding(seed_text))
        prototypes[cat] = proto

    return prototypes


def _result_text(result: Dict[str, Any]) -> str:
    title = result.get('title', '') or ''
    content = result.get('content', '') or ''
    url = result.get('url', '') or ''
    return f"{title}\n{content}\n{url}"


def classify_results_with_prototypes(
    results: List[Dict[str, Any]],
    categories: List[str],
    user_prefs: Dict[str, Any],
    top_k: int = 2,
    threshold: float = 0.18
) -> List[Dict[str, Any]]:
    """Classify results by cosine similarity to category prototypes.

    threshold: cosine similarity on normalized embeddings; tune per needs.
    """
    if not results:
        return []

    # Build prototypes
    prototypes = _build_category_prototypes(categories, user_prefs)
    cat_names = list(prototypes.keys())
    proto_matrix = np.stack([prototypes[c] for c in cat_names]) if cat_names else None

    # Build URL-to-category mapping from feedback for exact matches
    feedback_examples: Dict[str, List[Dict[str, str]]] = (user_prefs or {}).get('category_feedback', {})
    url_to_category: Dict[str, str] = {}
    for cat, examples in feedback_examples.items():
        for ex in examples:
            ex_url = ex.get('url', '')
            if ex_url:
                url_to_category[ex_url] = cat
    
    updated: List[Dict[str, Any]] = []
    for r in results:
        try:
            result_url = r.get('url', '')
            # Check if we have explicit feedback for this exact URL
            if result_url in url_to_category:
                feedback_cat = url_to_category[result_url]
                r['category'] = feedback_cat
                r['category_labels'] = [feedback_cat]
                r['category_confidences'] = [1.0]  # High confidence for explicit feedback
                logger.debug(f"Using explicit feedback category '{feedback_cat}' for URL: {result_url}")
            else:
                # Use embedding-based classification
                emb = normalize_embedding(get_embedding(_result_text(r)))
                # Cosine similarity for normalized vectors is dot product
                sims = proto_matrix @ emb if proto_matrix is not None else np.array([])
                # Pick top_k categories above threshold
                if sims.size > 0:
                    top_idx = np.argsort(-sims)[:top_k]
                    labels: List[str] = []
                    confidences: List[float] = []
                    for idx in top_idx:
                        if float(sims[idx]) >= threshold:
                            labels.append(cat_names[idx])
                            confidences.append(float(sims[idx]))
                    # Fallback
                    if not labels:
                        labels = ['Others']
                        confidences = [float(np.max(sims)) if sims.size else 0.0]
                    r['category'] = labels[0]
                    r['category_labels'] = labels
                    r['category_confidences'] = confidences
                else:
                    r['category'] = 'Others'
                    r['category_labels'] = ['Others']
                    r['category_confidences'] = [0.0]
        except Exception as e:
            logger.error(f"Error classifying result: {e}")
            r['category'] = 'Others'
            r['category_labels'] = ['Others']
            r['category_confidences'] = [0.0]
        updated.append(r)

    return updated


def record_feedback(user_prefs: Dict[str, Any], url: str, title: str, content: str, category: str) -> Dict[str, Any]:
    """Store a feedback example under category to improve prototypes later."""
    if not user_prefs:
        user_prefs = {}
    fb = user_prefs.get('category_feedback') or {}
    ex_list: List[Dict[str, str]] = fb.get(category) or []
    # Keep most recent N examples
    ex_list = ([{'url': url, 'title': title, 'content': content}] + ex_list)[:20]
    fb[category] = ex_list
    user_prefs['category_feedback'] = fb
    return user_prefs


