from flask import jsonify, request, current_app, send_file
from app.api import bp
import os
import logging
import json
from pathlib import Path
import tempfile
import shutil
import zipfile
import uuid
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services - lazy imports to avoid circular dependencies
faiss_index = None
gemini_chat = None
cognitive_agent = None

def _detect_category(result: Dict[str, Any]) -> str:
    """Detect category for a search result."""
    text = (result.get('title', '') + ' ' + result.get('content', '')).lower()
    url = result.get('url', '').lower()
    
    # Category keyword detection
    category_keywords = {
        'Sports': ['sport', 'football', 'basketball', 'soccer', 'cricket', 'tennis', 'game', 'match', 'player', 'league', 'championship', 'tournament', 'olympic', 'athletics'],
        'Politics': ['politic', 'government', 'election', 'president', 'senate', 'democracy', 'vote', 'congress', 'parliament', 'minister', 'party', 'candidate', 'campaign'],
        'Financial': ['finance', 'money', 'stock', 'investment', 'bank', 'economy', 'market', 'business', 'financial', 'trading', 'currency', 'dollar', 'economy'],
        'Health & Medical': ['health', 'medical', 'disease', 'doctor', 'hospital', 'medicine', 'treatment', 'wellness', 'cure', 'therapy', 'patient', 'clinic', 'pharmacy', 'symptom'],
        'Current Affairs': ['news', 'current', 'breaking', 'recent', 'today', 'happening', 'update', 'report', 'event', 'announcement'],
        'Technology': ['tech', 'computer', 'software', 'hardware', 'ai', 'programming', 'code', 'digital', 'internet', 'cyber', 'data', 'system', 'app', 'device', 'innovation'],
    }
    
    for category, keywords in category_keywords.items():
        if any(keyword in text or keyword in url for keyword in keywords):
            return category
    
    return 'Others'

def _categorize_results(results: List[Dict[str, Any]], user_context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Categorize search results (embedding-prototype if possible, else keyword fallback)."""
    try:
        from app.services.classifier import classify_results_with_prototypes
        
        # Load preferences via cognitive agent if available
        preferences = {}
        try:
            preferences = cognitive_agent.get_user_preferences() if cognitive_agent else {}
        except Exception:
            pass
        
        # Get available categories from preferences, with fallback
        available_categories = preferences.get('available_categories', [])
        if not available_categories:
            available_categories = ['Sports', 'Politics', 'Financial', 'Health & Medical', 'Current Affairs', 'Technology', 'Others']
        
        # Use available categories for classification
        prefs_categories = available_categories
        
        # Merge user_context into preferences if provided
        if user_context and user_context.get('categories'):
            preferences = {**preferences, 'categories': user_context.get('categories')}
        logger.info(f"Classifying with {len(prefs_categories)} available categories, {len(preferences.get('category_feedback', {}))} categories with feedback")

        return classify_results_with_prototypes(results, prefs_categories, preferences)
    except Exception as e:
        logger.warning(f"Embedding-based categorization failed, using keyword fallback: {e}")
        for result in results:
            result['category'] = _detect_category(result)
        return results

def init_services():
    """Initialize services within application context."""
    global faiss_index, gemini_chat, cognitive_agent
    from app.services.faiss_index import FaissIndex
    from app.services.gemini_chat import GeminiChat
    from app.agent import CognitiveAgent
    
    if faiss_index is None:
        faiss_index = FaissIndex(current_app.config['FAISS_INDEX_PATH'])
    if gemini_chat is None and current_app.config.get('GEMINI_API_KEY'):
        try:
            gemini_chat = GeminiChat(current_app.config['GEMINI_API_KEY'])
        except Exception as e:
            logger.warning(f'Could not initialize Gemini chat: {e}')
            gemini_chat = None
    if cognitive_agent is None:
        cognitive_agent = CognitiveAgent(faiss_index=faiss_index, gemini_chat=gemini_chat)

@bp.route('/index', methods=['POST'])
def index_page():
    """Index a web page's content."""
    init_services()
    from app.services.embedding import get_embedding
    data = request.get_json()
    
    if not data or 'url' not in data or 'content' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # Get embedding for the content
        embedding = get_embedding(data['content'])
        
        # Prepare document metadata
        document = {
            'url': data['url'],
            'content': data['content']
        }
        
        # Add title if provided
        if 'title' in data:
            document['title'] = data['title']
        
        # Add to FAISS index
        doc_id = faiss_index.add(embedding, document)
        
        return jsonify({
            'success': True,
            'doc_id': doc_id
        })
    except Exception as e:
        logger.error(f'Error indexing page: {str(e)}')
        return jsonify({'error': str(e)}), 500

@bp.route('/search', methods=['POST'])
def search():
    """Search the index for similar content using cognitive agent."""
    init_services()
    from app.services.embedding import get_embedding
    data = request.get_json()
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Missing query'}), 400
    
    try:
        # Get user context/preferences
        user_context = data.get('user_context', {})
        
        # Try to use cognitive agent, but fall back to direct search if agent not available
        search_results = []
        if cognitive_agent and cognitive_agent.faiss_index:
            try:
                logger.info("Using cognitive agent for search")
                result = cognitive_agent.process_user_query(data['query'], user_context)
                
                # Extract action results
                action_results = result.get('action', {}).get('search', {})
                search_results = action_results.get('results', [])
            except Exception as agent_error:
                logger.error(f"Cognitive agent failed, falling back to direct search: {agent_error}")
                # Fall back to direct search
                query_embedding = get_embedding(data['query'])
                search_results = faiss_index.search(query_embedding, k=10)
                # Categorize results
                search_results = _categorize_results(search_results, user_context)
        else:
            # Direct search fallback
            logger.info("Using direct search (cognitive agent not available)")
            query_embedding = get_embedding(data['query'])
            search_results = faiss_index.search(query_embedding, k=10)
            # Categorize results
            search_results = _categorize_results(search_results, user_context)
        
        return jsonify({
            'success': True,
            'results': search_results
        })
    except Exception as e:
        logger.error(f'Error searching: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@bp.route('/chat', methods=['POST'])
def chat():
    """Chat with Gemini about the indexed content."""
    init_services()
    from app.services.embedding import get_embedding
    data = request.get_json()
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Missing query'}), 400
    
    try:
        # Get relevant context from the index
        query_embedding = get_embedding(data['query'])
        context_results = faiss_index.search(query_embedding, k=3)
        
        # Prepare context for Gemini
        context = "\n".join([result['content'] for result in context_results])
        
        # Get response from Gemini
        response = gemini_chat.get_response(data['query'], context)
        
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f'Error in chat: {str(e)}')
        return jsonify({'error': str(e)}), 500

@bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    init_services()
    return jsonify({
        'status': 'healthy',
        'index_size': faiss_index.size()
    })

@bp.route('/embed', methods=['POST'])
def get_text_embedding():
    """Get embedding for the given text."""
    from app.services.embedding import get_embedding
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'error': 'Missing text'}), 400
    
    try:
        # Get embedding for the text
        embedding = get_embedding(data['text'])
        
        return jsonify({
            'success': True,
            'embedding': embedding.tolist()
        })
    except Exception as e:
        logger.error(f'Error getting embedding: {str(e)}')
        return jsonify({'error': str(e)}), 500

@bp.route('/regenerate-test-data', methods=['POST'])
def regenerate_test_data():
    """Regenerate test data in the index."""
    init_services()
    from app.services.embedding import get_embedding
    
    try:
        # Clear existing index
        faiss_index.clear()
        
        # Test data
        test_pages = [
            {
                'url': 'https://example.com/test1',
                'title': 'Machine Learning Page',
                'content': 'This is a test page about machine learning and artificial intelligence. Neural networks are becoming increasingly important in modern technology.'
            },
            {
                'url': 'https://example.com/test2',
                'title': 'Web Development Page',
                'content': 'Web development involves creating and maintaining websites. HTML, CSS, and JavaScript are the core technologies for building web pages.'
            },
            {
                'url': 'https://example.com/test3',
                'title': 'Data Science Page',
                'content': 'Data science combines statistics, math, programming, and domain expertise to extract insights from data.'
            }
        ]
        
        # Add test data to index
        for page in test_pages:
            embedding = get_embedding(page['content'])
            faiss_index.add(embedding, page)
        
        return jsonify({
            'success': True,
            'message': 'Test data regenerated successfully'
        })
    except Exception as e:
        logger.error(f'Error regenerating test data: {str(e)}')
        return jsonify({'error': str(e)}), 500

@bp.route('/download-index', methods=['GET'])
def download_index():
    """Download the current FAISS index and metadata."""
    init_services()
    
    try:
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        temp_dir_path = Path(temp_dir)
        
        try:
            # Create a unique filename for the zip
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            zip_filename = f'index_data_{timestamp}_{unique_id}.zip'
            zip_path = temp_dir_path / zip_filename
            
            # Create and populate the zip file
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                # Add the FAISS index file
                if faiss_index.index_path.exists():
                    zipf.write(faiss_index.index_path, 'faiss_index.bin')
                
                # Add the metadata file
                if faiss_index.index_path.with_suffix('.json').exists():
                    zipf.write(faiss_index.index_path.with_suffix('.json'), 'metadata.json')
                
                # Add stats file
                stats = {
                    'total_documents': faiss_index.size(),
                    'dimension': faiss_index.dimension,
                    'timestamp': str(Path(faiss_index.index_path).stat().st_mtime if faiss_index.index_path.exists() else None)
                }
                stats_path = temp_dir_path / 'stats.json'
                with open(stats_path, 'w') as f:
                    json.dump(stats, f, indent=2)
                zipf.write(stats_path, 'stats.json')
            
            # Create a copy of the zip file to send
            download_name = f'semantic_search_index_{timestamp}.zip'
            
            # Send the file and clean up after sending
            response = send_file(
                str(zip_path),  # Convert Path to string
                mimetype='application/zip',
                as_attachment=True,
                download_name=download_name
            )
            
            # Add cleanup callback
            @response.call_on_close
            def cleanup():
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.error(f'Error cleaning up temporary directory: {str(e)}')
            
            return response
            
        except Exception as e:
            # Clean up on error
            shutil.rmtree(temp_dir)
            raise
            
    except Exception as e:
        logger.error(f'Error preparing index download: {str(e)}')
        return jsonify({'error': str(e)}), 500

@bp.route('/stats', methods=['GET'])
def get_stats():
    """Get statistics about the index."""
    init_services()
    
    try:
        stats = {
            'total_documents': faiss_index.size(),
            'dimension': faiss_index.dimension,
            'index_size_bytes': os.path.getsize(faiss_index.index_path) if faiss_index.index_path.exists() else 0
        }
        
        return jsonify({
            'status': 'success',
            'stats': stats
        })
    except Exception as e:
        logger.error(f'Error getting stats: {str(e)}')
        return jsonify({'error': str(e)}), 500

@bp.route('/check-indexed', methods=['POST'])
def check_indexed():
    """Check if a page is already indexed."""
    init_services()
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing URL'}), 400
    
    try:
        # Check if URL exists in the index
        is_indexed = faiss_index.contains_url(data['url'])
        
        return jsonify({
            'success': True,
            'isIndexed': is_indexed,
            'is_indexed': is_indexed  # Also include snake_case for compatibility
        })
    except Exception as e:
        logger.error(f'Error checking if page is indexed: {str(e)}')
        return jsonify({'error': str(e)}), 500

@bp.route('/clear-index', methods=['POST'])
def clear_index():
    """Clear all indexed data and start fresh."""
    init_services()
    
    try:
        # Clear the FAISS index
        faiss_index.clear()
        
        logger.info("Index cleared successfully")
        
        return jsonify({
            'success': True,
            'message': 'All indexed data cleared successfully'
        })
    except Exception as e:
        logger.error(f'Error clearing index: {str(e)}')
        return jsonify({'error': str(e)}), 500

@bp.route('/preferences', methods=['GET'])
def get_preferences():
    """Get user preferences."""
    init_services()
    
    try:
        preferences = cognitive_agent.get_user_preferences()
        return jsonify({
            'success': True,
            'preferences': preferences
        })
    except Exception as e:
        logger.error(f'Error getting preferences: {str(e)}')
        return jsonify({'error': str(e)}), 500

@bp.route('/preferences', methods=['POST'])
def update_preferences():
    """Update user preferences."""
    init_services()
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing preferences data'}), 400
    
    try:
        success = cognitive_agent.update_user_preferences(data)
        
        return jsonify({
            'success': success,
            'message': 'Preferences updated successfully' if success else 'Failed to update preferences'
        })
    except Exception as e:
        logger.error(f'Error updating preferences: {str(e)}')
        return jsonify({'error': str(e)}), 500

@bp.route('/favorites', methods=['GET'])
def get_favorites():
    """Get user's favorite items."""
    init_services()
    
    try:
        preferences = cognitive_agent.get_user_preferences()
        favorites = preferences.get('favorites', [])
        
        return jsonify({
            'success': True,
            'favorites': favorites
        })
    except Exception as e:
        logger.error(f'Error getting favorites: {str(e)}')
        return jsonify({'error': str(e)}), 500

@bp.route('/favorites', methods=['POST'])
def add_favorite():
    """Add item to favorites."""
    init_services()
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing required data'}), 400
    
    try:
        preferences = cognitive_agent.get_user_preferences()
        favorites = preferences.get('favorites', [])
        
        # Check if already in favorites
        if any(fav.get('url') == data['url'] for fav in favorites):
            return jsonify({
                'success': False,
                'message': 'Item already in favorites'
            })
        
        # Add to favorites
        favorites.append({
            'url': data['url'],
            'title': data.get('title', ''),
            'content': data.get('content', ''),
            'added_at': datetime.now().isoformat()
        })
        
        # Update preferences
        preferences['favorites'] = favorites
        cognitive_agent.update_user_preferences(preferences)
        
        return jsonify({
            'success': True,
            'message': 'Item added to favorites',
            'favorites': favorites
        })
    except Exception as e:
        logger.error(f'Error adding favorite: {str(e)}')
        return jsonify({'error': str(e)}), 500

@bp.route('/favorites', methods=['DELETE'])
def remove_favorite():
    """Remove item from favorites."""
    init_services()
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing URL'}), 400
    
    try:
        preferences = cognitive_agent.get_user_preferences()
        favorites = preferences.get('favorites', [])
        
        # Remove from favorites
        favorites = [fav for fav in favorites if fav.get('url') != data['url']]
        
        # Update preferences
        preferences['favorites'] = favorites
        cognitive_agent.update_user_preferences(preferences)
        
        return jsonify({
            'success': True,
            'message': 'Item removed from favorites',
            'favorites': favorites
        })
    except Exception as e:
        logger.error(f'Error removing favorite: {str(e)}')
        return jsonify({'error': str(e)}), 500

@bp.route('/categorize', methods=['POST'])
def categorize():
    """Categorize content."""
    init_services()
    data = request.get_json()
    
    if not data or 'content' not in data:
        return jsonify({'error': 'Missing content'}), 400
    
    try:
        # Get user context
        user_context = data.get('user_context', {})
        
        # Use decision layer to categorize via cognitive agent
        if cognitive_agent:
            categorization = cognitive_agent.decision.categorize_content(data, user_context)
        else:
            categorization = {'categories': ['Others'], 'confidence': 0.5}
        
        return jsonify({
            'success': True,
            'categorization': categorization
        })
    except Exception as e:
        logger.error(f'Error categorizing: {str(e)}')
        return jsonify({'error': str(e)}), 500 

@bp.route('/classification/feedback', methods=['POST'])
def classification_feedback():
    """Accept user category correction feedback and store in preferences for future prototype updates."""
    init_services()
    data = request.get_json()
    if not data or 'url' not in data or 'category' not in data:
        return jsonify({'error': 'Missing required fields (url, category)'}), 400
    try:
        url = data['url']
        category = data['category']
        title = data.get('title', '')
        content = data.get('content', '')

        # Get and update preferences
        preferences = cognitive_agent.get_user_preferences() if cognitive_agent else {}
        from app.services.classifier import record_feedback
        preferences = record_feedback(preferences, url, title, content, category)
        ok = True
        if cognitive_agent:
            ok = cognitive_agent.update_user_preferences(preferences)

        return jsonify({
            'success': bool(ok),
            'message': 'Feedback recorded' if ok else 'Failed to store feedback'
        })
    except Exception as e:
        logger.error(f'Error recording classification feedback: {str(e)}')
        return jsonify({'error': str(e)}), 500

@bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all available categories."""
    try:
        init_services()
        
        if cognitive_agent and hasattr(cognitive_agent, 'memory') and cognitive_agent.memory:
            categories = cognitive_agent.memory.get_available_categories()
            preferences = cognitive_agent.get_user_preferences()
            descriptions = preferences.get('category_descriptions', {})
        else:
            # Fallback to defaults
            categories = ['Sports', 'Politics', 'Financial', 'Health & Medical', 'Current Affairs', 'Technology', 'Others']
            descriptions = {}
        
        return jsonify({
            'success': True,
            'categories': categories,
            'descriptions': descriptions
        })
    except Exception as e:
        logger.error(f'Error getting categories: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/categories', methods=['POST'])
def add_category():
    """Add a new category."""
    try:
        init_services()
        
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        if not data or 'category' not in data:
            return jsonify({'success': False, 'error': 'Missing category name'}), 400
        
        category = data['category']
        description = data.get('description', '')
        
        if not cognitive_agent:
            return jsonify({'success': False, 'error': 'Cognitive agent not available'}), 500
        
        if not hasattr(cognitive_agent, 'memory') or not cognitive_agent.memory:
            return jsonify({'success': False, 'error': 'Memory layer not available'}), 500
        
        success = cognitive_agent.memory.add_category(category, description)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Category "{category}" added successfully',
                'categories': cognitive_agent.memory.get_available_categories()
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Category "{category}" already exists'
            }), 400
    except Exception as e:
        logger.error(f'Error adding category: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/categories', methods=['DELETE'])
def remove_category():
    """Remove a category."""
    try:
        init_services()
        
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        if not data or 'category' not in data:
            return jsonify({'success': False, 'error': 'Missing category name'}), 400
        
        category = data['category']
        
        if not cognitive_agent:
            return jsonify({'success': False, 'error': 'Cognitive agent not available'}), 500
        
        if not hasattr(cognitive_agent, 'memory') or not cognitive_agent.memory:
            return jsonify({'success': False, 'error': 'Memory layer not available'}), 500
        
        success = cognitive_agent.memory.remove_category(category)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Category "{category}" removed successfully',
                'categories': cognitive_agent.memory.get_available_categories()
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Cannot remove category "{category}"'
            }), 400
    except Exception as e:
        logger.error(f'Error removing category: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500